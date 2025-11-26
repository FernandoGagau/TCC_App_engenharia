#!/usr/bin/env python3
"""
Script to migrate JSON data to MongoDB
Loads all data from backend/data/*.json files to MongoDB
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add backend src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from infrastructure.database.models import (
    SessionModel,
    MessageModel,
    ProjectModel,
    ImageAnalysisModel,
    EventModel,
    LocationModel,
    DetectedElement,
    SessionStatus,
    MessageRole,
    ProjectType
)


async def connect_mongodb():
    """Connect to MongoDB"""
    # Get connection from environment or use default for local
    mongodb_url = os.getenv("DB_MONGODB_URL", "mongodb://localhost:27017/construction_agent")

    print(f"Connecting to MongoDB: {mongodb_url}")

    client = AsyncIOMotorClient(mongodb_url)
    database = client.construction_agent

    # Initialize Beanie
    await init_beanie(
        database=database,
        document_models=[
            SessionModel,
            MessageModel,
            ProjectModel,
            ImageAnalysisModel,
            EventModel
        ]
    )

    # Test connection
    await client.admin.command('ping')
    print("✅ MongoDB connected successfully")

    return database


async def migrate_sessions(data_dir: Path):
    """Migrate sessions from JSON to MongoDB"""
    sessions_file = data_dir / "sessions.json"

    if not sessions_file.exists():
        print("⚠️ sessions.json not found")
        return

    with open(sessions_file, 'r') as f:
        sessions_data = json.load(f)

    count = 0
    for session_id, session_data in sessions_data.items():
        # Create session document
        session = SessionModel(
            session_id=session_id,
            user_id=session_data.get("user_id", "default_user"),
            status=SessionStatus.INACTIVE,
            created_at=datetime.fromisoformat(session_data.get("created_at", datetime.utcnow().isoformat())),
            title=session_data.get("title", "Session " + session_id[:8]),
            metadata=session_data.get("metadata", {})
        )

        # Save to MongoDB
        await session.save()

        # Migrate messages for this session
        messages = session_data.get("messages", [])
        for msg in messages:
            message = MessageModel(
                session_id=session_id,
                role=MessageRole(msg.get("role", "user")),
                content=msg.get("content", ""),
                timestamp=datetime.fromisoformat(msg.get("timestamp", datetime.utcnow().isoformat())),
                metadata=msg.get("metadata", {})
            )
            await message.save()

        count += 1
        print(f"  Migrated session {session_id[:8]}... with {len(messages)} messages")

    print(f"✅ Migrated {count} sessions")


async def migrate_projects(data_dir: Path):
    """Migrate projects from JSON to MongoDB"""
    projects_file = data_dir / "projects.json"

    if not projects_file.exists():
        print("⚠️ projects.json not found")
        return

    with open(projects_file, 'r') as f:
        projects_data = json.load(f)

    count = 0
    for project_id, project_data in projects_data.items():
        # Create project document
        locations = []
        for loc_data in project_data.get("locations", []):
            location = LocationModel(
                location_id=loc_data.get("location_id", str(uuid4())),
                location_name=loc_data.get("location_name", "Unknown"),
                location_type=loc_data.get("location_type"),
                current_phase=loc_data.get("current_phase"),
                progress=loc_data.get("progress", 0),
                cameras=loc_data.get("cameras", [])
            )
            locations.append(location)

        project = ProjectModel(
            project_id=project_id,
            project_name=project_data.get("project_name", "Unknown Project"),
            project_type=ProjectType(project_data.get("project_type", "residential")),
            address=project_data.get("address"),
            responsible_engineer=project_data.get("responsible_engineer"),
            start_date=datetime.fromisoformat(project_data["start_date"]) if "start_date" in project_data else None,
            expected_completion=datetime.fromisoformat(project_data["expected_completion"]) if "expected_completion" in project_data else None,
            current_phase=project_data.get("current_phase"),
            progress_percentage=project_data.get("progress_percentage", 0.0),
            locations=locations,
            metadata=project_data.get("metadata", {})
        )

        await project.save()
        count += 1
        print(f"  Migrated project {project_name}")

    print(f"✅ Migrated {count} projects")


async def migrate_analysis(data_dir: Path):
    """Migrate image analysis from JSON to MongoDB"""
    analysis_file = data_dir / "image_analysis.json"

    if not analysis_file.exists():
        print("⚠️ image_analysis.json not found")
        return

    with open(analysis_file, 'r') as f:
        analysis_data = json.load(f)

    count = 0
    for analysis_id, data in analysis_data.items():
        # Create detected elements
        elements = []
        for elem_data in data.get("detected_elements", []):
            element = DetectedElement(
                element_type=elem_data.get("element_type", "unknown"),
                confidence=elem_data.get("confidence", 0.0),
                bounding_box=elem_data.get("bounding_box"),
                attributes=elem_data.get("attributes", {})
            )
            elements.append(element)

        analysis = ImageAnalysisModel(
            analysis_id=analysis_id,
            project_id=data.get("project_id", ""),
            location_id=data.get("location_id"),
            image_url=data.get("image_url", ""),
            analysis_date=datetime.fromisoformat(data.get("analysis_date", datetime.utcnow().isoformat())),
            detected_phase=data.get("detected_phase"),
            detected_elements=elements,
            confidence_score=data.get("confidence_score", 0.0),
            quality_score=data.get("quality_score"),
            safety_issues=data.get("safety_issues", []),
            recommendations=data.get("recommendations", []),
            metadata=data.get("metadata", {})
        )

        await analysis.save()
        count += 1

    print(f"✅ Migrated {count} image analysis records")


async def main():
    """Main migration function"""
    print("🚀 Starting data migration to MongoDB...")

    # Connect to MongoDB
    try:
        db = await connect_mongodb()
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        print("Make sure MongoDB is running (docker-compose up -d)")
        return 1

    # Get data directory
    data_dir = Path(__file__).parent.parent / "data"

    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return 1

    print(f"📁 Loading data from: {data_dir}")

    # Migrate all data
    try:
        await migrate_sessions(data_dir)
        await migrate_projects(data_dir)
        await migrate_analysis(data_dir)

        print("\n✅ Migration completed successfully!")

        # Show statistics
        sessions_count = await SessionModel.count()
        messages_count = await MessageModel.count()
        projects_count = await ProjectModel.count()
        analysis_count = await ImageAnalysisModel.count()

        print("\n📊 Database Statistics:")
        print(f"  - Sessions: {sessions_count}")
        print(f"  - Messages: {messages_count}")
        print(f"  - Projects: {projects_count}")
        print(f"  - Image Analysis: {analysis_count}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)