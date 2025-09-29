from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import asyncio
import json
import re
from functools import wraps
import time
from collections import defaultdict
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
# from fastapi_limiter import FastAPILimiter
# import aioredis
import bleach
import google.generativeai as genai


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Load Bible verse data
print("Loading Bible verses...")
try:
    with open('storage/english_bible_verses.json', 'r', encoding='utf-8') as f:
        english_verses_data = json.load(f)
    with open('storage/hindi_bible_verses.json', 'r', encoding='utf-8') as f:
        hindi_verses_data = json.load(f)
    print("Bible verse data loaded successfully.")
except FileNotFoundError:
    logging.error("Bible verse JSON files not found. Please ensure they are in the backend directory.")
    english_verses_data = []
    hindi_verses_data = []
except UnicodeDecodeError as e:
    logging.error(f"Encoding error reading Bible verse files: {e}")
    print(f"Try saving the files with UTF-8 encoding. Error: {e}")
    english_verses_data = []
    hindi_verses_data = []
except json.JSONDecodeError as e:
    logging.error(f"JSON parsing error: {e}")
    english_verses_data = []
    hindi_verses_data = []

# Initialize Sentence Transformer model
print("Loading Sentence Transformer model...")
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("Sentence Transformer model loaded successfully.")
except Exception as e:
    logging.error(f"Error loading sentence transformer model: {e}")
    model = None

# Function to create FAISS index
def create_faiss_index(verses_data):
    if not verses_data or not model:
        return None, {}

    verses = [v['text'] for v in verses_data]
    verse_map = {i: v for i, v in enumerate(verses_data)}

    print(f"Creating embeddings for {len(verses)} verses...")
    embeddings = model.encode(verses, convert_to_numpy=True)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    print("FAISS index created successfully.")
    return index, verse_map

english_index, english_verse_map = create_faiss_index(english_verses_data)
hindi_index, hindi_verse_map = create_faiss_index(hindi_verses_data)

app = FastAPI()
api_router = APIRouter(prefix="/api")

# @app.on_event("startup")
# async def startup_event():
#     redis_url = os.environ.get('REDIS_URL')
#     if redis_url:
#         redis_client = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
#         await FastAPILimiter.init(redis_client)
#     else:
#         print("REDIS_URL not found. Rate limiting will not be enabled.")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)
            
manager = ConnectionManager()

def sanitize_input(text: str) -> str:
    """Sanitize user input using bleach for robust XSS prevention"""
    if not text:
        return ""
    
    sanitized_text = bleach.clean(
        text, 
        tags=[], 
        attributes=[], 
        strip=True
    )

    sanitized_text = re.sub(r'\s+', ' ', sanitized_text.strip())
    
    if len(sanitized_text) > 1000:
        sanitized_text = sanitized_text[:1000] + "..."
    
    return sanitized_text

def validate_session_id(session_id: str) -> bool:
    """Validate session ID format"""
    try:
        uuid.UUID(session_id)
        return True
    except ValueError:
        return False

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    message: str
    sender: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    language: str = "english"
    cited_verses: Optional[List[dict]] = []
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not validate_session_id(v):
            raise ValueError('Invalid session ID format')
        return v

def validate_and_prepare_message(message: str, sender: str = "user") -> str:
    """Validate and prepare message for storage with appropriate limits"""
    if not message or not message.strip():
        return ""
    
    if sender == "user":
        max_length = 1000
    else:
        max_length = 2500
    
    message = sanitize_input(message)
    
    if len(message) > max_length:
        if sender == "ai":
            sentences = message.split('. ')
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence + '. ') <= max_length:
                    truncated += sentence + '. '
                else:
                    break
            if truncated:
                message = truncated.rstrip()
            else:
                message = message[:max_length] + "..."
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
    cited_verses: List[dict] = []
    language: str

def prepare_for_mongo(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, str) and key in ['timestamp', 'created_at']:
                try:
                    item[key] = datetime.fromisoformat(value)
                except:
                    pass
    return item

