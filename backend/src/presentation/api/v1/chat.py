"""
Chat API Endpoints
RESTful API for conversational agent
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import base64
import json
import logging

from application.services.chat_service import ChatService
from infrastructure.dependencies import get_chat_service

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Chat request model"""
    session_id: Optional[str] = Field(default=None, description="Session ID (optional, will be created if not provided)")
    message: str = Field(..., description="User message")
    attachments: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of attachments (images, documents)"
    )


class ChatResponse(BaseModel):
    """Chat response model"""
    session_id: str
    response: str
    state: str
    data: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionResponse(BaseModel):
    """Session response model"""
    session_id: str
    project_id: Optional[str]
    state: str
    message_count: int
    created_at: datetime
    updated_at: datetime


@router.post("/start", response_model=SessionResponse)
async def start_chat(
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Start new chat session

    Initializes a new conversational session for project documentation.
    Returns session ID without automatic greeting (session is initialized on first message).
    """
    try:
        # Create session without automatic greeting
        session = await chat_service.create_session(add_greeting=False)

        return SessionResponse(
            session_id=session.id,
            project_id=session.metadata.get("project_id") if session.metadata else None,
            state=session.status,
            message_count=len(session.messages),
            created_at=session.started_at,
            updated_at=session.last_activity
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Send message to chat

    Process user message and return agent response.
    Creates session automatically on first message if session_id not provided.
    Supports text messages and attachments (images/documents).
    """
    try:
        # Create new session if not provided (session creation on first message)
        if not request.session_id:
            session = await chat_service.create_session(add_greeting=False)
            request.session_id = session.id

        # Save USER message to MongoDB FIRST
        logger.info(f"📝 v1/chat API: Saving USER message to MongoDB: {request.message[:50]}...")
        await chat_service.history_manager.add_message(
            session_id=request.session_id,
            role='user',
            content=request.message,
            attachments=request.attachments or []
        )
        logger.info(f"✅ v1/chat API: USER message saved to MongoDB")

        # Process message
        result = await chat_service.process_message(
            session_id=request.session_id,
            message=request.message,
            attachments=request.attachments
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return ChatResponse(
            session_id=result["session_id"],
            response=result["response"],
            state=result["state"],
            data=result.get("data"),
            next_action=result.get("next_action")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(
    session_id: Optional[str] = Form(default=None),
    message: str = Form(default="Enviando arquivo"),
    file: UploadFile = File(...),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Upload file with message

    Upload image or document file with optional message.
    Creates session automatically if session_id not provided.
    Supports: JPG, PNG, PDF, DOCX
    """
    try:
        # Create new session if not provided (session creation on first message)
        if not session_id:
            session = await chat_service.create_session(add_greeting=False)
            session_id = session.id
        # Validate file type
        allowed_extensions = [".jpg", ".jpeg", ".png", ".pdf", ".docx"]
        file_ext = "." + file.filename.split(".")[-1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not supported. Allowed: {allowed_extensions}"
            )
        
        # Read file content
        content = await file.read()
        
        # Encode to base64 for images
        if file_ext in [".jpg", ".jpeg", ".png"]:
            file_data = base64.b64encode(content).decode('utf-8')
            file_type = "image"
        else:
            # Save document temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                tmp.write(content)
                file_data = tmp.name
            file_type = "document"
        
        # Create attachment
        attachment = {
            "type": file_type,
            "filename": file.filename,
            "data": file_data,
            "size": len(content),
            "mime_type": file.content_type
        }
        
        # Process with chat service
        result = await chat_service.process_message(
            session_id=session_id,
            message=message,
            attachments=[attachment]
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return ChatResponse(
            session_id=result["session_id"],
            response=result["response"],
            state=result["state"],
            data=result.get("data"),
            next_action=result.get("next_action")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get session details
    
    Retrieve information about a specific chat session.
    """
    try:
        session = await chat_service.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(
            session_id=session.id,
            project_id=session.metadata.get("project_id") if session.metadata else None,
            state=session.status,
            message_count=len(session.messages),
            created_at=session.started_at,
            updated_at=session.last_activity
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/messages")
async def get_messages(
    session_id: str,
    limit: int = 50,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get session messages
    
    Retrieve message history for a session.
    """
    try:
        session = await chat_service.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get last N messages
        messages = session.messages[-limit:] if len(session.messages) > limit else session.messages
        
        return {
            "session_id": session_id,
            "total_messages": len(session.messages),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    List all chat sessions

    Get a list of all active chat sessions.
    """
    try:
        sessions = await chat_service.list_sessions()

        return {
            "total": len(sessions),
            "sessions": sessions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session_with_messages(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get session details with messages (for SessionHistory frontend)

    Retrieve session information including all messages.
    """
    try:
        session = await chat_service.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Return format expected by frontend
        return {
            "session": {
                "id": session.id,
                "user_id": session.user_id,
                "project_name": session.project_name,
                "started_at": session.started_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "status": session.status,
                "total_tokens": session.total_tokens,
                "total_cost": session.total_cost,
                "metadata": session.metadata
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "attachments": msg.attachments or [],
                    "metadata": msg.metadata or {},
                    "tokens_used": msg.tokens_used
                }
                for msg in session.messages
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/reset")
async def reset_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Reset chat session

    Clear session and start over.
    """
    try:
        logger.info(f"Resetting session: {session_id}")
        session = await chat_service.get_session(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")

        # Reset session
        logger.info(f"Clearing session data for: {session_id}")
        session.messages.clear()
        session.state = "initial"
        session.project_id = None
        if hasattr(session, 'context') and session.context:
            session.context.clear()
        session.updated_at = datetime.utcnow()

        # Reinitialize interview state if it exists
        try:
            from application.services.chat_service import InterviewState, ChatMessage

            # Reset interview state
            if hasattr(chat_service, 'interview_states'):
                logger.info(f"Reinitializing interview state for: {session_id}")
                chat_service.interview_states[session_id] = InterviewState()

                # Add initial greeting
                greeting_text = chat_service.interview_states[session_id].get_next_question()
                greeting = ChatMessage(
                    role="assistant",
                    content=greeting_text
                )
                session.messages.append(greeting)
                session.state = "interviewing"
                logger.info(f"Interview state initialized for: {session_id}")
            else:
                logger.warning(f"No interview_states attribute in chat_service")
                session.state = "ready"
        except Exception as e:
            # If interview state fails, just start with clean session
            logger.error(f"Error initializing interview state for {session_id}: {str(e)}", exc_info=True)
            session.state = "ready"

        logger.info(f"Session reset successfully: {session_id}, state: {session.state}")
        return {
            "message": "Session reset successfully",
            "session_id": session_id,
            "state": session.state
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))