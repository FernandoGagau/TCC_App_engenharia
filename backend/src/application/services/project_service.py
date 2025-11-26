"""
Project Service
Application service for project management
Following DDD and SOLID principles
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path

from domain.entities.project import Project
from domain.entities.location import Location
from domain.value_objects.project_info import ProjectInfo
from domain.value_objects.progress import Progress
from infrastructure.database.mongodb import MongoDB
from infrastructure.database.project_models import ProjectModel, LocationModel, ConstructionProjectModel
from infrastructure.config.settings import Settings
from infrastructure.storage_service import StorageService

logger = logging.getLogger(__name__)


class ProjectService:
    """
    Application service for project management
    Handles business operations and orchestrates domain entities
    """

    def __init__(self, db: MongoDB, settings: Settings):
        """
        Initialize project service

        Args:
            db: MongoDB database instance
            settings: Application settings
        """
        self.db = db
        self.settings = settings
        # Create storage config from settings
        storage_config = {
            'type': 'local',
            'base_path': 'backend/storage'
        }
        self.storage_service = StorageService(storage_config)
        logger.info("ProjectService initialized")

    async def create_project(self, project_data: Dict[str, Any]) -> Project:
        """
        Create a new project

        Args:
            project_data: Project information dictionary

        Returns:
            Created Project entity
        """
        try:
            # Create project info
            project_info = ProjectInfo(
                project_name=project_data.get("name", "New Project"),
                project_type=project_data.get("type", "residential"),
                address=project_data.get("address", ""),
                responsible_engineer=project_data.get("responsible_engineer", ""),
                start_date=project_data.get("start_date"),
                expected_completion=project_data.get("expected_completion")
            )

            # Create project entity
            project = Project(
                id=uuid4(),
                info=project_info,
                overall_progress=Progress(percentage=0),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # Save to MongoDB using Beanie
            construction_project = ConstructionProjectModel(
                project_id=str(project.id),
                name=project.info.project_name,
                description=project_data.get("description", ""),
                project_type=project.info.project_type,  # Save the actual type
                location={"address": project.info.address},
                status="planning",
                start_date=project.info.start_date,
                end_date=project.info.expected_completion,
                overall_progress=project.overall_progress.percentage,
                created_at=project.created_at,
                updated_at=project.updated_at
            )

            # Insert document using Beanie
            await construction_project.insert()

            logger.info(f"✅ Project created in MongoDB collection 'construction_projects': {project.id}")
            return project

        except Exception as e:
            logger.error(f"Error creating project: {str(e)}", exc_info=True)
            raise

    async def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get project by ID

        Args:
            project_id: Project UUID string

        Returns:
            Project entity or None
        """
        try:
            # Query MongoDB using Beanie
            doc = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == project_id
            )

            if not doc:
                logger.warning(f"Project not found: {project_id}")
                return None

            # Reconstruct project entity from MongoDB document
            project_info = ProjectInfo(
                project_name=doc.name,
                project_type=doc.project_type if hasattr(doc, 'project_type') else "residential",
                address=doc.location.get("address", "") if doc.location else "",
                responsible_engineer="",  # Not in ConstructionProjectModel
                start_date=doc.start_date,
                expected_completion=doc.end_date
            )

            project = Project(
                id=UUID(doc.project_id),
                info=project_info,
                overall_progress=Progress(percentage=doc.overall_progress),
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )

            # Set additional fields
            project.status = str(doc.status.value) if doc.status else "planning"
            project.budget = 0.0

            logger.info(f"Retrieved project from MongoDB: {project_id}")
            return project

        except Exception as e:
            logger.error(f"Error getting project {project_id}: {str(e)}", exc_info=True)
            return None

    async def list_projects(self, limit: int = 100) -> List[Project]:
        """
        List all projects (alias for get_all)

        Args:
            limit: Maximum number of projects to return

        Returns:
            List of Project entities
        """
        return await self.get_all(limit=limit)

    async def get_all(self, limit: int = 100) -> List[Project]:
        """
        Get all projects from database

        Args:
            limit: Maximum number of projects to return

        Returns:
            List of Project entities
        """
        try:
            # Use Beanie to query ConstructionProjectModel directly
            project_docs = await ConstructionProjectModel.find().limit(limit).to_list()
            projects = []

            for doc in project_docs:
                # Convert ConstructionProjectModel to Project entity
                project_info = ProjectInfo(
                    project_name=doc.name,
                    project_type=doc.project_type if hasattr(doc, 'project_type') else "residential",
                    address=doc.location.get("address", "") if doc.location else "",
                    responsible_engineer="",  # Not available in ConstructionProjectModel
                    start_date=doc.start_date,
                    expected_completion=doc.end_date
                )

                project = Project(
                    id=UUID(doc.project_id),
                    info=project_info,
                    overall_progress=Progress(percentage=doc.overall_progress),
                    created_at=doc.created_at,
                    updated_at=doc.updated_at
                )

                # Set status and budget if available
                project.status = str(doc.status.value) if doc.status else "planning"
                project.budget = 0.0  # Not available in ConstructionProjectModel

                projects.append(project)

            logger.info(f"Retrieved {len(projects)} projects from MongoDB")
            return projects

        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}", exc_info=True)
            return []

    async def update_project(self, project_id: str, update_data: Dict[str, Any]) -> Optional[Project]:
        """
        Update project information

        Args:
            project_id: Project UUID string
            update_data: Dictionary with fields to update

        Returns:
            Updated Project entity or None
        """
        try:
            # Find project in MongoDB
            doc = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == project_id
            )

            if not doc:
                logger.warning(f"Project not found for update: {project_id}")
                return None

            # Update fields
            if "name" in update_data:
                doc.name = update_data["name"]
            if "type" in update_data:
                doc.project_type = update_data["type"]
            if "address" in update_data:
                doc.location = {"address": update_data["address"]}
            if "overall_progress" in update_data:
                doc.overall_progress = update_data["overall_progress"]

            doc.updated_at = datetime.utcnow()

            # Save to MongoDB using Beanie
            await doc.save()

            logger.info(f"✅ Project updated in MongoDB: {project_id}")

            # Return updated project entity
            return await self.get_project(project_id)

        except Exception as e:
            logger.error(f"Error updating project {project_id}: {str(e)}", exc_info=True)
            return None

    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a project

        Args:
            project_id: Project UUID string

        Returns:
            True if deleted successfully
        """
        try:
            # Find and delete using Beanie
            doc = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == project_id
            )

            if not doc:
                logger.warning(f"Project not found for deletion: {project_id}")
                return False

            await doc.delete()

            logger.info(f"✅ Project deleted from MongoDB: {project_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}", exc_info=True)
            return False

    async def add_location(self, project_id: str, location_data: Dict[str, Any]) -> Optional[Location]:
        """
        Add location to project

        Args:
            project_id: Project UUID string
            location_data: Location information

        Returns:
            Created Location entity or None
        """
        try:
            project = await self.get_project(project_id)

            if not project:
                return None

            # Create location
            location = Location(
                id=uuid4(),
                name=location_data.get("name"),
                description=location_data.get("description", ""),
                progress=Progress(percentage=0)
            )

            # Add to project
            project.add_location(location)

            # Save to database
            await self.db.add_project_location(project_id, {
                "id": str(location.id),
                "name": location.name,
                "description": location.description,
                "progress": location.progress.percentage,
                "created_at": datetime.utcnow()
            })

            logger.info(f"Location added to project {project_id}: {location.id}")
            return location

        except Exception as e:
            logger.error(f"Error adding location to project {project_id}: {str(e)}")
            return None

    async def update_location_progress(self, project_id: str, location_id: str, progress: int) -> bool:
        """
        Update location progress

        Args:
            project_id: Project UUID string
            location_id: Location UUID string
            progress: Progress percentage (0-100)

        Returns:
            True if updated successfully
        """
        try:
            project = await self.get_project(project_id)

            if not project:
                return False

            # Find and update location
            for location in project.locations:
                if str(location.id) == location_id:
                    location.update_progress(progress)
                    break

            # Recalculate overall progress
            project.calculate_overall_progress()

            # Save to database
            await self.db.update_location_progress(project_id, location_id, progress)
            await self.db.update_project(project_id, {
                "overall_progress": project.overall_progress.percentage,
                "updated_at": datetime.utcnow()
            })

            logger.info(f"Location {location_id} progress updated to {progress}%")
            return True

        except Exception as e:
            logger.error(f"Error updating location progress: {str(e)}")
            return False

    async def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Get project summary with all details

        Args:
            project_id: Project UUID string

        Returns:
            Dictionary with project summary
        """
        try:
            project = await self.get_project(project_id)

            if not project:
                return {}

            return {
                "id": str(project.id),
                "name": project.info.project_name,
                "type": project.info.project_type,
                "address": project.info.address,
                "responsible_engineer": project.info.responsible_engineer,
                "start_date": project.info.start_date,
                "expected_completion": project.info.expected_completion,
                "overall_progress": project.overall_progress.percentage,
                "locations": [
                    {
                        "id": str(loc.id),
                        "name": loc.name,
                        "description": loc.description,
                        "progress": loc.progress.percentage
                    }
                    for loc in project.locations
                ],
                "timeline": {
                    "total_days": project.timeline.get_total_days() if project.timeline else 0,
                    "elapsed_days": project.timeline.get_elapsed_days() if project.timeline else 0,
                    "remaining_days": project.timeline.get_remaining_days() if project.timeline else 0
                },
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None
            }

        except Exception as e:
            logger.error(f"Error getting project summary: {str(e)}")
            return {}