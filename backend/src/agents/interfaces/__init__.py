"""
Agent Interfaces Package
Defines contracts for all specialized agents
"""

from .base_agent import BaseAgent
from .visual_agent_interface import VisualAgentInterface
from .document_agent_interface import DocumentAgentInterface
from .progress_agent_interface import ProgressAgentInterface
from .report_agent_interface import ReportAgentInterface

__all__ = [
    "BaseAgent",
    "VisualAgentInterface",
    "DocumentAgentInterface",
    "ProgressAgentInterface",
    "ReportAgentInterface"
]