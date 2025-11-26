"""
Progress Tracking Agent Interface
"""

from abc import abstractmethod
from typing import Dict, Any
from .base_agent import BaseAgent, AgentResult


class ProgressAgentInterface(BaseAgent):
    """Interface for progress tracking agent"""

    @abstractmethod
    async def calculate_progress(self, project_id: str) -> AgentResult:
        """Calculate project progress percentage"""
        pass

    @abstractmethod
    async def analyze_timeline(self, project_id: str) -> AgentResult:
        """Analyze project timeline and delays"""
        pass