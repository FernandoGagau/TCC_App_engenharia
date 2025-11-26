"""
Domain Entity: Timeline
Represents the chronological events of a project or location
Following DDD principles
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from domain.exceptions.domain_exceptions import DomainException


@dataclass
class TimelineEvent:
    """
    Value Object representing a single timeline event
    """
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: str = None  # 'phase_change', 'progress_update', 'photo_analysis', 'milestone'
    description: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    confidence_score: Optional[float] = None  # For AI-generated events

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'description': self.description,
            'metadata': self.metadata,
            'user_id': self.user_id,
            'confidence_score': self.confidence_score
        }


@dataclass
class Timeline:
    """
    Timeline Entity
    Tracks chronological events for auditing and history
    """

    id: UUID = field(default_factory=uuid4)
    events: List[TimelineEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_event(
        self,
        event_type: str,
        description: str,
        metadata: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        confidence_score: Optional[float] = None
    ) -> TimelineEvent:
        """
        Add a new event to the timeline
        Business Rule: Events are immutable once added
        """
        if not event_type or not description:
            raise DomainException("Event type and description are required")

        event = TimelineEvent(
            event_type=event_type,
            description=description,
            metadata=metadata or {},
            user_id=user_id,
            confidence_score=confidence_score
        )

        self.events.append(event)
        self.updated_at = datetime.utcnow()

        return event

    def get_events_by_type(self, event_type: str) -> List[TimelineEvent]:
        """Get all events of a specific type"""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[TimelineEvent]:
        """Get events within a date range"""
        return [
            e for e in self.events
            if start_date <= e.timestamp <= end_date
        ]

    def get_latest_event(self, event_type: Optional[str] = None) -> Optional[TimelineEvent]:
        """Get the most recent event, optionally filtered by type"""
        filtered_events = self.events
        if event_type:
            filtered_events = [e for e in self.events if e.event_type == event_type]

        if not filtered_events:
            return None

        return max(filtered_events, key=lambda e: e.timestamp)

    def get_milestones(self) -> List[TimelineEvent]:
        """Get all milestone events"""
        return self.get_events_by_type('milestone')

    def calculate_duration(self) -> Optional[int]:
        """Calculate duration in days from first to last event"""
        if not self.events:
            return None

        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        duration = sorted_events[-1].timestamp - sorted_events[0].timestamp
        return duration.days

    def get_event_frequency(self) -> Dict[str, int]:
        """Get frequency count of each event type"""
        frequency = {}
        for event in self.events:
            frequency[event.event_type] = frequency.get(event.event_type, 0) + 1
        return frequency

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'id': str(self.id),
            'events': [e.to_dict() for e in self.events],
            'event_count': len(self.events),
            'duration_days': self.calculate_duration(),
            'event_frequency': self.get_event_frequency(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
