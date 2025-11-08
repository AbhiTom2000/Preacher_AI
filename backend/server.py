from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import json
import re
import math
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import bleach
import google.generativeai as genai

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# --- Config knobs ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
AI_TIMEOUT_S = int(os.environ.get("AI_TIMEOUT_S", "30"))
WS_PING_INTERVAL_S = int(os.environ.get("WS_PING_INTERVAL_S", "25"))
PREFERRED_GEMINI = os.environ.get("GEMINI_MODEL", "").strip()  # may be empty
MAX_GEN_RETRIES = int(os.environ.get("GEN_RETRIES", "2"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# Load Bible verse data
print("Loading Bible verses...")
try:
    with open(ROOT_DIR / "storage" / "english_bible_verses.json", "r", encoding="utf-8") as f:
        english_verses_data = json.load(f)
    with open(ROOT_DIR / "storage" / "hindi_bible_verses.json", "r", encoding="utf-8") as f:
        hindi_verses_data = json.load(f)
    print("Bible verse data loaded successfully.")
except FileNotFoundError:
    logger.error("Bible verse JSON files not found. Ensure they are in backend/storage.")
    english_verses_data = []
    hindi_verses_data = []
except (UnicodeDecodeError, json.JSONDecodeError) as e:
    logger.error(f"Error reading Bible verse files: {e}")
    english_verses_data = []
    hindi_verses_data = []

# Initialize Sentence Transformer model
print("Loading Sentence Transformer model...")
try:
    embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    print("Sentence Transformer model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading sentence transformer model: {e}")
    embedding_model = None

# --- FAISS persistence ---
INDEX_DIR = ROOT_DIR / "storage" / "faiss"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

def build_or_load_index(name: str, verses_data):
    path = INDEX_DIR / f"{name}.index"
    map_path = INDEX_DIR / f"{name}_map.json"

    if path.exists() and map_path.exists():
        try:
            idx = faiss.read_index(str(path))
            with open(map_path, "r", encoding="utf-8") as f:
                verse_map = json.load(f)
            verse_map = {int(k): v for k, v in verse_map.items()}
            print(f"Loaded FAISS index for {name} from disk.")
            return idx, verse_map
        except Exception as e:
            logger.warning(f"Failed to load {name} index; rebuilding. {e}")

    if not verses_data or not embedding_model:
        return None, {}

    verses = [v["text"] for v in verses_data]
    verse_map = {i: v for i, v in enumerate(verses_data)}
    embeds = embedding_model.encode(verses, convert_to_numpy=True)
    idx = faiss.IndexFlatL2(embeds.shape[1])
    idx.add(embeds)

    try:
        faiss.write_index(idx, str(path))
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(verse_map, f, ensure_ascii=False)
        print(f"Built & persisted FAISS index for {name}.")
    except Exception as e:
        logger.warning(f"Could not persist {name} index: {e}")

    return idx, verse_map

english_index, english_verse_map = build_or_load_index("english", english_verses_data)
hindi_index, hindi_verse_map = build_or_load_index("hindi", hindi_verses_data)

# --- FastAPI lifespan (startup/shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure indexes
    try:
        await db.chat_messages.create_index([("session_id", 1), ("timestamp", 1)])
        await db.chat_sessions.create_index([("id", 1)], unique=True)
        await db.analytics_events.create_index([("session_id", 1), ("ts", 1)])
        await db.analytics_events.create_index([("_meta.ingested_at", 1)])
    except Exception as e:
        logger.warning(f"Index creation failed: {e}")
    try:
        # Configure Gemini and choose a valid model up front
        _configure_gemini()
        _resolve_and_cache_gemini_model()
        yield
    finally:
        client.close()

app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# ---------------- Gemini helpers ----------------
_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
_CHOSEN_MODEL = None  # cached resolved model name (e.g., "gemini-1.5-flash")

def _configure_gemini():
    if not _GEMINI_KEY:
        logger.error("Gemini API key not configured")
        return
    genai.configure(api_key=_GEMINI_KEY)

def _list_models_safe() -> List[str]:
    """
    Returns list of model names (without 'models/') that support generateContent.
    Handles library/API differences.
    """
    try:
        models = list(genai.list_models())
        names = []
        for m in models:
            base = (getattr(m, "name", "") or "").split("/")[-1]
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                names.append(base)
        return names
    except Exception as e:
        logger.warning(f"Could not list Gemini models: {e}")
        # fallback to a reasonable static set
        return [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.5-pro",
            "gemini-pro",
        ]

def _resolve_and_cache_gemini_model():
    global _CHOSEN_MODEL
    if not _GEMINI_KEY:
        _CHOSEN_MODEL = None
        return

    available = set(_list_models_safe())
    prefs = []
    if PREFERRED_GEMINI:
        prefs.append(PREFERRED_GEMINI)
    prefs += [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.5-pro",
        "gemini-pro",
    ]
    for p in prefs:
        base = p.replace("-latest", "")
        if base in available:
            _CHOSEN_MODEL = base
            logger.info(f"Using Gemini model: {_CHOSEN_MODEL} (available set: {sorted(list(available))[:6]}...)")
            return
    logger.error(f"No compatible Gemini model found among preferences {prefs} and available {available}")
    _CHOSEN_MODEL = None

def _make_gemini():
    """
    Returns a ready GenerativeModel or None if not available.
    """
    if not _GEMINI_KEY:
        return None
    if not _CHOSEN_MODEL:
        _resolve_and_cache_gemini_model()
        if not _CHOSEN_MODEL:
            return None
    try:
        return genai.GenerativeModel(model_name=_CHOSEN_MODEL)
    except Exception as e:
        logger.error(f"Failed to init GenerativeModel({_CHOSEN_MODEL}): {e}")
        return None

async def _generate_with_retry(user_message: str, system_instruction: str) -> Optional[str]:
    """
    Portable generation across gemini library versions:
    - Build a single combined prompt with system + user text.
    - Use generate_content in a background thread.
    - Retry on 429 with a short sleep.
    """
    model = _make_gemini()
    if not model:
        return None

    combined = (
        f"[SYSTEM]\n{system_instruction.strip()}\n\n"
        f"[USER]\n{user_message.strip()}"
    )

    for attempt in range(MAX_GEN_RETRIES + 1):
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, combined),
                timeout=AI_TIMEOUT_S,
            )
            return (getattr(resp, "text", "") or "").strip()
        except asyncio.TimeoutError:
            logger.error("AI response timeout")
            return None
        except Exception as e:
            msg = str(e)
            if "429" in msg and attempt < MAX_GEN_RETRIES:
                m = re.search(r"retry.*?(\d+)\s*s", msg, flags=re.I)
                delay = int(m.group(1)) if m else 40
                logger.warning(f"429 rate-limited. Sleeping {delay}s then retrying (attempt {attempt+1}).")
                await asyncio.sleep(delay)
                continue
            logger.error(f"Gemini error (attempt {attempt}): {e}")
            return None

