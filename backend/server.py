from fastapi import FastAPI, APIRouter, HTTPException, WebSocket
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import asyncio
import json
import aiohttp
from emergentintegrations.llm.chat import LlmChat, UserMessage
import re
from functools import wraps
import time
from collections import defaultdict
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Load Bible verse data
print("Loading Bible verses...")
try:
    with open('storage/english_bible_verses.json', 'r') as f:
        english_verses_data = json.load(f)
    with open('storage/hindi_bible_verses.json', 'r') as f:
        hindi_verses_data = json.load(f)
    print("Bible verse data loaded successfully.")
except FileNotFoundError:
    logging.error("Bible verse JSON files not found. Please ensure they are in the backend directory.")
    english_verses_data = []
    hindi_verses_data = []

# Initialize Sentence Transformer model
# This model needs to be downloaded, a process that can take a while
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

# Create English and Hindi indexes
english_index, english_verse_map = create_faiss_index(english_verses_data)
hindi_index, hindi_verse_map = create_faiss_index(hindi_verses_data)

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# Rate limiting setup
rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 10  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

def rate_limit(max_requests: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get client IP (simplified for demo)
            client_id = "default_client"  # In production, extract from request
            current_time = time.time()
            
            # Clean old requests
            rate_limit_storage[client_id] = [
                req_time for req_time in rate_limit_storage[client_id] 
                if current_time - req_time < window
            ]
            
            # Check rate limit
            if len(rate_limit_storage[client_id]) >= max_requests:
                raise HTTPException(
                    status_code=429, 
                    detail="Too many requests. Please wait before sending another message."
                )
            
            # Add current request
            rate_limit_storage[client_id].append(current_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Input validation and sanitization
def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Limit length
    if len(text) > 1000:
        text = text[:1000] + "..."
    
    # Remove potentially harmful characters (basic XSS prevention)
    text = re.sub(r'[<>{}]', '', text)
    
    return text

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
    sender: str  # 'user' or 'ai'
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    language: str = "english"
    cited_verses: Optional[List[dict]] = []
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        # Different limits for user vs AI messages
        # This will be handled in the API endpoint
        return v
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not validate_session_id(v):
            raise ValueError('Invalid session ID format')
        return v

# Helper function to validate and truncate messages appropriately
def validate_and_prepare_message(message: str, sender: str = "user") -> str:
    """Validate and prepare message for storage with appropriate limits"""
    if not message or not message.strip():
        return ""
    
    if sender == "user":
        # User messages limited to 1000 characters
        max_length = 1000
    else:
        # AI messages can be longer for biblical guidance
        max_length = 2500
    
    # Remove excessive whitespace
    message = re.sub(r'\s+', ' ', message.strip())
    
    # Truncate if too long
    if len(message) > max_length:
        if sender == "ai":
            # For AI messages, truncate at sentence boundary if possible
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
    
    # Remove potentially harmful characters (basic XSS prevention)
    message = re.sub(r'[<>{}]', '', message)
    
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

# Helper functions
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

# Bible files through JSON files
async def get_bible_verses(query: str, language: str = "english"):
    """
    Get relevant Bible verses using semantic search on pre-built FAISS indices.
    """
    try:
        # Use appropriate index based on language
        if language == "hindi":
            index = hindi_index
            verse_map = hindi_verse_map
        else:
            index = english_index
            verse_map = english_verse_map

        if index is None or model is None:
            logging.warning("FAISS index or model not available. Returning empty list.")
            return []

        # Create embedding for the user query
        query_embedding = model.encode([query], convert_to_numpy=True)

        # Search the index for the top 5 most similar verses
        # The 'I' contains the indices of the most similar vectors
        D, I = index.search(query_embedding, k=5)

        # Extract the actual verse data based on the indices
        results = []
        for i, distance in zip(I[0], D[0]):
            # Implement similarity thresholding
            if distance < 10.0:  # A lower distance means higher similarity
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

# Enhanced AI Integration with better error handling
async def get_biblical_guidance(user_message: str, session_id: str, language: str = "english"):
    """Get biblical guidance using Gemini AI with enhanced error handling"""
    try:
        # Input validation
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

        # Enhanced system prompt for better biblical guidance
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

        # Initialize Gemini chat with timeout
        chat = LlmChat(
            api_key=gemini_key,
            session_id=session_id,
            system_message=system_message
        ).with_model("gemini", "gemini-1.5-flash")

        # Create user message
        user_msg = UserMessage(text=user_message)
        
        # Get AI response with timeout
        try:
            ai_response = await asyncio.wait_for(
                chat.send_message(user_msg), 
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logging.error("AI response timeout")
            return BiblicalResponse(
                response="I apologize for the delay. Please try asking your question again.",
                cited_verses=[],
                language=language
            )
        
        # Validate response
        if not ai_response or len(ai_response.strip()) < 10:
            logging.warning("AI response too short")
            return BiblicalResponse(
                response="Let me think more about your question. Could you please rephrase it or provide more context?",
                cited_verses=[],
                language=language
            )
        
        # Get related Bible verses
        verses = await get_bible_verses(user_message, language)
        
        return BiblicalResponse(
            response=ai_response,
            cited_verses=verses,
            language=language
        )
        
    except Exception as e:
        logging.error(f"Error getting biblical guidance: {e}")
        
        # Provide graceful fallback responses
        fallback_responses = {
            "english": "I apologize, but I'm experiencing technical difficulties right now. Please try again in a moment. Remember, 'The Lord is near to all who call on him, to all who call on him in truth.' - Psalm 145:18",
            "hindi": "मुझे खुशी है, लेकिन मैं अभी तकनीकी कठिनाइयों का सामना कर रहा हूं। कृपया एक पल में फिर से कोशिश करें।"
        }
        
        return BiblicalResponse(
            response=fallback_responses.get(language, fallback_responses["english"]),
            cited_verses=[],
            language=language
        )

# Language detection
def detect_language(text: str) -> str:
    """Simple language detection"""
    hindi_chars = any('\u0900' <= char <= '\u097F' for char in text)
    return "hindi" if hindi_chars else "english"

# Enhanced API Routes with better error handling and validation
@api_router.post("/chat", response_model=dict)
@rate_limit()
async def chat_endpoint(message: dict):
    """Handle chat messages with enhanced validation and error handling"""
    try:
        # Validate input
        user_message = message.get('message', '').strip()
        session_id = message.get('session_id', '')
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if not session_id or not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        # Sanitize and validate user input
        user_message = validate_and_prepare_message(user_message, "user")
        language = detect_language(user_message)
        
        # Validate session exists
        session_exists = await db.chat_sessions.find_one({"id": session_id})
        if not session_exists:
            # Create session if it doesn't exist
            session = ChatSession(id=session_id, language=language)
            session_dict = prepare_for_mongo(session.dict())
            await db.chat_sessions.insert_one(session_dict)
        
        # Save user message
        try:
            user_msg = ChatMessage(
                session_id=session_id,
                message=user_message,
                sender="user",
                language=language
            )
            user_msg_dict = prepare_for_mongo(user_msg.dict())
            await db.chat_messages.insert_one(user_msg_dict)
        except Exception as e:
            logging.error(f"Error saving user message: {e}")
            raise HTTPException(status_code=500, detail="Error saving message")
        
        # Get AI response
        biblical_response = await get_biblical_guidance(user_message, session_id, language)
        
        # Save AI response with proper validation
        try:
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
        except Exception as e:
            logging.error(f"Error saving AI message: {e}")
            # Continue even if save fails, user still gets response
        
        return {
            "response": biblical_response.response,
            "cited_verses": biblical_response.cited_verses,
            "session_id": session_id,
            "language": language,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")

@api_router.get("/chat/{session_id}", response_model=List[dict])
async def get_chat_history(session_id: str):
    """Get chat history for a session with validation"""
    try:
        # Validate session ID
        if not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID format")
        
        # Get messages with limit to prevent large responses
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).limit(200).to_list(200)
        
        # Clean up MongoDB ObjectId and other non-serializable fields
        cleaned_messages = []
        for msg in messages:
            try:
                # Remove MongoDB ObjectId
                if '_id' in msg:
                    del msg['_id']
                # Parse datetime fields
                msg = parse_from_mongo(msg)
                cleaned_messages.append(msg)
            except Exception as e:
                logging.warning(f"Error processing message: {e}")
                continue
        
        return cleaned_messages
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving chat history")

@api_router.post("/session", response_model=dict)
async def create_session():
    """Create a new chat session with error handling"""
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
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Error creating session")

@api_router.get("/")
async def root():
    return {"message": "Preacher.ai Backend Running", "status": "healthy"}

# Server-Sent Events endpoint for real-time updates
@api_router.get("/stream/{session_id}")
async def stream_chat_updates(session_id: str):
    """Server-Sent Events endpoint for real-time chat updates"""
    from fastapi.responses import StreamingResponse
    
    async def event_generator():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            
            # Keep connection alive with periodic heartbeat
            last_message_count = 0
            while True:
                try:
                    # Check for new messages in this session
                    messages = await db.chat_messages.find(
                        {"session_id": session_id}
                    ).sort("timestamp", 1).to_list(1000)
                    
                    current_count = len(messages)
                    if current_count > last_message_count:
                        # New messages found, send the latest one
                        latest_message = messages[-1] if messages else None
                        if latest_message:
                            # Clean up MongoDB ObjectId
                            if '_id' in latest_message:
                                del latest_message['_id']
                            latest_message = parse_from_mongo(latest_message)
                            
                            yield f"data: {json.dumps({'type': 'new_message', 'message': latest_message})}\n\n"
                        
                        last_message_count = current_count
                    
                    # Send heartbeat every 30 seconds
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    
                    # Wait before next check
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logging.error(f"SSE stream error: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error occurred'})}\n\n"
                    break
                    
        except Exception as e:
            logging.error(f"SSE generator error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Connection error'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# WebSocket endpoint (keeping for compatibility but will fallback to SSE)
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint - fallback implementation"""
    try:
        await manager.connect(websocket)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "session_id": session_id,
            "note": "Using WebSocket fallback mode"
        }))
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process the message (similar to chat endpoint)
            user_message = message_data.get('message', '')
            language = detect_language(user_message)
            
            # Send typing indicator
            await websocket.send_text(json.dumps({
                "type": "typing",
                "message": "Preacher.ai is thinking..."
            }))
            
            # Get biblical guidance
            biblical_response = await get_biblical_guidance(user_message, session_id, language)
            
            # Send response
            response_data = {
                "type": "message",
                "response": biblical_response.response,
                "cited_verses": biblical_response.cited_verses,
                "session_id": session_id,
                "language": language
            }
            
            await websocket.send_text(json.dumps(response_data))
            
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

# Include the router
app.include_router(api_router)

# CORS and Security Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],    
)

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()