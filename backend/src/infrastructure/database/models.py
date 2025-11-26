"""
MongoDB Document Models using Beanie ODM
Following Domain-Driven Design principles
"""

from beanie import Document, Indexed
from pydantic import Field, BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"


class MessageRole(str, Enum):
    """Message role enum"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProjectType(str, Enum):
    """Project type enum"""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    REFORM = "reform"


class FileModel(Document):
    """File document model for storing file metadata"""
    file_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    filename: str
    content_type: str
    size: int
    path: str
    bucket: Optional[str] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "files"
        indexes = [
            "file_id",
            "project_id",
            "session_id",
            "created_at"
        ]


class SessionModel(Document):
    """Session document model"""
    session_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    total_tokens: int = Field(default=0)
    total_cost: float = Field(default=0.0)

    class Settings:
        name = "sessions"
        indexes = [
            "user_id",
            [("created_at", -1)],
            [("status", 1), ("created_at", -1)]
        ]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class AttachmentModel(BaseModel):
    """Attachment subdocument"""
    filename: str
    content_type: str
    size: int
    url: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)


class MessageModel(Document):
    """Message document model"""
    session_id: Indexed(str)
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attachments: List[AttachmentModel] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    class Settings:
        name = "messages"
        indexes = [
            [("session_id", 1), ("timestamp", -1)],
            "timestamp"
        ]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class LocationModel(BaseModel):
    """Location subdocument"""
    location_id: str = Field(default_factory=lambda: str(uuid4()))
    location_name: str
    location_type: Optional[str] = None
    current_phase: Optional[str] = None
    progress: int = 0
    last_update: datetime = Field(default_factory=datetime.utcnow)
    coordinates: Optional[Dict[str, float]] = None
    cameras: List[str] = Field(default_factory=list)


class ProjectModel(Document):
    """Project document model"""
    project_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    project_name: str
    project_type: ProjectType
    address: Optional[str] = None
    responsible_engineer: Optional[str] = None
    responsible_crea: Optional[str] = None
    start_date: Optional[datetime] = None
    expected_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    current_phase: Optional[str] = None
    progress_percentage: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    bim_model_url: Optional[str] = None
    locations: List[LocationModel] = Field(default_factory=list)
    budget: Optional[float] = None
    total_area_m2: Optional[float] = None
    number_of_floors: Optional[int] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "projects"
        indexes = [
            "project_type",
            [("created_at", -1)],
            [("progress_percentage", 1)],
            "responsible_engineer"
        ]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class DetectedElement(BaseModel):
    """Detected element subdocument"""
    element_type: str
    confidence: float
    bounding_box: Optional[Dict[str, float]] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ImageAnalysisModel(Document):
    """Image analysis document model"""
    analysis_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: Indexed(str)
    location_id: Optional[str] = None
    image_url: str
    thumbnail_url: Optional[str] = None
    analysis_date: datetime = Field(default_factory=datetime.utcnow)
    capture_date: Optional[datetime] = None
    detected_phase: Optional[str] = None
    detected_elements: List[DetectedElement] = Field(default_factory=list)
    confidence_score: float = 0.0
    quality_score: Optional[int] = None
    safety_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    camera_id: Optional[str] = None
    weather_conditions: Optional[str] = None

    class Settings:
        name = "image_analysis"
        indexes = [
            [("project_id", 1), ("analysis_date", -1)],
            "location_id",
            "detected_phase",
            [("quality_score", -1)]
        ]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class EventModel(Document):
    """Event sourcing document model"""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    aggregate_id: Indexed(str)
    event_type: Indexed(str)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_data: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "events"
        indexes = [
            [("aggregate_id", 1), ("timestamp", -1)],
            [("event_type", 1), ("timestamp", -1)],
            "correlation_id"
        ]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# Query helpers
class QueryHelpers:
    """Helper methods for common queries"""

    @staticmethod
    async def get_active_sessions(user_id: Optional[str] = None) -> List[SessionModel]:
        """Get active sessions"""
        query = {"status": SessionStatus.ACTIVE}
        if user_id:
            query["user_id"] = user_id
        return await SessionModel.find(query).sort("-created_at").to_list()

    @staticmethod
    async def get_session_messages(session_id: str, limit: int = 100) -> List[MessageModel]:
        """Get messages for a session"""
        return await MessageModel.find(
            {"session_id": session_id}
        ).sort("timestamp").limit(limit).to_list()

    @staticmethod
    async def get_project_analysis(
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ImageAnalysisModel]:
        """Get image analysis for a project"""
        query = {"project_id": project_id}
        if start_date and end_date:
            query["analysis_date"] = {"$gte": start_date, "$lte": end_date}
        return await ImageAnalysisModel.find(query).sort("-analysis_date").to_list()

    @staticmethod
    async def get_project_events(aggregate_id: str) -> List[EventModel]:
        """Get events for an aggregate"""
        return await EventModel.find(
            {"aggregate_id": aggregate_id}
        ).sort("timestamp").to_list()