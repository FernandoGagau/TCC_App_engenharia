"""Chat domain models."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4
from beanie import Document, Indexed
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Chat session status."""
    ACTIVE = "active"
    IDLE = "idle"
    CLOSED = "closed"


class MessageRole(str, Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SessionMetadata(BaseModel):
    """Session metadata."""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    client_version: Optional[str] = None


class SessionSettings(BaseModel):
    """Session settings."""
    model_preference: Optional[str] = "grok-fast"
    language: str = "pt-BR"
    stream_responses: bool = True


class MessageMetadata(BaseModel):
    """Message metadata."""
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    agent_used: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)


class MessageReactions(BaseModel):
    """Message reactions."""
    helpful: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


class ChatSession(Document):
    """Chat session document."""

    session_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    project_id: Optional[str] = None
    user_id: Indexed(str)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    settings: SessionSettings = Field(default_factory=SessionSettings)
    total_tokens: int = Field(default=0)  # Total de tokens usados nesta sessão
    total_cost: float = Field(default=0.0)  # Custo total da sessão em USD

    class Settings:
        name = "chat_sessions"
        indexes = [
            "session_id",
            "user_id",
            [("user_id", 1), ("status", 1)],
            [("project_id", 1), ("started_at", -1)]
        ]

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def close(self):
        """Close the session."""
        self.status = SessionStatus.CLOSED
        self.update_activity()


class ChatMessage(Document):
    """Chat message document."""

    message_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    session_id: Indexed(str)
    project_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    role: MessageRole
    content: str
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    reactions: MessageReactions = Field(default_factory=MessageReactions)

    class Settings:
        name = "chat_messages"
        indexes = [
            "message_id",
            "session_id",
            [("session_id", 1), ("timestamp", 1)],
            [("project_id", 1), ("timestamp", -1)]
        ]

    def add_reaction(self, helpful: Optional[bool] = None, rating: Optional[int] = None):
        """Add reaction to message."""
        if helpful is not None:
            self.reactions.helpful = helpful
        if rating is not None:
            self.reactions.rating = rating


class ConnectionState(BaseModel):
    """Connection state for Redis storage."""
    connection_id: str
    session_id: str
    user_id: str
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_ping: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "connection_id": self.connection_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "active": self.active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionState":
        """Create from dictionary."""
        data["connected_at"] = datetime.fromisoformat(data["connected_at"])
        data["last_ping"] = datetime.fromisoformat(data["last_ping"])
        return cls(**data)