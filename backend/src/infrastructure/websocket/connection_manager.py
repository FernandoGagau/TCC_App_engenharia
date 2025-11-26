"""WebSocket connection manager."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Optional, Set, Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
from loguru import logger

from domain.chat.models import ConnectionState


class ConnectionManager:
    """Manage WebSocket connections and message routing."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.connection_states: Dict[str, ConnectionState] = {}
        self.redis_client = redis_client
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        connection_id: Optional[str] = None
    ) -> str:
        """Accept new WebSocket connection."""
        await websocket.accept()

        connection_id = connection_id or str(uuid4())

        # Store connection
        self.active_connections[connection_id] = websocket

        # Track session connections
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)

        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        # Create connection state
        state = ConnectionState(
            connection_id=connection_id,
            session_id=session_id,
            user_id=user_id
        )
        self.connection_states[connection_id] = state

        # Store in Redis if available
        if self.redis_client:
            await self._store_connection_redis(state)

        # Start heartbeat
        self.heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat_loop(connection_id, websocket)
        )

        logger.info(f"WebSocket connected: {connection_id} for session {session_id}")

        # Send connection confirmation
        await self.send_message(connection_id, {
            "type": "connected",
            "connection_id": connection_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        return connection_id

    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket connection."""
        if connection_id not in self.active_connections:
            return

        # Cancel heartbeat
        if connection_id in self.heartbeat_tasks:
            self.heartbeat_tasks[connection_id].cancel()
            del self.heartbeat_tasks[connection_id]

        # Get connection state
        state = self.connection_states.get(connection_id)

        if state:
            # Remove from session connections
            if state.session_id in self.session_connections:
                self.session_connections[state.session_id].discard(connection_id)
                if not self.session_connections[state.session_id]:
                    del self.session_connections[state.session_id]

            # Remove from user connections
            if state.user_id in self.user_connections:
                self.user_connections[state.user_id].discard(connection_id)
                if not self.user_connections[state.user_id]:
                    del self.user_connections[state.user_id]

            # Remove from Redis
            if self.redis_client:
                await self._remove_connection_redis(connection_id)

        # Remove connection
        del self.active_connections[connection_id]
        if connection_id in self.connection_states:
            del self.connection_states[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """Send message to specific connection."""
        if websocket := self.active_connections.get(connection_id):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                await self.disconnect(connection_id)

    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to all connections in a session."""
        if session_id in self.session_connections:
            for connection_id in self.session_connections[session_id]:
                await self.send_message(connection_id, message)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all connections of a user."""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                await self.send_message(connection_id, message)

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set[str]] = None):
        """Broadcast message to all connections."""
        exclude = exclude or set()
        for connection_id in self.active_connections:
            if connection_id not in exclude:
                await self.send_message(connection_id, message)

    async def stream_start(self, connection_id: str, message_id: str):
        """Start streaming response."""
        await self.send_message(connection_id, {
            "type": "stream_start",
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def stream_chunk(self, connection_id: str, message_id: str, content: str):
        """Send stream chunk."""
        await self.send_message(connection_id, {
            "type": "stream_chunk",
            "message_id": message_id,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def stream_end(
        self,
        connection_id: str,
        message_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """End streaming response."""
        await self.send_message(connection_id, {
            "type": "stream_end",
            "message_id": message_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_error(self, connection_id: str, error: str, code: Optional[str] = None):
        """Send error message."""
        await self.send_message(connection_id, {
            "type": "error",
            "error": error,
            "code": code,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)

    def get_session_connections(self, session_id: str) -> int:
        """Get number of connections for a session."""
        return len(self.session_connections.get(session_id, set()))

    def get_user_connections(self, user_id: str) -> int:
        """Get number of connections for a user."""
        return len(self.user_connections.get(user_id, set()))

    async def _heartbeat_loop(self, connection_id: str, websocket: WebSocket):
        """Send periodic heartbeat to keep connection alive."""
        try:
            while connection_id in self.active_connections:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds

                if connection_id in self.active_connections:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    # Update last ping in state
                    if state := self.connection_states.get(connection_id):
                        state.last_ping = datetime.utcnow()
                        if self.redis_client:
                            await self._store_connection_redis(state)
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"Heartbeat error for {connection_id}: {e}")
            await self.disconnect(connection_id)

    async def _store_connection_redis(self, state: ConnectionState):
        """Store connection state in Redis."""
        if not self.redis_client:
            return

        try:
            key = f"ws:connection:{state.connection_id}"
            await self.redis_client.hset(
                key,
                mapping=state.to_dict()
            )
            await self.redis_client.expire(key, 3600)  # 1 hour TTL

            # Add to session set
            session_key = f"ws:session:{state.session_id}"
            await self.redis_client.sadd(session_key, state.connection_id)
            await self.redis_client.expire(session_key, 3600)

            # Add to user set
            user_key = f"ws:user:{state.user_id}"
            await self.redis_client.sadd(user_key, state.connection_id)
            await self.redis_client.expire(user_key, 3600)
        except Exception as e:
            logger.error(f"Redis storage error: {e}")

    async def _remove_connection_redis(self, connection_id: str):
        """Remove connection state from Redis."""
        if not self.redis_client:
            return

        try:
            state = self.connection_states.get(connection_id)
            if not state:
                return

            # Remove connection key
            await self.redis_client.delete(f"ws:connection:{connection_id}")

            # Remove from session set
            await self.redis_client.srem(
                f"ws:session:{state.session_id}",
                connection_id
            )

            # Remove from user set
            await self.redis_client.srem(
                f"ws:user:{state.user_id}",
                connection_id
            )
        except Exception as e:
            logger.error(f"Redis removal error: {e}")

    async def recover_from_redis(self):
        """Recover connection states from Redis after restart."""
        if not self.redis_client:
            return

        try:
            # Find all connection keys
            keys = await self.redis_client.keys("ws:connection:*")

            for key in keys:
                data = await self.redis_client.hgetall(key)
                if data:
                    # Mark as inactive since WebSocket is gone
                    data["active"] = False
                    state = ConnectionState.from_dict(data)
                    self.connection_states[state.connection_id] = state

                    logger.info(f"Recovered connection state: {state.connection_id}")
        except Exception as e:
            logger.error(f"Redis recovery error: {e}")