async def get_bible_verses(query: str, language: str = "english"):
    try:
        if language == "hindi":
            index = hindi_index
            verse_map = hindi_verse_map
        else:
            index = english_index
            verse_map = english_verse_map

        if index is None or model is None:
            logging.warning("FAISS index or model not available. Returning empty list.")
            return []

        query_embedding = model.encode([query], convert_to_numpy=True)
        D, I = index.search(query_embedding, k=5)

        results = []
        for i, distance in zip(I[0], D[0]):
            if distance < 10.0:
                verse = verse_map[i]
                results.append({
                    "reference": f"{verse['book']} {verse['chapter']}:{verse['verse']}",
                    "text": verse['text'],
                    "score": float(distance)
                })

        if not results:
            logging.info(f"No relevant verses found for query: {query}")

        return results

    except Exception as e:
        logging.error(f"Error fetching Bible verses with semantic search: {e}")
        return []

async def get_biblical_guidance(user_message: str, session_id: str, language: str = "english"):
    try:
        if not user_message or len(user_message.strip()) < 3:
            return BiblicalResponse(
                response="Please ask a more specific question for biblical guidance.",
                cited_verses=[],
                language=language
            )
        
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_key:
            logging.error("Gemini API key not configured")
            return BiblicalResponse(
                response="I apologize, but I'm having trouble accessing the AI service right now. Please try again later.",
                cited_verses=[],
                language=language
            )

        system_message = f"""You are Preacher.ai, a gentle spiritual companion who responds with the heart of a caring pastor.

**RESPONSE FORMAT** - Use "The Gentle Guide" structure:

🤲 **Personal Acknowledgment**: Begin with warm personal acknowledgment of their struggle/question (1 line only)
💙 **Heart-Centered Opening**: Offer heart-centered opening that validates their experience  (1 line only)
📖 **Sacred Scripture**: Share 1-2 relevant scriptures with gentle context (*always italicize verse references and quotes*)
🌱 **Practical Wisdom**: Provide practical, grace-filled wisdom they can apply today
✨ **Encouraging Affirmation**: Give encouraging affirmation of their worth and God's love
🙏 **Personal Blessing**: Close with a personal prayer or blessing 

**FORMATTING GUIDELINES**:
- **Bold** all section emojis and key spiritual concepts
- *Italicize* all Bible verse references (e.g., *John 14:27*)
- *Italicize* all direct scripture quotes (e.g., *"Peace I leave with you..."*)
- Use **bold** for emphasis on important spiritual truths
- Create visual breathing space with gentle pauses (...)

**TONE GUIDELINES**:
- Speak as if sitting beside them in a quiet sanctuary
- Use "**dear friend**," "**precious soul**," "**beloved**" naturally
- Never preach AT them, always walk WITH them
- Include gentle pauses (...) for reflection
- End with **specific, personal blessings**

**LENGTH**: 150-250 words for optimal heart connection

**HEART-TOUCH**: Make them feel **seen**, **valued**, and **loved** by God

**SCRIPTURE CITATION EXAMPLES**:
- *Philippians 4:6-7* reminds us that *"Do not be anxious about anything..."*
- In *Matthew 11:28*, Jesus tenderly invites us: *"Come to me, all you who are weary..."*
- The psalmist declares in *Psalm 23:4*: *"Even though I walk through the darkest valley..."*

Remember: Every response should feel like a **personal letter from a loving pastor** who truly understands their heart."""

        genai.configure(api_key=gemini_key)
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction=system_message
        )
        
        chat_session = model.start_chat()
        
        try:
            ai_response_obj = await asyncio.wait_for(
                chat_session.send_message_async(user_message), 
                timeout=30.0
            )
            ai_response = ai_response_obj.text
        except asyncio.TimeoutError:
            logging.error("AI response timeout")
            return BiblicalResponse(
                response="I apologize for the delay. Please try asking your question again.",
                cited_verses=[],
                language=language
            )
        
        if not ai_response or len(ai_response.strip()) < 10:
            logging.warning("AI response too short")
            return BiblicalResponse(
                response="Let me think more about your question. Could you please rephrase it or provide more context?",
                cited_verses=[],
                language=language
            )
        
        verses = await get_bible_verses(user_message, language)
        
        return BiblicalResponse(
            response=ai_response,
            cited_verses=verses,
            language=language
        )
        
    except Exception as e:
        logging.error(f"Error getting biblical guidance: {e}")
        
        fallback_responses = {
            "english": "I apologize, but I'm experiencing technical difficulties right now. Please try again in a moment. Remember, 'The Lord is near to all who call on him, to all who call on him in truth.' - Psalm 145:18",
            "hindi": "मुझे खुशी है, लेकिन मैं अभी तकनीकी कठिनाइयों का सामना कर रहा हूं। कृपया एक पल में फिर से कोशिश करें।"
        }
        
        return BiblicalResponse(
            response=fallback_responses.get(language, fallback_responses["english"]),
            cited_verses=[],
            language=language
        )

