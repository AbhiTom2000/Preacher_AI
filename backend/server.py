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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

# Bible API integration
async def get_bible_verses(query: str, language: str = "english"):
    """Get relevant Bible verses using ESV API"""
    try:
        # For demo purposes, return sample verses
        # In production, integrate with ESV API or Bible Gateway
        sample_verses = {
            "english": [
                {
                    "reference": "Philippians 4:6-7",
                    "text": "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God. And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus."
                },
                {
                    "reference": "Matthew 11:28",
                    "text": "Come to me, all you who are weary and burdened, and I will give you rest."
                }
            ],
            "hindi": [
                {
                    "reference": "फिलिप्पियों 4:6-7",
                    "text": "किसी भी बात की चिन्ता मत करो, परन्तु हर परिस्थिति में प्रार्थना और विनती के द्वारा धन्यवाद के साथ अपनी विनतियाँ परमेश्वर के सामने प्रस्तुत करो।"
                }
            ]
        }
        return sample_verses.get(language, sample_verses["english"])
    except Exception as e:
        logging.error(f"Error fetching Bible verses: {e}")
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
        system_message = f"""You are Preacher.ai, a compassionate and wise AI assistant that provides biblical guidance.

Your role:
- Provide thoughtful, biblical guidance based on Scripture
- Always cite relevant Bible verses in your responses
- Be encouraging, loving, and spiritually uplifting
- Respond in {language}
- Keep responses between 150-300 words for optimal readability

Guidelines:
- Focus on practical application of biblical principles
- Use warm, pastoral tone
- Address spiritual concerns with empathy
- Include 1-3 relevant Bible verses with clear references
- Avoid denominational controversies
- Emphasize God's love, grace, and wisdom

When citing verses, reference them clearly in your response with format: [Book Chapter:Verse]

Example topics you help with:
- Finding peace in difficult times
- Understanding forgiveness
- Dealing with anxiety and worry
- Spiritual growth and faith
- Relationships and love
- Purpose and meaning in life"""

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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()