# ---------------- App helpers ----------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("connection open")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        logger.info("connection closed")

    async def send_text(self, session_id: str, payload: dict):
        if session_id not in self.active_connections:
            return
        try:
            if "_id" in payload:
                payload = dict(payload)
                payload.pop("_id", None)
            await self.active_connections[session_id].send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"send_text failed: {e}")

def sanitize_input(text: str) -> str:
    if not text:
        return ""
    sanitized = bleach.clean(text, tags=[], attributes=[], strip=True)
    sanitized = re.sub(r"\s+", " ", sanitized.strip())
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000] + "..."
    return sanitized

def validate_session_id(session_id: str) -> bool:
    try:
        uuid.UUID(session_id)
        return True
    except ValueError:
        return False

BLOCKLIST = {"suicide instructions", "self-harm instructions"}
def is_disallowed_prompt(t: str) -> bool:
    low = t.lower()
    return any(k in low for k in BLOCKLIST)

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    message: str
    sender: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    language: str = "english"
    cited_verses: Optional[List[dict]] = Field(default_factory=list)

    @validator("message")
    def _validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v

    @validator("session_id")
    def _validate_session_id(cls, v):
        if not validate_session_id(v):
            raise ValueError("Invalid session ID format")
        return v

def validate_and_prepare_message(message: str, sender: str = "user") -> str:
    if not message or not message.strip():
        return ""
    max_length = 1000 if sender == "user" else 1300
    message = sanitize_input(message)
    if len(message) > max_length:
        if sender == "ai":
            sentences = message.split(". ")
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence + ". ") <= max_length:
                    truncated += sentence + ". "
                else:
                    break
            message = truncated.rstrip() if truncated else (message[:max_length] + "...")
        else:
            message = message[:max_length] + "..."
    return message

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    language: str = "english"
    message_count: int = 0

class BiblicalResponse(BaseModel):
    response: str
    cited_verses: List[dict] = Field(default_factory=list)
    language: str

# --- Analytics model + APIs ---
class AnalyticsEvent(BaseModel):
    type: str
    ts: int
    session_id: str
    props: Dict[str, Any] = Field(default_factory=dict)

