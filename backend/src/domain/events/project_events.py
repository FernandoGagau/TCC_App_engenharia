"""
Domain Events: Project
Events raised by Project aggregate
Following DDD and Event Sourcing principles
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.value_objects.project_info import ProjectInfo


@dataclass
class DomainEvent:
    """Base class for all domain events"""
    aggregate_id: UUID
    timestamp: datetime
    event_type: Optional[str] = field(default=None, init=False)
    version: int = field(default=1)

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__


@dataclass
class ProjectCreated(DomainEvent):
    """Event raised when a new project is created"""
    project_info: Optional[ProjectInfo] = None


@dataclass
class LocationAdded(DomainEvent):
    """Event raised when a location is added to project"""
    location_id: Optional[UUID] = None
    location_name: Optional[str] = None
    location_type: Optional[str] = None


@dataclass
class ProjectProgressUpdated(DomainEvent):
    """Event raised when project progress is updated"""
    old_progress: Optional[int] = None
    new_progress: Optional[int] = None
    phase: Optional[str] = None


@dataclass
class ProjectDelayed(DomainEvent):
    """Event raised when project is detected as delayed"""
    expected_progress: int = 0
    actual_progress: int = 0
    delay_days: int = 0
    recommendations: Optional[list] = field(default_factory=list)


@dataclass
class ProjectCompleted(DomainEvent):
    """Event raised when project reaches completion"""
    completion_date: datetime = field(default_factory=lambda: datetime.utcnow())
    final_progress: int = 100
    total_duration_days: int = 0
