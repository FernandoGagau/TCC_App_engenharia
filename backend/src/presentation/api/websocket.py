"""WebSocket API endpoints."""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi import APIRouter, Request
from loguru import logger
import redis.asyncio as redis

from infrastructure.websocket import ConnectionManager
from infrastructure.rate_limiter import RateLimiter, MessageRateLimiter
from application.services.chat_service import ChatService
from domain.chat.models import ChatSession, ChatMessage, MessageRole

# Initialize router
router = APIRouter(prefix="/ws", tags=["websocket"])

# Initialize services
connection_manager = ConnectionManager()
redis_client = None
rate_limiter = None
message_limiter = None
chat_service = ChatService()


async def init_redis():
    """Initialize Redis connection."""
    global redis_client, rate_limiter, message_limiter, connection_manager

    try:
        redis_client = await redis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()

        rate_limiter = RateLimiter(redis_client)
        message_limiter = MessageRateLimiter(redis_client)
        connection_manager.redis_client = redis_client

        logger.info("Redis connected for WebSocket services")
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Rate limiting disabled.")


async def get_current_user_from_token(token: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Get current user from token."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        from infrastructure.auth.jwt_service import jwt_service
        from domain.auth.models import User

        # Verify token
        payload = jwt_service.verify_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get user from database
        user = await User.find_one(User.user_id == user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return {
            "id": user.user_id,
            "email": user.email,
            "name": user.username
        }

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.websocket("/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time chat."""

    # Authenticate user
    try:
        user = await get_current_user_from_token(token)
        user_id = user["id"]
    except HTTPException:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Connect WebSocket
    connection_id = await connection_manager.connect(
        websocket, session_id, user_id
    )

    # Create or get session
    session = await chat_service.get_session(session_id)
    if not session:
        session = await chat_service.create_session(add_greeting=False)

    try:
        while True:
            # Receive message
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await connection_manager.send_error(
                    connection_id,
                    "Invalid JSON format"
                )
                continue

            message_type = data.get("type", "message")

            # Handle different message types
            if message_type == "ping":
                await connection_manager.send_message(connection_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })

            elif message_type == "message":
                # Check rate limit
                if rate_limiter and not await rate_limiter.check_rate_limit(user_id):
                    await connection_manager.send_error(
                        connection_id,
                        "Rate limit exceeded. Please wait before sending more messages.",
                        "RATE_LIMIT"
                    )
                    continue

                # Process message
                try:
                    response = await chat_service.process_message(
                        data,
                        session_id,
                        user_id
                    )

                    # Stream response if requested
                    if response.get("stream"):
                        await stream_response(
                            connection_manager,
                            connection_id,
                            response
                        )
                    else:
                        await connection_manager.send_message(connection_id, {
                            "type": "message",
                            "message_id": response["message_id"],
                            "content": response["content"],
                            "metadata": response.get("metadata", {}),
                            "timestamp": datetime.utcnow().isoformat()
                        })

                except Exception as e:
                    logger.error(f"Message processing error: {e}")
                    await connection_manager.send_error(
                        connection_id,
                        "Failed to process message",
                        "PROCESSING_ERROR"
                    )

            elif message_type == "typing":
                # Broadcast typing indicator to other connections
                await connection_manager.send_to_session(
                    session_id,
                    {
                        "type": "typing",
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

            elif message_type == "reaction":
                # Handle message reaction
                message_id = data.get("message_id")
                helpful = data.get("helpful")
                rating = data.get("rating")

                if message_id:
                    success = await chat_service.add_reaction(
                        message_id, helpful, rating
                    )

                    await connection_manager.send_message(connection_id, {
                        "type": "reaction_saved",
                        "message_id": message_id,
                        "success": success,
                        "timestamp": datetime.utcnow().isoformat()
                    })

            else:
                await connection_manager.send_error(
                    connection_id,
                    f"Unknown message type: {message_type}",
                    "UNKNOWN_TYPE"
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await connection_manager.disconnect(connection_id)
        await chat_service.update_session_activity(session_id)


async def stream_response(
    manager: ConnectionManager,
    connection_id: str,
    response: Dict[str, Any]
):
    """Stream response in chunks."""
    message_id = response["message_id"]
    chunks = response.get("chunks", [])

    # Send stream start
    await manager.stream_start(connection_id, message_id)

    # Send chunks with delay for visual effect
    for chunk in chunks:
        await manager.stream_chunk(connection_id, message_id, chunk)
        await asyncio.sleep(0.05)  # 50ms delay between chunks

    # Send stream end
    await manager.stream_end(
        connection_id,
        message_id,
        response.get("metadata", {})
    )


# REST API Endpoints for session management
api_router = APIRouter(prefix="/api/chat", tags=["chat"])


@api_router.get("/sessions")
async def get_sessions(
    user: Dict = Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = Query(10, le=100)
):
    """Get user's chat sessions."""
    sessions = await chat_service.get_user_sessions(
        user["id"],
        status=status,
        limit=limit
    )

    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "project_id": s.project_id,
                "started_at": s.started_at.isoformat(),
                "last_activity": s.last_activity.isoformat(),
                "status": s.status,
                "settings": s.settings.dict()
            }
            for s in sessions
        ]
    }


@api_router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: Dict = Depends(get_current_user)
):
    """Get session details."""
    session = await chat_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    message_count = await chat_service.get_message_count(session_id)

    return {
        "session_id": session.session_id,
        "project_id": session.project_id,
        "started_at": session.started_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "status": session.status,
        "settings": session.settings.dict(),
        "metadata": session.metadata.dict(),
        "message_count": message_count
    }


@api_router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    user: Dict = Depends(get_current_user),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0)
):
    """Get session messages."""
    session = await chat_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = await chat_service.get_session_messages(
        session_id, limit, offset
    )

    return {
        "messages": [
            {
                "message_id": m.message_id,
                "timestamp": m.timestamp.isoformat(),
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata.dict(),
                "reactions": m.reactions.dict()
            }
            for m in messages
        ],
        "total": await chat_service.get_message_count(session_id),
        "limit": limit,
        "offset": offset
    }


@api_router.delete("/sessions/{session_id}")
async def close_session(
    session_id: str,
    user: Dict = Depends(get_current_user)
):
    """Close a chat session."""
    session = await chat_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    success = await chat_service.close_session(session_id)

    return {"success": success, "session_id": session_id}


@api_router.post("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    user: Dict = Depends(get_current_user),
    format: str = Query("json", regex="^(json|csv|txt)$")
):
    """Export session conversation."""
    session = await chat_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    export_data = await chat_service.export_session(session_id, format)

    return export_data


@api_router.get("/quota")
async def get_quota(
    user: Dict = Depends(get_current_user)
):
    """Get user's rate limit quota."""
    if not rate_limiter:
        return {"message": "Rate limiting not enabled"}

    quota = await rate_limiter.get_remaining_quota(user["id"])

    if message_limiter:
        message_quotas = await message_limiter.get_all_quotas(user["id"])
        quota["message_quotas"] = message_quotas

    return quota


# WebSocket connection statistics endpoint
@api_router.get("/stats")
async def get_stats():
    """Get WebSocket connection statistics."""
    return {
        "total_connections": connection_manager.get_connection_count(),
        "timestamp": datetime.utcnow().isoformat()
    }


# Initialize on startup
async def startup_event():
    """Initialize services on startup."""
    await init_redis()
    logger.info("WebSocket API initialized")


# Shutdown cleanup
async def shutdown_event():
    """Clean up on shutdown."""
    if redis_client:
        await redis_client.close()
    logger.info("WebSocket API shutdown")