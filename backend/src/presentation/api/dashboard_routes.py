"""
Dashboard API Endpoints
Provides dashboard data and analytics
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID

from application.services.project_service import ProjectService
from infrastructure.dependencies import get_project_service
from domain.chat_history_mongo import ChatHistoryManagerMongo

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(
    project_service: ProjectService = Depends(get_project_service)
):
    """Get dashboard overview data with chat statistics"""
    try:
        # Get all projects for overview
        projects = await project_service.list_projects()

        # Calculate project statistics
        total_projects = len(projects)
        active_projects = len([p for p in projects if p.status == "in_progress"])
        completed_projects = len([p for p in projects if p.status == "completed"])

        # Calculate average progress
        total_progress = sum(p.overall_progress.percentage for p in projects) if projects else 0
        avg_progress = round(total_progress / len(projects), 1) if projects else 0

        # Get chat statistics from MongoDB
        history_manager = ChatHistoryManagerMongo()
        chat_stats = await history_manager.get_statistics()

        total_sessions = chat_stats.get('total_sessions', 0)
        active_sessions = chat_stats.get('active_sessions', 0)
        total_messages = chat_stats.get('total_messages', 0)
        messages_today = chat_stats.get('messages_today', 0)
        total_tokens = chat_stats.get('total_tokens', 0)
        total_cost = chat_stats.get('total_cost', 0.0)
        tokens_today = chat_stats.get('tokens_today', 0)

        # Get recent sessions for activities
        recent_sessions = await history_manager.list_sessions(limit=5)

        # Recent activities (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activities = []

        # Add project activities
        for project in projects[:3]:  # Limit to 3 most recent projects
            if project.updated_at >= week_ago:
                recent_activities.append({
                    "id": str(project.id),
                    "title": f"Projeto {project.info.project_name}",
                    "activity": f"Progresso atualizado para {project.overall_progress.percentage}%",
                    "timestamp": project.updated_at.isoformat(),
                    "type": "progress_update",
                    "icon": "construction"
                })

        # Add chat activities from MongoDB
        for session in recent_sessions:
            if session.last_activity >= week_ago:
                recent_activities.append({
                    "id": session.id,
                    "title": "Nova conversa de chat",
                    "activity": f"Sessão criada com {len(session.messages)} mensagens",
                    "timestamp": session.last_activity.isoformat(),
                    "type": "chat_activity",
                    "icon": "chat"
                })

        # Sort activities by timestamp (most recent first)
        recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activities = recent_activities[:5]  # Keep only 5 most recent

        # Progress alerts
        alerts = []
        for project in projects:
            if project.overall_progress.percentage < 50 and project.status == "in_progress":
                days_since_start = (datetime.utcnow() - project.created_at).days
                if days_since_start > 30:  # Alert if low progress after 30 days
                    alerts.append({
                        "project_id": str(project.id),
                        "project_name": project.info.project_name,
                        "message": f"Baixo progresso ({project.overall_progress.percentage}%) após {days_since_start} dias",
                        "severity": "warning",
                        "type": "project_delay"
                    })

        # Chat alerts
        if active_sessions > 10:
            alerts.append({
                "message": f"Muitas sessões de chat ativas ({active_sessions})",
                "severity": "info",
                "type": "chat_usage"
            })

        # Get recent sessions from MongoDB for dashboard
        recent_sessions_data = await history_manager.list_sessions(limit=5)

        # Format recent sessions for frontend
        recent_sessions = []
        for session in recent_sessions_data:
            # Calculate tokens and cost from session
            session_tokens = session.total_tokens
            session_cost = session.total_cost

            recent_sessions.append({
                "id": session.id,
                "project_name": session.project_name or f"Sessão {session.id[:8]}",
                "status": session.status,
                "message_count": len(session.messages),
                "tokens": session_tokens,
                "cost": round(session_cost, 4),
                "last_activity": session.last_activity.isoformat()
            })

        return {
            # Fields that frontend expects directly
            "active_sessions": active_sessions,
            "chat_statistics": {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "messages_today": messages_today
            },
            "token_statistics": {
                "total_tokens": total_tokens,
                "total_requests": total_sessions,
                "total_cost": round(total_cost, 4),
                "tokens_today": tokens_today
            },
            "recent_sessions": recent_sessions,

            # Keep existing structure for backward compatibility
            "statistics": {
                # Project statistics
                "total_projects": total_projects,
                "active_projects": active_projects,
                "completed_projects": completed_projects,
                "average_progress": avg_progress,

                # Chat statistics
                "total_chat_sessions": total_sessions,
                "active_chat_sessions": active_sessions,
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 4)
            },
            "recent_activities": recent_activities,
            "alerts": alerts,
            "usage_summary": {
                "sessions_today": active_sessions,
                "messages_today": messages_today,
                "projects_updated": len([p for p in projects if (datetime.utcnow() - p.updated_at).days == 0]),
                "tokens_today": tokens_today,
                "cost_today": round(total_cost / max(total_sessions, 1) if total_sessions > 0 else 0.0, 4)  # Estimated daily cost
            },
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard overview: {str(e)}")


@router.get("/costs")
async def get_dashboard_costs(
    project_service: ProjectService = Depends(get_project_service)
):
    """Get dashboard cost analysis including API usage"""
    try:
        # Get all projects for cost analysis
        projects = await project_service.list_projects()

        # Get chat/API statistics from MongoDB
        history_manager = ChatHistoryManagerMongo()
        chat_stats = await history_manager.get_statistics()

        api_total_tokens = chat_stats.get('total_tokens', 0)
        api_total_cost = chat_stats.get('total_cost', 0.0)

        # Calculate cost statistics
        total_budget = sum(p.budget for p in projects if p.budget) if projects else 0
        total_spent = 0  # This would come from actual cost tracking

        # Estimated costs based on progress
        estimated_spent = 0
        for project in projects:
            if project.budget:
                estimated_spent += project.budget * (project.overall_progress / 100)

        # Cost breakdown by project
        project_costs = []
        for project in projects:
            if project.budget:
                estimated_project_spent = project.budget * (project.overall_progress.percentage / 100)
                project_costs.append({
                    "project_id": str(project.id),
                    "project_name": project.info.project_name,
                    "budget": project.budget,
                    "estimated_spent": round(estimated_project_spent, 2),
                    "remaining": round(project.budget - estimated_project_spent, 2),
                    "progress": project.overall_progress.percentage
                })

        # Monthly cost trends (mock data - would be real in production)
        monthly_trends = []
        for i in range(6):  # Last 6 months
            month_date = datetime.utcnow() - timedelta(days=30*i)
            monthly_trends.append({
                "month": month_date.strftime("%Y-%m"),
                "planned": round(total_budget / 12, 2),  # Simple monthly distribution
                "actual": round(estimated_spent / 6, 2)  # Mock actual spending
            })

        monthly_trends.reverse()  # Chronological order

        # Cost efficiency metrics
        efficiency_score = 85  # Mock efficiency score
        if total_budget > 0:
            budget_utilization = round((estimated_spent / total_budget) * 100, 1)
        else:
            budget_utilization = 0

        # Calculate cost per token for efficiency metrics
        cost_per_token = round(api_total_cost / api_total_tokens, 6) if api_total_tokens > 0 else 0.0

        # Get recent sessions for models breakdown
        recent_sessions = await history_manager.list_sessions(limit=100)

        # Calculate cost by model (if metadata contains model info)
        models_breakdown = {}
        for session in recent_sessions:
            if session.metadata and 'model' in session.metadata:
                model = session.metadata['model']
                if model not in models_breakdown:
                    models_breakdown[model] = {
                        'total_cost': 0.0,
                        'requests': 0,
                        'tokens': 0
                    }
                models_breakdown[model]['total_cost'] += session.total_cost
                models_breakdown[model]['requests'] += 1
                models_breakdown[model]['tokens'] += session.total_tokens

        # Round values in models_breakdown
        for model in models_breakdown:
            models_breakdown[model]['total_cost'] = round(models_breakdown[model]['total_cost'], 4)

        # Calculate monthly projection based on current usage
        days_in_month = 30
        current_day = datetime.utcnow().day
        monthly_projection = round((api_total_cost / max(current_day, 1)) * days_in_month, 2)

        return {
            "summary": {
                "total_budget": total_budget,
                "estimated_spent": round(estimated_spent, 2),
                "remaining_budget": round(total_budget - estimated_spent, 2),
                "budget_utilization": budget_utilization
            },
            "api_costs": {
                "total_cost": round(api_total_cost, 4),
                "total_tokens": api_total_tokens,
                "cost_per_token": cost_per_token
            },
            "projections": {
                "monthly_projection": monthly_projection
            },
            "efficiency": {
                "cost_per_token": cost_per_token,
                "score": efficiency_score,
                "status": "good" if efficiency_score > 80 else "warning"
            },
            "models_breakdown": models_breakdown,
            "project_breakdown": project_costs,
            "monthly_trends": monthly_trends,
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard costs: {str(e)}")


@router.get("/metrics")
async def get_dashboard_metrics(
    timeframe: Optional[str] = "30d",
    project_service: ProjectService = Depends(get_project_service)
):
    """Get dashboard performance metrics"""
    try:
        # Parse timeframe
        if timeframe == "7d":
            days = 7
        elif timeframe == "30d":
            days = 30
        elif timeframe == "90d":
            days = 90
        else:
            days = 30

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get projects
        projects = await project_service.list_projects()

        # Calculate metrics
        metrics = {
            "productivity": {
                "projects_completed": len([p for p in projects if p.status == "completed"]),
                "average_completion_time": 45,  # Mock data - days
                "on_time_delivery": 87.5  # Mock percentage
            },
            "quality": {
                "average_quality_score": 92.3,  # Mock score
                "issues_resolved": 156,  # Mock count
                "client_satisfaction": 96.8  # Mock percentage
            },
            "efficiency": {
                "resource_utilization": 89.2,  # Mock percentage
                "cost_efficiency": 94.1,  # Mock percentage
                "time_efficiency": 91.7  # Mock percentage
            },
            "trends": {
                "progress_velocity": "+12.5%",  # Mock trend
                "budget_variance": "-3.2%",  # Mock variance
                "timeline_adherence": "+5.8%"  # Mock adherence
            }
        }

        return {
            "timeframe": timeframe,
            "metrics": metrics,
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard metrics: {str(e)}")