def prepare_for_mongo(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, str) and key in ["timestamp", "created_at"]:
                try:
                    item[key] = datetime.fromisoformat(value)
                except:
                    pass
    return item

# ------------- Verse retrieval (refined) -------------
def _pick_language(text: str) -> str:
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        return "hindi"
    return "english"

def _normalize_scores(distances: np.ndarray) -> np.ndarray:
    d = distances.astype(np.float32)
    d = d - d.min() if d.size and not np.isclose(d.max(), d.min()) else d
    if d.size and d.max() > 0:
        d = 1.0 - (d / d.max())
    return d

async def get_bible_verses(query: str, language: str = "english"):
    try:
        index = english_index if language != "hindi" else hindi_index
        verse_map = english_verse_map if language != "hindi" else hindi_verse_map

        if index is None or embedding_model is None or not verse_map:
            logger.warning("FAISS index or model not available. Returning empty list.")
            return []

        q_emb = embedding_model.encode([query], convert_to_numpy=True)
        D, I = index.search(q_emb, k=7)
        sims = _normalize_scores(D[0])

        MIN_SIM = 0.25
        pairs = [(i, s) for i, s in zip(I[0], sims) if i >= 0]
        pairs.sort(key=lambda x: x[1], reverse=True)
        kept = [p for p in pairs if p[1] >= MIN_SIM][:5] or pairs[:1]

        results = []
        for i, score in kept:
            verse = verse_map[i]
            results.append({
                "reference": f"{verse['book']} {verse['chapter']}:{verse['verse']}",
                "text": verse["text"],
                "score": float(score),
            })

        if not results:
            logger.info(f"No relevant verses found for query: {query}")

        return results

    except Exception as e:
        logger.error(f"Error fetching Bible verses: {e}")
        return []

# ------------- LLM guidance -------------
PASTORAL_SYSTEM = """You are Preacher.ai — a gentle spiritual companion who writes with the heart of a caring pastor.

Your purpose: offer **deeply compassionate, biblically grounded responses** that feel like a personal letter from a loving pastor — gentle, wise, and full of grace.

**STYLE & TONE**
- Speak tenderly, as if beside someone in a quiet sanctuary.
- Use **Markdown** naturally — bold, italics, blockquotes, and short lists are welcome.
- Avoid HTML. Keep formatting clean and prayerful.
- You may use a few emojis for warmth (e.g., 🤲 💙 ✨ 🙏) — but sparingly.
- Use gentle pauses with “…” for reflection.
- Keep paragraphs short (1–3 sentences each).
- Separate paragraphs with a blank line.

**STRUCTURE — “The Gentle Guide”**
1. 🤲 **Personal Acknowledgment** – Recognize their emotion or struggle.
2. 💙 **Heart-Centered Opening** – Validate their experience with compassion.
3. 📖 **Sacred Scripture** – Include 1–2 relevant verses (*italicize references and quotes*).
4. 🌱 **Practical Wisdom** – Offer simple, grace-filled guidance they can apply today.
5. ✨ **Encouraging Affirmation** – Remind them of their worth and God’s love.
6. 🙏 **Personal Blessing** – End with a heartfelt blessing or prayer.

**LENGTH**
- 150–250 words, written as a warm pastoral letter.
- Flow naturally — not rigidly sectioned; let the structure *guide*, not constrain.

**EXAMPLES OF SCRIPTURE STYLE**
- *Philippians 4:6–7* reminds us that *"Do not be anxious about anything…"*
- In *Matthew 11:28*, Jesus gently invites, *"Come to me, all you who are weary…"*
- The psalmist writes in *Psalm 23:4*, *"Even though I walk through the darkest valley…"* 

Every response should help the user feel **seen**, **valued**, and **loved** by God.
"""

async def get_biblical_guidance(user_message: str, session_id: str, language: str = "english"):
    try:
        if not user_message or len(user_message.strip()) < 3:
            return BiblicalResponse(
                response="Please ask a more specific question for biblical guidance.",
                cited_verses=[],
                language=language,
            )

        if not _GEMINI_KEY:
            return BiblicalResponse(
                response="I’m having trouble accessing the AI service right now. Please try again later.",
                cited_verses=[],
                language=language,
            )

        ai_response = await _generate_with_retry(user_message, PASTORAL_SYSTEM)
        if not ai_response or len(ai_response.strip()) < 10:
            return BiblicalResponse(
                response="Let me think more about your question. Could you please rephrase it or provide more context?",
                cited_verses=[],
                language=language,
            )

        verses = await get_bible_verses(user_message, language)
        return BiblicalResponse(response=ai_response, cited_verses=verses, language=language)

    except Exception as e:
        logger.error(f"Error getting biblical guidance: {e}")
        fallback = {
            "english": "I’m experiencing technical difficulties right now. Please try again in a moment. *“The Lord is near to all who call on him, to all who call on him in truth.” — Psalm 145:18*",
            "hindi": "मुझे खेद है, अभी तकनीकी समस्या आ रही है। कृपया कुछ देर बाद फिर प्रयास करें।",
        }
        return BiblicalResponse(response=fallback.get(language, fallback["english"]), cited_verses=[], language=language)

