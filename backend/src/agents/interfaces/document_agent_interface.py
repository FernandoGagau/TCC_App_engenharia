"""
Document Processing Agent Interface
"""

from abc import abstractmethod
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResult


class DocumentAgentInterface(BaseAgent):
    """Interface for document processing agent"""

    @abstractmethod
    async def process_document(self, file_path: str, document_type: str = "auto") -> AgentResult:
        """Process document and extract information"""
        pass

    @abstractmethod
    async def extract_project_data(self, file_path: str) -> AgentResult:
        """Extract project-specific data from document"""
        pass