"""
Dependency Injection Module
Provides FastAPI dependency functions for service injection
Following the Dependency Inversion Principle (DIP) from SOLID
"""

from fastapi import Depends, HTTPException

from application.services.project_service import ProjectService
from application.services.chat_service import ChatService
from infrastructure.app_state import get_app_state, AppState


def get_project_service(state: AppState = Depends(get_app_state)) -> ProjectService:
    """Get project service dependency"""
    if not state.project_service:
        raise HTTPException(status_code=503, detail="Project service not initialized")
    return state.project_service


def get_chat_service(state: AppState = Depends(get_app_state)) -> ChatService:
    """Get chat service dependency"""
    if not state.chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")
    return state.chat_service