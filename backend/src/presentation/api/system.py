"""
System Information API Endpoints
Provides system health and information endpoints
Following the Single Responsibility Principle (SRP) from SOLID
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any
import os

from infrastructure.app_state import AppState, get_app_state
from infrastructure.database.mongodb import mongodb

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Construction Analysis Agent API",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Conversational AI Chat",
            "Image Analysis with AI Model",
            "Document Processing",
            "Progress Monitoring",
            "Automated Reports",
            "Multi-Agent Orchestration"
        ],
        "powered_by": {
            "langchain": "0.3.12",
            "langgraph": "0.2.63",
            "chat": os.getenv("CHAT_MODEL", "x-ai/grok-4-fast"),
            "vision": os.getenv("VISION_MODEL", "google/gemini-2.5-flash-image-preview")
        }
    }


@router.get("/health")
async def health_check(state: AppState = Depends(get_app_state)):
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "database": "disconnected",
        "agents": "not_initialized",
        "services": "not_initialized"
    }

    try:
        # Check database
        if state.db_connected and await mongodb.health_check():
            health_status["database"] = "connected"
    except:
        pass

    try:
        # Check agents
        if state.agent_factory and state.agent_factory.is_initialized:
            health_status["agents"] = "initialized"
    except:
        pass

    try:
        # Check services
        if state.chat_service and state.project_service:
            health_status["services"] = "initialized"
    except:
        pass

    # Determine overall health
    if any(v in ["disconnected", "not_initialized"] for v in health_status.values() if v != "healthy"):
        health_status["status"] = "degraded"

    return health_status


@router.get("/api/v1/system/info")
async def system_info():
    """Get system information"""
    return {
        "agents": {
            "visual": "Image analysis with AI Model",
            "document": "Document processing and OCR",
            "progress": "Progress monitoring and predictions",
            "report": "Report generation and BI",
            "supervisor": "LangGraph orchestration"
        },
        "capabilities": {
            "image_formats": ["jpg", "jpeg", "png", "bmp"],
            "document_formats": ["pdf", "docx", "xlsx", "txt"],
            "max_file_size_mb": 50,
            "locations_per_project": 3,
            "supported_languages": ["pt-BR", "en-US"]
        },
        "integrations": {
            "openrouter": "OpenRouter API",
            "models": {
                "chat": os.getenv("CHAT_MODEL", "x-ai/grok-4-fast"),
                "vision": os.getenv("VISION_MODEL", "google/gemini-2.5-flash-image-preview")
            },
            "langchain": "Latest v0.3.12",
            "langgraph": "Latest v0.2.63"
        }
    }