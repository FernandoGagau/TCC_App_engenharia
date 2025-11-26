"""
Application State Management
Manages global application state and lifecycle
Following the Single Responsibility Principle (SRP) from SOLID
"""

from typing import Optional

from infrastructure.config.settings import Settings
from infrastructure.agents.agent_factory import AgentFactory
from application.services.project_service import ProjectService
from application.services.chat_service import ChatService


class AppState:
    """Application state management"""
    def __init__(self):
        self.settings: Optional[Settings] = None
        self.agent_factory: Optional[AgentFactory] = None
        self.project_service: Optional[ProjectService] = None
        self.chat_service: Optional[ChatService] = None
        self.db_connected: bool = False


# Global app state instance
_app_state = AppState()


def get_app_state() -> AppState:
    """Get application state for dependency injection"""
    return _app_state


def initialize_app_state(
    settings: Settings,
    agent_factory: AgentFactory,
    project_service: ProjectService,
    chat_service: ChatService,
    db_connected: bool = True
) -> None:
    """Initialize application state with all services"""
    _app_state.settings = settings
    _app_state.agent_factory = agent_factory
    _app_state.project_service = project_service
    _app_state.chat_service = chat_service
    _app_state.db_connected = db_connected


def reset_app_state() -> None:
    """Reset application state to initial values"""
    global _app_state
    _app_state = AppState()