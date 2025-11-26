"""
Value Object: Phase
Immutable object representing construction phases
Following DDD principles
"""

from dataclasses import dataclass
from typing import List, Optional

from domain.exceptions.domain_exceptions import DomainException


@dataclass(frozen=True)
class Phase:
    """
    Construction Phase Value Object
    Represents a specific phase in the construction process
    """

    name: str  # 'planning', 'foundation', 'structure', 'masonry', 'installations', 'finishing', 'completed'
    description: Optional[str] = None
    visual_indicators: Optional[List[str]] = None
    completion_criteria: Optional[str] = None
    typical_duration_days: Optional[int] = None
    predecessor_phases: Optional[List[str]] = None

    def __post_init__(self):
        """Validate phase creation"""
        valid_phases = [
            'planning',
            'foundation',
            'structure',
            'masonry',
            'installations',
            'finishing',
            'completed'
        ]

        if self.name not in valid_phases:
            raise DomainException(
                f"Invalid phase name '{self.name}'. Must be one of: {', '.join(valid_phases)}"
            )

        # Set default visual indicators if not provided
        if self.visual_indicators is None:
            object.__setattr__(self, 'visual_indicators', self._get_default_indicators())

        # Set default description if not provided
        if self.description is None:
            object.__setattr__(self, 'description', self._get_default_description())

    def _get_default_indicators(self) -> List[str]:
        """Get default visual indicators for the phase"""
        indicators_map = {
            'planning': ['project_boards', 'survey_marks', 'permits'],
            'foundation': ['excavation', 'rebar', 'concrete_forms', 'foundation_walls'],
            'structure': ['columns', 'beams', 'slabs', 'structural_steel'],
            'masonry': ['bricks', 'blocks', 'mortar', 'walls'],
            'installations': ['pipes', 'wiring', 'electrical_boxes', 'ducts'],
            'finishing': ['plaster', 'paint', 'tiles', 'fixtures'],
            'completed': ['finished_surfaces', 'installed_equipment', 'landscaping']
        }
        return indicators_map.get(self.name, [])

    def _get_default_description(self) -> str:
        """Get default description for the phase"""
        descriptions = {
            'planning': 'Initial planning and project preparation',
            'foundation': 'Excavation and foundation construction',
            'structure': 'Structural framework construction',
            'masonry': 'Wall construction and enclosure',
            'installations': 'Electrical, plumbing, and HVAC installation',
            'finishing': 'Final finishes and details',
            'completed': 'Project completed and ready for use'
        }
        return descriptions.get(self.name, '')

    def is_initial_phase(self) -> bool:
        """Check if this is an initial phase"""
        return self.name in ['planning', 'foundation']

    def is_final_phase(self) -> bool:
        """Check if this is a final phase"""
        return self.name in ['finishing', 'completed']

    def is_structural_phase(self) -> bool:
        """Check if this is a structural phase"""
        return self.name in ['foundation', 'structure']

    def get_next_phases(self) -> List[str]:
        """Get possible next phases"""
        transitions = {
            'planning': ['foundation'],
            'foundation': ['structure'],
            'structure': ['masonry', 'installations'],
            'masonry': ['installations', 'finishing'],
            'installations': ['finishing'],
            'finishing': ['completed'],
            'completed': []
        }
        return transitions.get(self.name, [])

    def can_transition_to(self, next_phase: str) -> bool:
        """Check if transition to next phase is valid"""
        return next_phase in self.get_next_phases()

    def get_typical_elements(self) -> List[str]:
        """Get typical construction elements for this phase"""
        elements_map = {
            'planning': ['drawings', 'permits', 'specifications'],
            'foundation': ['footings', 'foundation_walls', 'waterproofing'],
            'structure': ['columns', 'beams', 'slabs', 'roof_structure'],
            'masonry': ['exterior_walls', 'interior_walls', 'partitions'],
            'installations': ['electrical', 'plumbing', 'hvac', 'fire_protection'],
            'finishing': ['flooring', 'painting', 'ceilings', 'fixtures'],
            'completed': ['landscaping', 'final_cleaning', 'inspections']
        }
        return elements_map.get(self.name, [])

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'visual_indicators': self.visual_indicators,
            'completion_criteria': self.completion_criteria,
            'typical_duration_days': self.typical_duration_days,
            'predecessor_phases': self.predecessor_phases,
            'is_initial': self.is_initial_phase(),
            'is_final': self.is_final_phase(),
            'is_structural': self.is_structural_phase(),
            'next_phases': self.get_next_phases(),
            'typical_elements': self.get_typical_elements()
        }