def detect_language(text: str) -> str:
    hindi_chars = any('\u0900' <= char <= '\u097F' for char in text)
    return "hindi" if hindi_chars else "english"

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get('message', '').strip()

            if not user_message:
                await manager.send_personal_message(json.dumps({
                    "response": "Message cannot be empty.",
                    "sender": "ai",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), session_id)
                continue

            user_message = validate_and_prepare_message(user_message, "user")
            language = detect_language(user_message)

            session_exists = await db.chat_sessions.find_one({"id": session_id})
            if not session_exists:
                session = ChatSession(id=session_id, language=language)
                session_dict = prepare_for_mongo(session.dict())
                await db.chat_sessions.insert_one(session_dict)

            user_msg = ChatMessage(
                session_id=session_id,
                message=user_message,
                sender="user",
                language=language
            )
            user_msg_dict = prepare_for_mongo(user_msg.dict())
            await db.chat_messages.insert_one(user_msg_dict)
            
            await manager.send_personal_message(json.dumps(user_msg_dict), session_id)

            biblical_response = await get_biblical_guidance(user_message, session_id, language)

            ai_response_text = validate_and_prepare_message(biblical_response.response, "ai")
            ai_msg = ChatMessage(
                session_id=session_id,
                message=ai_response_text,
                sender="ai",
                language=language,
                cited_verses=biblical_response.cited_verses
            )
            ai_msg_dict = prepare_for_mongo(ai_msg.dict())
            await db.chat_messages.insert_one(ai_msg_dict)
            
            await manager.send_personal_message(json.dumps(ai_msg_dict), session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        error_message = {
            "response": "An unexpected error occurred. Please try again.",
            "sender": "ai",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.send_personal_message(json.dumps(error_message), session_id)
    finally:
        manager.disconnect(session_id)

@api_router.post("/session", response_model=dict)
# @FastAPILimiter.limit("5/minute")
async def create_session():
    try:
        session = ChatSession()
        session_dict = prepare_for_mongo(session.dict())
        
        result = await db.chat_sessions.insert_one(session_dict)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        return {
            "session_id": session.id,
            "status": "success",
            "created_at": session.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except PyMongoError:
        logging.error("Database error while creating session.")
        raise HTTPException(status_code=500, detail="Database error creating session.")
    except Exception as e:
        logging.error(f"Unexpected error creating session: {e}")
        raise HTTPException(status_code=500, detail="Error creating session")

@api_router.get("/chat/{session_id}", response_model=List[dict])
# @FastAPILimiter.limit("20/minute")
async def get_chat_history(session_id: str):
    try:
        if not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID format")
        
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).limit(200).to_list(200)
        
        cleaned_messages = []
        for msg in messages:
            try:
                if '_id' in msg:
                    del msg['_id']
                msg = parse_from_mongo(msg)
                cleaned_messages.append(msg)
            except Exception as e:
                logging.warning(f"Error processing message: {e}")
                continue
        
        return cleaned_messages
        
    except HTTPException:
        raise
    except PyMongoError:
        logging.error(f"Database error getting chat history for session {session_id}.")
        raise HTTPException(status_code=500, detail="Database error retrieving chat history")
    except Exception as e:
        logging.error(f"Unexpected error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")

@api_router.get("/")
async def root():
    return {"message": "Preacher.ai Backend Running", "status": "healthy"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["http://localhost:3000"],
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
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()