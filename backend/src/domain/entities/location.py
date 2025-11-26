"""
Domain Entity: Location
Represents a specific location within a construction project
Following DDD principles
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID, uuid4

from domain.value_objects.phase import Phase
from domain.value_objects.progress import Progress
from domain.entities.timeline import Timeline
from domain.exceptions.domain_exceptions import DomainException
from domain.events.location_events import LocationPhaseChanged, LocationProgressUpdated


@dataclass
class Location:
    """
    Location Entity
    Represents a monitored area in the construction project
    """

    id: UUID = field(default_factory=uuid4)
    name: str = None
    description: str = None
    location_type: str = None  # 'external', 'internal', 'technical'
    current_phase: Phase = None
    progress: Progress = None
    timeline: Timeline = None
    elements_detected: List[str] = field(default_factory=list)
    quality_score: int = 0  # 0-100
    last_photo_date: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _domain_events: List = field(default_factory=list, init=False)

    def __post_init__(self):
        """Initialize location with default values"""
        if self.timeline is None:
            self.timeline = Timeline()
        if self.progress is None:
            self.progress = Progress(percentage=0)
        if self.current_phase is None:
            self.current_phase = Phase(name="planning")

    def update_phase(self, new_phase: Phase) -> None:
        """
        Update the current construction phase
        Business Rule: Phase transitions must be valid
        """
        if self.current_phase and not self._is_valid_phase_transition(self.current_phase, new_phase):
            raise DomainException(
                f"Invalid phase transition from {self.current_phase.name} to {new_phase.name}"
            )

        old_phase = self.current_phase
        self.current_phase = new_phase
        self.updated_at = datetime.utcnow()

        # Add event to timeline
        self.timeline.add_event(
            event_type="phase_change",
            description=f"Phase changed from {old_phase.name if old_phase else 'none'} to {new_phase.name}",
            metadata={"old_phase": old_phase.name if old_phase else None, "new_phase": new_phase.name}
        )

        # Raise domain event
        self._raise_event(LocationPhaseChanged(
            location_id=self.id,
            old_phase=old_phase.name if old_phase else None,
            new_phase=new_phase.name,
            timestamp=self.updated_at
        ))

    def update_progress(self, new_progress: int, elements: List[str] = None) -> None:
        """
        Update location progress
        Business Rule: Progress must be between 0 and 100
        """
        if not 0 <= new_progress <= 100:
            raise DomainException(f"Progress must be between 0 and 100, got {new_progress}")

        old_progress = self.progress.percentage
        self.progress = Progress(
            percentage=new_progress,
            phase=self.current_phase.name if self.current_phase else None
        )

        if elements:
            self.elements_detected = elements

        self.updated_at = datetime.utcnow()

        # Add event to timeline
        self.timeline.add_event(
            event_type="progress_update",
            description=f"Progress updated from {old_progress}% to {new_progress}%",
            metadata={"old_progress": old_progress, "new_progress": new_progress, "elements": elements}
        )

        # Raise domain event if significant change (>5%)
        if abs(new_progress - old_progress) > 5:
            self._raise_event(LocationProgressUpdated(
                location_id=self.id,
                old_progress=old_progress,
                new_progress=new_progress,
                timestamp=self.updated_at
            ))

    def add_photo_analysis(self, photo_date: datetime, elements: List[str], quality_score: int) -> None:
        """
        Add photo analysis results
        Business Rule: Quality score must be between 0 and 100
        """
        if not 0 <= quality_score <= 100:
            raise DomainException(f"Quality score must be between 0 and 100, got {quality_score}")

        self.last_photo_date = photo_date
        self.elements_detected = elements
        self.quality_score = quality_score
        self.updated_at = datetime.utcnow()

        # Add event to timeline
        self.timeline.add_event(
            event_type="photo_analysis",
            description=f"Photo analyzed with quality score {quality_score}",
            metadata={"elements": elements, "quality_score": quality_score}
        )

    def _is_valid_phase_transition(self, current: Phase, new: Phase) -> bool:
        """
        Validate phase transitions based on construction logic
        """
        valid_transitions = {
            "planning": ["foundation", "structure"],
            "foundation": ["structure"],
            "structure": ["masonry", "installations"],
            "masonry": ["installations", "finishing"],
            "installations": ["finishing"],
            "finishing": ["completed"]
        }

        if current.name not in valid_transitions:
            return True  # Allow if current phase unknown

        return new.name in valid_transitions.get(current.name, [])

    def is_delayed(self, expected_progress: int) -> bool:
        """
        Check if location is delayed based on expected progress
        Business Rule: Delayed if actual < expected - 10% tolerance
        """
        return self.progress.percentage < (expected_progress * 0.9)

    def get_recommendations(self) -> List[str]:
        """Generate recommendations based on current state"""
        recommendations = []

        if self.quality_score < 70:
            recommendations.append(f"Quality issues detected. Current score: {self.quality_score}")

        if self.progress.percentage < 30 and self.current_phase.name != "planning":
            recommendations.append(f"Accelerate work on {self.name}")

        if not self.last_photo_date or (datetime.utcnow() - self.last_photo_date).days > 7:
            recommendations.append(f"Update photos for {self.name} - last update over 7 days ago")

        return recommendations

    def _raise_event(self, event) -> None:
        """Raise a domain event"""
        self._domain_events.append(event)

    def collect_events(self) -> List:
        """Collect and clear domain events"""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'location_type': self.location_type,
            'current_phase': self.current_phase.to_dict() if self.current_phase else None,
            'progress': self.progress.to_dict() if self.progress else None,
            'timeline': self.timeline.to_dict() if self.timeline else None,
            'elements_detected': self.elements_detected,
            'quality_score': self.quality_score,
            'last_photo_date': self.last_photo_date.isoformat() if self.last_photo_date else None,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'recommendations': self.get_recommendations()
        }
