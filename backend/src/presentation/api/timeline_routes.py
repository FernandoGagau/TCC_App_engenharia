"""
Timeline API Endpoints
Provides construction timeline and progress analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import calendar
import logging

from application.services.timeline_service import TimelineService

router = APIRouter()
timeline_service = TimelineService()
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_timeline_summary(
    project_id: Optional[str] = Query(None)
):
    """Get timeline summary with monthly periods"""
    try:
        summary = await timeline_service.get_timeline_summary(project_id)
        return summary
    except Exception as e:
        logger.error(f"Error getting timeline summary: {str(e)}", exc_info=True)
        return {
            "project": project_id or "all",
            "total_images": 0,
            "total_months": 0,
            "periods": [],
            "progress_timeline": []
        }


@router.get("/latest")
async def get_latest_timeline_images(limit: int = Query(10), project_id: Optional[str] = None):
    """Get latest timeline images"""
    try:
        images = await timeline_service.get_latest_images(limit, project_id)
        return {"images": images, "count": len(images)}
    except Exception as e:
        logger.error(f"Error getting latest images: {str(e)}", exc_info=True)
        return {"images": [], "count": 0}


@router.get("/progress")
async def get_construction_progress(project_id: Optional[str] = None):
    """Get construction progress analysis"""
    try:
        progress = await timeline_service.get_progress_analysis(project_id)
        return progress
    except Exception as e:
        logger.error(f"Error getting construction progress: {str(e)}", exc_info=True)
        return {
            "total_duration_days": 0,
            "total_images": 0,
            "periods_analyzed": 0,
            "monthly_progress": [],
            "activity_frequency": {}
        }


@router.get("/images/{month}")
async def get_images_by_month(month: str, project_id: Optional[str] = None):
    """Get images for a specific month"""
    try:
        images = await timeline_service.get_images_by_period(month, project_id)
        return {"month": month, "images": images, "count": len(images)}
    except Exception as e:
        logger.error(f"Error getting images for month {month}: {str(e)}", exc_info=True)
        return {"month": month, "images": [], "count": 0}