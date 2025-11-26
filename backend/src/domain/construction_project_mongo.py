"""
Construction Project Manager with MongoDB
Replaces file-based storage with MongoDB collections
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
import logging

from infrastructure.database.project_models import (
    ConstructionProjectModel,
    ProjectImageModel,
    ProjectAlertModel,
    ConstructionPhase,
    ProjectStatus,
    BIMModel,
    Camera,
    ComponentProgress
)
from infrastructure.database.mongodb import MongoDB

logger = logging.getLogger(__name__)


class ProjectManagerMongo:
    """MongoDB-based construction project manager"""

    def __init__(self):
        """Initialize manager without file storage"""
        self.projects_cache = {}
        logger.info("ProjectManagerMongo initialized with MongoDB backend")

    async def create_project(
        self,
        name: str,
        description: str,
        location: Dict[str, Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None
    ) -> ConstructionProjectModel:
        """Create new project in MongoDB"""

        project = ConstructionProjectModel(
            name=name,
            description=description,
            location=location,
            start_date=start_date,
            end_date=end_date,
            status=ProjectStatus.PLANNING
        )

        # Save to MongoDB
        await project.save()

        # Cache for quick access
        self.projects_cache[project.project_id] = project

        logger.info(f"Project created in MongoDB: {project.project_id} - {name}")
        return project

    async def update_project(
        self,
        project_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ConstructionProjectModel]:
        """Update existing project"""

        project = await self.get_project(project_id)
        if not project:
            logger.error(f"Project {project_id} not found")
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(project, key):
                # Handle enum conversions
                if key == 'status' and isinstance(value, str):
                    value = ProjectStatus(value)
                elif key == 'current_phase' and isinstance(value, str):
                    value = ConstructionPhase(value)

                setattr(project, key, value)

        # Update timestamp
        project.updated_at = datetime.utcnow()

        # Save to MongoDB
        await project.save()

        # Update cache
        self.projects_cache[project_id] = project

        return project

    async def get_project(self, project_id: str) -> Optional[ConstructionProjectModel]:
        """Get project by ID"""

        # Check cache first
        if project_id in self.projects_cache:
            return self.projects_cache[project_id]

        # Fetch from MongoDB
        project = await ConstructionProjectModel.find_one(
            ConstructionProjectModel.project_id == project_id
        )

        if project:
            self.projects_cache[project_id] = project

        return project

    async def list_projects(
        self,
        status: Optional[ProjectStatus] = None,
        limit: int = 50
    ) -> List[ConstructionProjectModel]:
        """List projects from MongoDB"""

        query = {}
        if status:
            query = ConstructionProjectModel.status == status
            projects = await ConstructionProjectModel.find(query).sort("-updated_at").limit(limit).to_list()
        else:
            projects = await ConstructionProjectModel.find_all().sort("-updated_at").limit(limit).to_list()

        # Update cache
        for project in projects:
            self.projects_cache[project.project_id] = project

        return projects

    async def add_bim_model(
        self,
        project_id: str,
        file_path: str,
        format: str,
        version: str,
        metadata: Dict = None
    ) -> Optional[BIMModel]:
        """Add BIM model to project"""

        project = await self.get_project(project_id)
        if not project:
            return None

        bim_model = BIMModel(
            file_path=file_path,
            format=format,
            version=version,
            upload_date=datetime.utcnow(),
            metadata=metadata or {}
        )

        project.bim_model = bim_model
        project.updated_at = datetime.utcnow()

        await project.save()

        logger.info(f"BIM model added to project {project_id}")
        return bim_model

    async def add_camera(
        self,
        project_id: str,
        name: str,
        position: Dict[str, float],
        rotation: Dict[str, float],
        fov: float = 60.0,
        resolution: str = "1920x1080",
        stream_url: Optional[str] = None
    ) -> Optional[Camera]:
        """Add camera to project"""

        project = await self.get_project(project_id)
        if not project:
            return None

        camera = Camera(
            name=name,
            position=position,
            rotation=rotation,
            fov=fov,
            resolution=resolution,
            stream_url=stream_url
        )

        project.cameras.append(camera)
        project.updated_at = datetime.utcnow()

        await project.save()

        logger.info(f"Camera {name} added to project {project_id}")
        return camera

    async def update_component_progress(
        self,
        project_id: str,
        component_id: str,
        phase: ConstructionPhase,
        confidence: float,
        images: List[str] = None
    ):
        """Update component progress"""

        project = await self.get_project(project_id)
        if not project:
            return

        if component_id not in project.components:
            # Create new component progress
            project.components[component_id] = ComponentProgress(
                component_id=component_id,
                component_type="unknown",  # Will be updated from BIM
                current_phase=phase,
                detection_confidence=confidence,
                last_updated=datetime.utcnow(),
                images=images or []
            )
        else:
            # Update existing
            comp = project.components[component_id]
            comp.current_phase = phase
            comp.detection_confidence = confidence
            comp.last_updated = datetime.utcnow()
            if images:
                comp.images.extend(images)

            # Add to history
            comp.detection_history.append({
                'phase': phase.value,
                'confidence': confidence,
                'timestamp': datetime.utcnow().isoformat(),
                'images': images or []
            })

        # Update overall progress
        project.overall_progress = self._calculate_overall_progress(project)
        project.updated_at = datetime.utcnow()

        await project.save()

    def _calculate_overall_progress(self, project: ConstructionProjectModel) -> float:
        """Calculate overall project progress"""
        if not project.components:
            return 0.0

        phase_weights = {
            ConstructionPhase.REBAR_TYING_COLUMNS: 0.15,
            ConstructionPhase.PRE_REBAR_TYING_WALLS: 0.20,
            ConstructionPhase.REBAR_TYING_WALLS: 0.25,
            ConstructionPhase.FORMWORK_ASSEMBLY_WALLS: 0.35,
            ConstructionPhase.FORMWORK_ASSEMBLY_COLUMNS: 0.40,
            ConstructionPhase.CONCRETE_POURING: 0.70,
            ConstructionPhase.COMPLETED: 1.0
        }

        total_weight = 0.0
        for comp in project.components.values():
            weight = phase_weights.get(comp.current_phase, 0.0)
            total_weight += weight

        # Average progress
        if project.components:
            return (total_weight / len(project.components)) * 100

        return 0.0

    async def get_project_analytics(self, project_id: str) -> Dict:
        """Get project analytics"""

        project = await self.get_project(project_id)
        if not project:
            return {}

        # Phase distribution
        phase_count = {}
        for comp in project.components.values():
            phase = comp.current_phase.value
            phase_count[phase] = phase_count.get(phase, 0) + 1

        # Time analysis
        days_elapsed = 0
        days_remaining = 0
        if project.start_date:
            days_elapsed = (datetime.utcnow() - project.start_date).days
        if project.end_date:
            days_remaining = (project.end_date - datetime.utcnow()).days

        # Component statistics
        total_components = len(project.components)
        completed_components = sum(
            1 for c in project.components.values()
            if c.current_phase == ConstructionPhase.COMPLETED
        )

        # Average confidence
        avg_confidence = 0.0
        if project.components:
            total_conf = sum(c.detection_confidence for c in project.components.values())
            avg_confidence = total_conf / len(project.components)

        analytics = {
            'project_id': project_id,
            'overall_progress': project.overall_progress,
            'phase_distribution': phase_count,
            'total_components': total_components,
            'completed_components': completed_components,
            'completion_rate': (completed_components / max(total_components, 1)) * 100,
            'average_confidence': avg_confidence,
            'days_elapsed': days_elapsed,
            'days_remaining': days_remaining,
            'cameras_active': sum(1 for c in project.cameras if c.active),
            'last_update': project.updated_at.isoformat()
        }

        # Update analytics in project
        project.analytics = analytics
        await project.save()

        return analytics

    async def generate_alerts(self, project_id: str) -> List[ProjectAlertModel]:
        """Generate alerts based on project analysis"""

        project = await self.get_project(project_id)
        if not project:
            return []

        alerts = []
        analytics = await self.get_project_analytics(project_id)

        # Check delays
        if analytics['days_remaining'] < 0:
            alert = ProjectAlertModel(
                project_id=project_id,
                type='error',
                category='delay',
                message='Project delayed',
                details=f"Deadline exceeded by {abs(analytics['days_remaining'])} days",
                priority=3
            )
            await alert.save()
            alerts.append(alert)

        # Check low confidence
        if analytics['average_confidence'] < 0.7:
            alert = ProjectAlertModel(
                project_id=project_id,
                type='warning',
                category='quality',
                message='Low detection confidence',
                details=f"Average confidence: {analytics['average_confidence']:.2%}",
                priority=1
            )
            await alert.save()
            alerts.append(alert)

        # Check slow progress
        if project.overall_progress < 50 and analytics['days_elapsed'] > 30:
            alert = ProjectAlertModel(
                project_id=project_id,
                type='warning',
                category='progress',
                message='Slow progress',
                details=f"Only {project.overall_progress:.1f}% completed after {analytics['days_elapsed']} days",
                priority=2
            )
            await alert.save()
            alerts.append(alert)

        # Check inactive cameras
        inactive_cameras = [c for c in project.cameras if not c.active]
        if inactive_cameras:
            alert = ProjectAlertModel(
                project_id=project_id,
                type='info',
                category='safety',
                message=f"{len(inactive_cameras)} cameras inactive",
                details=', '.join([c.name for c in inactive_cameras]),
                priority=0
            )
            await alert.save()
            alerts.append(alert)

        return alerts

    async def add_project_image(
        self,
        project_id: str,
        file_path: str,
        phase_detected: Optional[ConstructionPhase] = None,
        components_detected: List[str] = None,
        confidence_score: float = 0.0,
        camera_id: Optional[str] = None,
        metadata: Dict = None
    ) -> ProjectImageModel:
        """Add image to project"""

        image = ProjectImageModel(
            project_id=project_id,
            file_path=file_path,
            phase_detected=phase_detected,
            components_detected=components_detected or [],
            confidence_score=confidence_score,
            camera_id=camera_id,
            metadata=metadata or {}
        )

        if phase_detected:
            image.analyzed_at = datetime.utcnow()

        await image.save()

        logger.info(f"Image added to project {project_id}: {image.image_id}")
        return image

    async def get_project_images(
        self,
        project_id: str,
        phase: Optional[ConstructionPhase] = None,
        camera_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ProjectImageModel]:
        """Get project images"""

        query = ProjectImageModel.project_id == project_id

        if phase:
            query = query & (ProjectImageModel.phase_detected == phase)

        if camera_id:
            query = query & (ProjectImageModel.camera_id == camera_id)

        images = await ProjectImageModel.find(query).sort("-captured_at").limit(limit).to_list()

        return images

    async def get_active_alerts(
        self,
        project_id: str,
        priority: Optional[int] = None
    ) -> List[ProjectAlertModel]:
        """Get active alerts for project"""

        query = (
            (ProjectAlertModel.project_id == project_id) &
            (ProjectAlertModel.is_active == True) &
            (ProjectAlertModel.is_resolved == False)
        )

        if priority is not None:
            query = query & (ProjectAlertModel.priority >= priority)

        alerts = await ProjectAlertModel.find(query).sort("-created_at").to_list()

        return alerts

    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> Optional[ProjectAlertModel]:
        """Acknowledge an alert"""

        alert = await ProjectAlertModel.find_one(
            ProjectAlertModel.alert_id == alert_id
        )

        if alert:
            alert.is_acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            await alert.save()

        return alert

    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution_notes: Optional[str] = None
    ) -> Optional[ProjectAlertModel]:
        """Resolve an alert"""

        alert = await ProjectAlertModel.find_one(
            ProjectAlertModel.alert_id == alert_id
        )

        if alert:
            alert.is_resolved = True
            alert.resolved_by = resolved_by
            alert.resolved_at = datetime.utcnow()
            alert.resolution_notes = resolution_notes
            alert.is_active = False
            alert.updated_at = datetime.utcnow()
            await alert.save()

        return alert

    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old project data"""

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Clean old images
        result = await ProjectImageModel.find(
            ProjectImageModel.captured_at < cutoff_date
        ).delete()

        if result.deleted_count > 0:
            logger.info(f"Removed {result.deleted_count} old project images")

        # Clean resolved alerts
        result = await ProjectAlertModel.find(
            (ProjectAlertModel.is_resolved == True) &
            (ProjectAlertModel.resolved_at < cutoff_date)
        ).delete()

        if result.deleted_count > 0:
            logger.info(f"Removed {result.deleted_count} old resolved alerts")


# Synchronous wrapper for compatibility
class ProjectManager:
    """Synchronous wrapper for MongoDB project manager"""

    def __init__(self):
        self.async_manager = ProjectManagerMongo()

    def create_project(self, *args, **kwargs):
        """Synchronous create project"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.async_manager.create_project(*args, **kwargs)
            )
        finally:
            loop.close()

    def get_project(self, project_id: str):
        """Synchronous get project"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.async_manager.get_project(project_id)
            )
        finally:
            loop.close()

    def list_projects(self, *args, **kwargs):
        """Synchronous list projects"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.async_manager.list_projects(*args, **kwargs)
            )
        finally:
            loop.close()

    def update_project(self, *args, **kwargs):
        """Synchronous update project"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.async_manager.update_project(*args, **kwargs)
            )
        finally:
            loop.close()