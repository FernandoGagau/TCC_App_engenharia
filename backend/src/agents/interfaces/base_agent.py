"""
Base Agent Interface
Defines the contract that all agents must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class AgentResult:
    """Standard result format for all agents"""
    success: bool
    data: Dict[str, Any]
    message: str
    errors: List[str] = None
    metadata: Dict[str, Any] = None


class BaseAgent(ABC):
    """Base interface for all specialized agents"""

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process input data and return standardized result

        Args:
            input_data: Input data specific to each agent type

        Returns:
            AgentResult with success status, data, and messages
        """
        pass

    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get agent metadata and capabilities

        Returns:
            Dictionary with agent name, version, capabilities
        """
        pass

    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data format

        Args:
            input_data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        pass