"""
Domain Entity: Project
Aggregate Root for construction project
Following DDD principles
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from domain.value_objects.project_info import ProjectInfo
from domain.value_objects.progress import Progress
from domain.entities.location import Location
from domain.entities.timeline import Timeline
from domain.exceptions.domain_exceptions import DomainException
from domain.events.project_events import ProjectCreated, LocationAdded, ProjectProgressUpdated


@dataclass
class Project:
    """
    Project Aggregate Root
    Central entity for construction project management
    """

    id: UUID = field(default_factory=uuid4)
    info: ProjectInfo = None
    locations: List[Location] = field(default_factory=list)
    timeline: Timeline = None
    overall_progress: Progress = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _domain_events: List = field(default_factory=list, init=False)

    def __post_init__(self):
        """Initialize project with default values"""
        if self.timeline is None:
            self.timeline = Timeline()
        if self.overall_progress is None:
            self.overall_progress = Progress(percentage=0)

        # Raise domain event for project creation
        if self.info:
            self._raise_event(ProjectCreated(
                aggregate_id=self.id,
                project_info=self.info,
                timestamp=self.created_at
            ))

    def add_location(self, location: Location) -> None:
        """
        Add a new location to the project
        Business Rule: Maximum 3 locations allowed
        """
        if len(self.locations) >= 3:
            raise DomainException(
                "Maximum 3 locations allowed per project. "
                "Current locations: " + ", ".join([loc.name for loc in self.locations])
            )

        if any(loc.id == location.id for loc in self.locations):
            raise DomainException(f"Location with ID {location.id} already exists")

        self.locations.append(location)
        self.updated_at = datetime.utcnow()

        # Raise domain event
        self._raise_event(LocationAdded(
            aggregate_id=self.id,
            location_id=location.id,
            location_name=location.name,
            timestamp=self.updated_at
        ))

    def update_overall_progress(self) -> None:
        """
        Calculate and update overall project progress
        Business Rule: Weighted average of all locations
        """
        if not self.locations:
            self.overall_progress = Progress(percentage=0)
            return

        # Calculate weighted average (40% external, 30% internal, 30% technical)
        weights = [0.4, 0.3, 0.3]
        total_progress = 0

        for i, location in enumerate(self.locations[:3]):
            weight = weights[i] if i < len(weights) else 0.33
            total_progress += location.progress.percentage * weight

        old_progress = self.overall_progress.percentage
        new_progress = int(total_progress)

        self.overall_progress = Progress(
            percentage=new_progress,
            phase=self._determine_overall_phase(),
            quality_score=self._calculate_quality_score()
        )

        self.updated_at = datetime.utcnow()

        # Raise event if progress changed
        if old_progress != new_progress:
            self._raise_event(ProjectProgressUpdated(
                aggregate_id=self.id,
                old_progress=old_progress,
                new_progress=new_progress,
                timestamp=self.updated_at
            ))

    def _determine_overall_phase(self) -> str:
        """Determine the predominant phase across all locations"""
        if not self.locations:
            return "planning"

        phases = [loc.current_phase.name for loc in self.locations if loc.current_phase]
        if not phases:
            return "planning"

        # Return most common phase
        return max(set(phases), key=phases.count)

    def _calculate_quality_score(self) -> int:
        """Calculate average quality score across all locations"""
        if not self.locations:
            return 0

        quality_scores = [loc.quality_score for loc in self.locations if loc.quality_score]
        if not quality_scores:
            return 0

        return int(sum(quality_scores) / len(quality_scores))

    def get_location_by_id(self, location_id: str) -> Optional[Location]:
        """Get a specific location by ID"""
        return next((loc for loc in self.locations if loc.id == location_id), None)

    def is_delayed(self) -> bool:
        """
        Check if project is delayed based on timeline
        Business Rule: Delayed if current progress < expected progress
        """
        if not self.info or not self.info.start_date or not self.info.expected_completion:
            return False

        days_elapsed = (datetime.utcnow().date() - self.info.start_date).days
        total_days = (self.info.expected_completion - self.info.start_date).days

        if total_days <= 0:
            return False

        expected_progress = (days_elapsed / total_days) * 100
        return self.overall_progress.percentage < (expected_progress * 0.9)  # 10% tolerance

    def get_recommendations(self) -> List[str]:
        """Generate recommendations based on current project state"""
        recommendations = []

        if self.is_delayed():
            recommendations.append("Project is behind schedule. Consider allocating more resources.")

        # Check each location
        for location in self.locations:
            if location.progress.percentage < 30:
                recommendations.append(f"Accelerate work on {location.name}")
            elif location.quality_score and location.quality_score < 70:
                recommendations.append(f"Quality issues detected in {location.name}")

        if not recommendations:
            recommendations.append("Project is progressing well. Maintain current pace.")

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
            'info': self.info.to_dict() if self.info else None,
            'locations': [loc.to_dict() for loc in self.locations],
            'timeline': self.timeline.to_dict() if self.timeline else None,
            'overall_progress': self.overall_progress.to_dict() if self.overall_progress else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_delayed': self.is_delayed(),
            'recommendations': self.get_recommendations()
        }