def detect_language(text: str) -> str:
    return _pick_language(text)

# Per-verse justification helper
async def justify_with_llm(verse_text: str, reference: str, query: str) -> str:
    if not _GEMINI_KEY:
        return "This verse relates to your question by addressing a closely connected principle in context."

    prompt = (
        "In 3–4 short lines, explain why the following Bible verse is relevant "
        "to the user's question. Be specific and pastoral, avoid repetition.\n\n"
        f"Question: {query}\n"
        f"Verse: {reference} — {verse_text}\n\n"
        "Answer:"
    )
    model = _make_gemini()
    if not model:
        return "This verse offers guidance that speaks to your situation in a related way."

    for attempt in range(MAX_GEN_RETRIES + 1):
        try:
            resp = await asyncio.to_thread(model.generate_content, prompt)
            text = (getattr(resp, "text", "") or "").strip()
            return text[:600] + ("…" if len(text) > 600 else "") or \
                   "This verse offers guidance that speaks to your situation in a related way."
        except Exception as e:
            msg = str(e)
            if "429" in msg and attempt < MAX_GEN_RETRIES:
                m = re.search(r"retry.*?(\d+)\s*s", msg, flags=re.I)
                delay = int(m.group(1)) if m else 40
                await asyncio.sleep(delay)
                continue
            return "This verse offers guidance that speaks to your situation in a related way."

# ---------------- WebSocket ----------------
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)

    async def _ping():
        while True:
            await asyncio.sleep(WS_PING_INTERVAL_S)
            await manager.send_text(session_id, {"type": "ping"})

    ping_task = asyncio.create_task(_ping())

    try:
        while True:
            raw = await websocket.receive_text()
            message_data = json.loads(raw)

            # Explain requests over WS
            if message_data.get("type") == "explain":
                verse_id = message_data.get("verseId")
                verse_text = message_data.get("verseText", "")
                reference = message_data.get("reference", "")
                query = message_data.get("query", "")
                try:
                    explanation = await justify_with_llm(verse_text, reference, query)
                    await manager.send_text(session_id, {
                        "type": "explain",
                        "payload": {"for": verse_id, "text": explanation},
                    })
                except Exception:
                    logger.exception("Explain failed")
                    await manager.send_text(session_id, {
                        "type": "explain_error",
                        "payload": {"for": verse_id, "message": "Sorry, I couldn’t explain this verse right now."},
                    })
                continue

            # Chat messages
            user_message = (message_data.get("message") or "").strip()
            if not user_message:
                await manager.send_text(session_id, {"type": "error", "message": "Message cannot be empty."})
                continue

            user_message = validate_and_prepare_message(user_message, "user")

            if is_disallowed_prompt(user_message):
                await manager.send_text(session_id, {
                    "type": "error",
                    "message": "I can’t help with that. If you’re in immediate danger, please contact local emergency services or a trusted person.",
                })
                continue

            language = detect_language(user_message)

            session_exists = await db.chat_sessions.find_one({"id": session_id})
            if not session_exists:
                session = ChatSession(id=session_id, language=language)
                await db.chat_sessions.insert_one(prepare_for_mongo(session.dict()))

            user_msg = ChatMessage(session_id=session_id, message=user_message, sender="user", language=language)
            user_doc = prepare_for_mongo(user_msg.dict())
            await db.chat_messages.insert_one(user_doc)
            await manager.send_text(session_id, user_doc)

            biblical_response = await get_biblical_guidance(user_message, session_id, language)

            ai_text = validate_and_prepare_message(biblical_response.response, "ai")
            ai_msg = ChatMessage(
                session_id=session_id,
                message=ai_text,
                sender="ai",
                language=language,
                cited_verses=biblical_response.cited_verses,
            )
            ai_doc = prepare_for_mongo(ai_msg.dict())
            await db.chat_messages.insert_one(ai_doc)
            await manager.send_text(session_id, ai_doc)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.send_text(session_id, {"type": "error", "message": "An unexpected error occurred. Please try again."})
    finally:
        ping_task.cancel()
        manager.disconnect(session_id)

