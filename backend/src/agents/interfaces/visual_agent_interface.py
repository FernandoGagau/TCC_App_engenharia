"""
Visual Analysis Agent Interface
Specialized interface for image analysis
"""

from abc import abstractmethod
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResult


class VisualAgentInterface(BaseAgent):
    """Interface for visual analysis agent"""

    @abstractmethod
    async def analyze_image(self, image_path: str, metadata: Dict[str, Any] = None) -> AgentResult:
        """
        Analyze construction site image

        Args:
            image_path: Path to image file
            metadata: Additional image metadata

        Returns:
            AgentResult with visual analysis data
        """
        pass

    @abstractmethod
    async def analyze_batch_images(self, image_paths: List[str]) -> AgentResult:
        """
        Analyze multiple images in batch

        Args:
            image_paths: List of image file paths

        Returns:
            AgentResult with batch analysis data
        """
        pass

    @abstractmethod
    async def detect_construction_phase(self, image_path: str) -> AgentResult:
        """
        Detect current construction phase from image

        Args:
            image_path: Path to image file

        Returns:
            AgentResult with detected phase information
        """
        pass

    @abstractmethod
    async def detect_safety_issues(self, image_path: str) -> AgentResult:
        """
        Detect safety issues in construction site

        Args:
            image_path: Path to image file

        Returns:
            AgentResult with safety analysis
        """
        pass