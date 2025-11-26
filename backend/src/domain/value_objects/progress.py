"""
Value Object: Progress
Immutable object representing progress state
Following DDD principles
"""

from dataclasses import dataclass
from typing import Optional, List

from domain.exceptions.domain_exceptions import DomainException


@dataclass(frozen=True)
class Progress:
    """
    Progress Value Object
    Represents the progress state of a project or location
    """

    percentage: int  # 0-100
    phase: Optional[str] = None
    quality_score: Optional[int] = None  # 0-100
    confidence: Optional[float] = None  # 0.0-1.0 for AI predictions
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate progress values"""
        if not 0 <= self.percentage <= 100:
            raise DomainException(
                f"Progress percentage must be between 0 and 100, got {self.percentage}"
            )

        if self.quality_score is not None and not 0 <= self.quality_score <= 100:
            raise DomainException(
                f"Quality score must be between 0 and 100, got {self.quality_score}"
            )

        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise DomainException(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def is_completed(self) -> bool:
        """Check if progress indicates completion"""
        return self.percentage >= 100

    def is_critical(self) -> bool:
        """Check if progress is critically low"""
        return self.percentage < 20 and self.phase not in ['planning', 'foundation']

    def get_status(self) -> str:
        """Get progress status category"""
        if self.percentage == 0:
            return "not_started"
        elif self.percentage < 25:
            return "initial"
        elif self.percentage < 50:
            return "in_progress"
        elif self.percentage < 75:
            return "advanced"
        elif self.percentage < 100:
            return "finalizing"
        else:
            return "completed"

    def get_quality_status(self) -> Optional[str]:
        """Get quality status if available"""
        if self.quality_score is None:
            return None

        if self.quality_score >= 90:
            return "excellent"
        elif self.quality_score >= 75:
            return "good"
        elif self.quality_score >= 60:
            return "acceptable"
        elif self.quality_score >= 40:
            return "needs_improvement"
        else:
            return "critical"

    def compare_with(self, other: 'Progress') -> dict:
        """Compare with another progress object"""
        if not isinstance(other, Progress):
            raise DomainException("Can only compare with another Progress object")

        return {
            'percentage_delta': self.percentage - other.percentage,
            'quality_delta': (
                self.quality_score - other.quality_score
                if self.quality_score and other.quality_score
                else None
            ),
            'phase_changed': self.phase != other.phase,
            'improvement': self.percentage > other.percentage
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'percentage': self.percentage,
            'phase': self.phase,
            'quality_score': self.quality_score,
            'confidence': self.confidence,
            'notes': self.notes,
            'status': self.get_status(),
            'quality_status': self.get_quality_status(),
            'is_completed': self.is_completed(),
            'is_critical': self.is_critical()
        }