# ---------------- REST ----------------
@api_router.post("/session", response_model=dict)
async def create_session():
    try:
        session = ChatSession()
        result = await db.chat_sessions.insert_one(prepare_for_mongo(session.dict()))
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create session")
        return {"session_id": session.id, "status": "success", "created_at": session.created_at.isoformat()}
    except HTTPException:
        raise
    except PyMongoError:
        logger.error("Database error while creating session.")
        raise HTTPException(status_code=500, detail="Database error creating session.")
    except Exception as e:
        logger.error(f"Unexpected error creating session: {e}")
        raise HTTPException(status_code=500, detail="Error creating session")

@api_router.get("/chat/{session_id}", response_model=List[dict])
async def get_chat_history(session_id: str):
    try:
        if not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID format")

        messages = await db.chat_messages.find({"session_id": session_id}).sort("timestamp", 1).limit(200).to_list(200)

        cleaned = []
        for msg in messages:
            if "_id" in msg:
                msg.pop("_id", None)
            cleaned.append(parse_from_mongo(msg))
        return cleaned

    except HTTPException:
        raise
    except PyMongoError:
        logger.error(f"Database error getting chat history for session {session_id}.")
        raise HTTPException(status_code=500, detail="Database error retrieving chat history")
    except Exception as e:
        logger.error(f"Unexpected error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")

@api_router.get("/")
async def root():
    return {"message": "Preacher.ai Backend Running", "status": "healthy", "model": _CHOSEN_MODEL or "unconfigured"}

# --- Analytics intake API ---
@api_router.post("/analytics/events")
async def analytics_events(payload: dict, request: Request):
    try:
        events = payload.get("events", [])
        if not isinstance(events, list) or len(events) == 0:
            raise HTTPException(status_code=400, detail="No events")

        user_agent = request.headers.get("user-agent")
        ip = request.client.host if request.client else None

        docs = []
        for e in events:
            try:
                ev = AnalyticsEvent(**e).dict()
                ev["_meta"] = {"ua": user_agent, "ip": ip, "ingested_at": datetime.utcnow().isoformat()}
                ev["type"] = ev["type"][:64]
                docs.append(ev)
            except Exception:
                continue

        if docs:
            await db.analytics_events.insert_many(docs)
        return {"ok": True, "stored": len(docs)}
    except HTTPException:
        raise
    except Exception:
        logger.exception("analytics_events failed")
        raise HTTPException(status_code=500, detail="analytics intake error")

# --- Analytics summary ---
@api_router.get("/analytics/summary")
async def analytics_summary(hours: int = 24):
    now = datetime.utcnow()
    start = now - timedelta(hours=hours)
    coll = db.analytics_events

    cursor = coll.find({"_meta.ingested_at": {"$gte": start.isoformat()}}, projection={"type": 1, "props": 1})
    total = 0
    rtts = []
    explain_ok = explain_err = explain_to = 0
    ws_open = ws_err = 0

    async for doc in cursor:
        total += 1
        t = doc.get("type")
        p = doc.get("props") or {}
        if t == "ai_response_received" and isinstance(p.get("ms"), (int, float)):
            rtts.append(p["ms"])
        elif t == "explain_success":
            explain_ok += 1
        elif t == "explain_error":
            explain_err += 1
        elif t == "explain_timeout":
            explain_to += 1
        elif t == "ws_open":
            ws_open += 1
        elif t == "ws_error":
            ws_err += 1

    avg = (sum(rtts) / len(rtts)) if rtts else None
    p50 = (sorted(rtts)[len(rtts) // 2] if rtts else None)
    p95 = (sorted(rtts)[math.floor(0.95 * (len(rtts) - 1))] if rtts else None)

    explain_total = explain_ok + explain_err + explain_to
    explain_rate = (explain_ok / explain_total) if explain_total else None

    return {
        "window_hours": hours,
        "events": total,
        "rtt_ms": {"avg": avg, "p50": p50, "p95": p95, "samples": len(rtts)},
        "explain": {"success": explain_ok, "error": explain_err, "timeout": explain_to, "success_rate": explain_rate},
        "ws": {"open": ws_open, "error": ws_err},
    }

app.include_router(api_router)

# --- CORS from env ---
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "connect-src 'self' http: https: ws: wss:; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self';"
    )
    return response

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("connection open")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        logger.info("connection closed")

    async def send_text(self, session_id: str, payload: dict):
        if session_id not in self.active_connections:
            return
        try:
            if "_id" in payload:
                payload = dict(payload)
                payload.pop("_id", None)
            await self.active_connections[session_id].send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"send_text failed: {e}")

# 👉 ADD THIS
manager = ConnectionManager()
