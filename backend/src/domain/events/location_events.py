"""
Domain Events: Location
Events raised by Location entity
Following DDD and Event Sourcing principles
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


@dataclass
class LocationEvent:
    """Base class for location events"""
    location_id: UUID
    timestamp: datetime
    event_type: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__


@dataclass
class LocationPhaseChanged(LocationEvent):
    """Event raised when location phase changes"""
    new_phase: str
    old_phase: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class LocationProgressUpdated(LocationEvent):
    """Event raised when location progress is updated"""
    old_progress: int
    new_progress: int
    elements_detected: Optional[List[str]] = None
    quality_score: Optional[int] = None


@dataclass
class LocationPhotoAnalyzed(LocationEvent):
    """Event raised when a photo is analyzed for location"""
    photo_id: str
    elements_detected: List[str]
    phase_detected: str
    progress_detected: int
    quality_score: int
    confidence: float


@dataclass
class LocationQualityIssueDetected(LocationEvent):
    """Event raised when quality issue is detected"""
    issue_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    recommendations: Optional[List[str]] = None