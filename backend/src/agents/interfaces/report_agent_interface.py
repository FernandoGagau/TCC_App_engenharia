"""
Report Generation Agent Interface
"""

from abc import abstractmethod
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResult


class ReportAgentInterface(BaseAgent):
    """Interface for report generation agent"""

    @abstractmethod
    async def generate_progress_report(self, project_id: str) -> AgentResult:
        """Generate progress report for project"""
        pass

    @abstractmethod
    async def generate_safety_report(self, project_id: str) -> AgentResult:
        """Generate safety analysis report"""
        pass

    @abstractmethod
    async def generate_custom_report(self, project_id: str, report_config: Dict[str, Any]) -> AgentResult:
        """Generate custom report based on configuration"""
        pass