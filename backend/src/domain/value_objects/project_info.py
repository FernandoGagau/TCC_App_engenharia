"""
Value Object: ProjectInfo
Immutable object containing project metadata
Following DDD principles
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from domain.exceptions.domain_exceptions import DomainException


@dataclass(frozen=True)
class ProjectInfo:
    """
    Project Information Value Object
    Contains immutable project metadata
    """

    project_name: str
    project_type: str  # 'residential', 'commercial', 'industrial', 'reform'
    address: str
    responsible_engineer: Optional[str] = None
    responsible_crea: Optional[str] = None
    start_date: Optional[date] = None
    expected_completion: Optional[date] = None
    budget: Optional[float] = None
    total_area_m2: Optional[float] = None
    number_of_floors: Optional[int] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None

    def __post_init__(self):
        """Validate value object creation"""
        if not self.project_name:
            raise DomainException("Project name is required")

        if not self.project_type:
            raise DomainException("Project type is required")

        valid_types = ['residential', 'commercial', 'industrial', 'reform', 'infrastructure']
        if self.project_type not in valid_types:
            raise DomainException(
                f"Invalid project type. Must be one of: {', '.join(valid_types)}"
            )

        if not self.address:
            raise DomainException("Project address is required")

        # Validate dates if provided
        if self.start_date and self.expected_completion:
            if self.expected_completion < self.start_date:
                raise DomainException("Expected completion cannot be before start date")

        # Validate numeric values if provided
        if self.budget is not None and self.budget < 0:
            raise DomainException("Budget cannot be negative")

        if self.total_area_m2 is not None and self.total_area_m2 <= 0:
            raise DomainException("Total area must be positive")

        if self.number_of_floors is not None and self.number_of_floors <= 0:
            raise DomainException("Number of floors must be positive")

    def calculate_duration_days(self) -> Optional[int]:
        """Calculate project duration in days"""
        if not self.start_date or not self.expected_completion:
            return None
        return (self.expected_completion - self.start_date).days

    def is_active(self) -> bool:
        """Check if project is currently active"""
        if not self.start_date:
            return False

        today = date.today()
        if self.expected_completion:
            return self.start_date <= today <= self.expected_completion
        return self.start_date <= today

    def get_status(self) -> str:
        """Get current project status"""
        if not self.start_date:
            return "planning"

        today = date.today()
        if today < self.start_date:
            return "scheduled"
        elif self.expected_completion and today > self.expected_completion:
            return "overdue"
        elif self.is_active():
            return "in_progress"
        else:
            return "completed"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'project_name': self.project_name,
            'project_type': self.project_type,
            'address': self.address,
            'responsible_engineer': self.responsible_engineer,
            'responsible_crea': self.responsible_crea,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expected_completion': self.expected_completion.isoformat() if self.expected_completion else None,
            'budget': self.budget,
            'total_area_m2': self.total_area_m2,
            'number_of_floors': self.number_of_floors,
            'client_name': self.client_name,
            'client_contact': self.client_contact,
            'duration_days': self.calculate_duration_days(),
            'status': self.get_status()
        }
