# Database Documentation

This document provides comprehensive documentation for the MongoDB database implementation in the Construction Analysis AI System.

## Database Overview

### Technology Stack
- **Database**: MongoDB 7.0+
- **Driver**: Motor (AsyncIOMotorClient) for Python async support
- **ODM**: Custom implementation with Pydantic models
- **Connection**: Connection pooling with async context management
- **Indexing**: Strategic indexes for performance optimization

### Database Architecture
```
MongoDB Instance
├── construction_ai (Database)
│   ├── projects (Collection)
│   ├── analyses (Collection)
│   ├── files (Collection)
│   ├── chat_sessions (Collection)
│   ├── reports (Collection)
│   ├── users (Collection - Future)
│   └── system_logs (Collection)
```

## Database Configuration

### Connection Setup
```python
# src/infrastructure/database/connection.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
import asyncio
import logging

from ..config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """MongoDB connection manager with async support."""

    _client: Optional[AsyncIOMotorClient] = None
    _database = None

    @classmethod
    async def get_client(cls) -> AsyncIOMotorClient:
        """Get or create MongoDB client."""
        if cls._client is None:
            cls._client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=20,
                minPoolSize=5,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000
            )

            # Test connection
            try:
                await cls._client.admin.command('ping')
                logger.info("MongoDB connection established")
            except Exception as e:
                logger.error(f"MongoDB connection failed: {e}")
                raise

        return cls._client

    @classmethod
    async def get_database(cls):
        """Get database instance."""
        if cls._database is None:
            client = await cls.get_client()
            cls._database = client[settings.database_name]
        return cls._database

    @classmethod
    async def close_connection(cls):
        """Close database connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._database = None
            logger.info("MongoDB connection closed")

# Global database access
async def get_database():
    """Get database instance for dependency injection."""
    return await DatabaseConnection.get_database()
```

### Connection Pool Configuration
```python
# Connection pool settings
MONGODB_CONFIG = {
    "maxPoolSize": 20,  # Maximum connections in pool
    "minPoolSize": 5,   # Minimum connections in pool
    "maxIdleTimeMS": 30000,  # 30 seconds
    "waitQueueTimeoutMS": 5000,  # 5 seconds
    "serverSelectionTimeoutMS": 5000,  # 5 seconds
    "connectTimeoutMS": 10000,  # 10 seconds
    "socketTimeoutMS": 20000,  # 20 seconds
    "heartbeatFrequencyMS": 10000,  # 10 seconds
}
```

## Data Models

### Project Model
```python
# src/domain/entities/project.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

class ProjectType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INFRASTRUCTURE = "infrastructure"
    RENOVATION = "renovation"

class ProjectDocument(BaseModel):
    """MongoDB document model for construction projects."""

    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    location: str = Field(..., min_length=1, max_length=500)
    type: ProjectType
    status: ProjectStatus = ProjectStatus.ACTIVE

    # Dates
    start_date: Optional[datetime] = None
    estimated_end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Financial
    budget: Optional[float] = Field(None, ge=0)
    spent: Optional[float] = Field(None, ge=0)

    # Progress
    progress_percentage: float = Field(0.0, ge=0, le=100)
    current_phase: Optional[str] = None

    # Project details
    contractor: Optional[str] = None
    project_manager: Optional[str] = None
    stakeholders: List[str] = Field(default_factory=list)

    # Metadata
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

    # Analysis summary
    total_analyses: int = 0
    last_analysis_date: Optional[datetime] = None
    safety_score: Optional[float] = Field(None, ge=0, le=100)
    quality_score: Optional[float] = Field(None, ge=0, le=100)

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "name": "Downtown Office Building",
                "description": "Modern 10-story office building construction",
                "location": "123 Main St, Downtown, NY",
                "type": "commercial",
                "status": "active",
                "start_date": "2024-01-15T00:00:00Z",
                "estimated_end_date": "2024-12-31T00:00:00Z",
                "budget": 5000000.0,
                "contractor": "ABC Construction Co.",
                "progress_percentage": 45.5
            }
        }
```

### Analysis Model
```python
# src/domain/entities/analysis.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId

class AnalysisType(str, Enum):
    VISUAL = "visual"
    DOCUMENT = "document"
    PROGRESS = "progress"
    SAFETY = "safety"
    QUALITY = "quality"

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisDocument(BaseModel):
    """MongoDB document model for analysis results."""

    id: Optional[str] = Field(None, alias="_id")
    project_id: str = Field(..., description="Associated project ID")
    type: AnalysisType
    status: AnalysisStatus = AnalysisStatus.PENDING

    # Input data
    input_files: List[str] = Field(default_factory=list)
    input_data: Dict[str, Any] = Field(default_factory=dict)

    # Results
    result: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    processing_time: Optional[float] = Field(None, ge=0)

    # Agent information
    agent_name: Optional[str] = None
    agent_version: Optional[str] = None
    model_used: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
```

### File Model
```python
# src/domain/entities/file.py
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class FileType(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"

class FileStatus(str, Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class FileDocument(BaseModel):
    """MongoDB document model for file metadata."""

    id: Optional[str] = Field(None, alias="_id")
    project_id: Optional[str] = None
    analysis_id: Optional[str] = None

    # File information
    filename: str
    original_filename: str
    file_type: FileType
    mime_type: str
    file_size: int = Field(..., ge=0)

    # Storage information
    storage_path: str
    storage_bucket: str
    file_hash: Optional[str] = None

    # Status
    status: FileStatus = FileStatus.UPLOADING
    upload_progress: float = Field(0.0, ge=0, le=100)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    # File analysis results
    analysis_results: Dict[str, Any] = Field(default_factory=dict)

    # Access control
    is_public: bool = False
    access_permissions: List[str] = Field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
```

### Chat Session Model
```python
# src/domain/entities/chat_session.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    """Individual chat message."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatSessionDocument(BaseModel):
    """MongoDB document model for chat sessions."""

    id: Optional[str] = Field(None, alias="_id")
    session_id: str = Field(..., description="Unique session identifier")
    project_id: Optional[str] = None
    user_id: Optional[str] = None

    # Session data
    messages: List[ChatMessage] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)

    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    # Statistics
    message_count: int = 0
    total_tokens_used: int = 0

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
```

## Repository Pattern Implementation

### Base Repository
```python
# src/infrastructure/database/repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Abstract base repository with common database operations."""

    def __init__(self, database: AsyncIOMotorDatabase, collection_name: str):
        self.database = database
        self.collection: AsyncIOMotorCollection = database[collection_name]
        self.collection_name = collection_name

    @abstractmethod
    def _to_dict(self, entity: T) -> Dict[str, Any]:
        """Convert entity to dictionary for MongoDB."""
        pass

    @abstractmethod
    def _from_dict(self, data: Dict[str, Any]) -> T:
        """Convert dictionary from MongoDB to entity."""
        pass

    async def save(self, entity: T) -> T:
        """Save entity to database."""
        try:
            entity_dict = self._to_dict(entity)

            if hasattr(entity, 'id') and entity.id:
                # Update existing
                result = await self.collection.replace_one(
                    {"_id": ObjectId(entity.id)},
                    entity_dict
                )
                if result.matched_count == 0:
                    raise ValueError(f"Entity with ID {entity.id} not found")
            else:
                # Create new
                result = await self.collection.insert_one(entity_dict)
                entity.id = str(result.inserted_id)

            logger.debug(f"Saved entity to {self.collection_name}: {entity.id}")
            return entity

        except Exception as e:
            logger.error(f"Error saving entity to {self.collection_name}: {e}")
            raise

    async def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find entity by ID."""
        try:
            if not ObjectId.is_valid(entity_id):
                return None

            doc = await self.collection.find_one({"_id": ObjectId(entity_id)})
            return self._from_dict(doc) if doc else None

        except Exception as e:
            logger.error(f"Error finding entity by ID in {self.collection_name}: {e}")
            return None

    async def find_all(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_direction: int = ASCENDING,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[T]:
        """Find entities with filtering, sorting, and pagination."""
        try:
            query = filter_criteria or {}
            cursor = self.collection.find(query)

            if sort_by:
                cursor = cursor.sort(sort_by, sort_direction)

            if offset > 0:
                cursor = cursor.skip(offset)

            if limit:
                cursor = cursor.limit(limit)

            docs = await cursor.to_list(length=limit)
            return [self._from_dict(doc) for doc in docs]

        except Exception as e:
            logger.error(f"Error finding entities in {self.collection_name}: {e}")
            return []

    async def count(self, filter_criteria: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching criteria."""
        try:
            query = filter_criteria or {}
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting entities in {self.collection_name}: {e}")
            return 0

    async def delete_by_id(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        try:
            if not ObjectId.is_valid(entity_id):
                return False

            result = await self.collection.delete_one({"_id": ObjectId(entity_id)})
            success = result.deleted_count > 0

            if success:
                logger.debug(f"Deleted entity from {self.collection_name}: {entity_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting entity from {self.collection_name}: {e}")
            return False

    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        try:
            if not ObjectId.is_valid(entity_id):
                return False

            count = await self.collection.count_documents(
                {"_id": ObjectId(entity_id)},
                limit=1
            )
            return count > 0

        except Exception as e:
            logger.error(f"Error checking entity existence in {self.collection_name}: {e}")
            return False
```

### Project Repository
```python
# src/infrastructure/database/repositories/project_repository.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from pymongo import DESCENDING

from .base_repository import BaseRepository
from ...domain.entities.project import ProjectDocument, ProjectStatus, ProjectType

class ProjectRepository(BaseRepository[ProjectDocument]):
    """Repository for project operations."""

    def __init__(self, database):
        super().__init__(database, "projects")

    def _to_dict(self, project: ProjectDocument) -> Dict[str, Any]:
        """Convert project entity to MongoDB document."""
        data = project.dict(exclude={"id"}, by_alias=True)

        # Ensure updated_at is current
        data["updated_at"] = datetime.utcnow()

        return data

    def _from_dict(self, data: Dict[str, Any]) -> ProjectDocument:
        """Convert MongoDB document to project entity."""
        data["_id"] = str(data["_id"])
        return ProjectDocument(**data)

    async def find_by_name(self, name: str) -> Optional[ProjectDocument]:
        """Find project by exact name."""
        doc = await self.collection.find_one({"name": name})
        return self._from_dict(doc) if doc else None

    async def find_by_status(
        self,
        status: ProjectStatus,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ProjectDocument]:
        """Find projects by status."""
        return await self.find_all(
            filter_criteria={"status": status.value},
            sort_by="updated_at",
            sort_direction=DESCENDING,
            limit=limit,
            offset=offset
        )

    async def find_by_type(
        self,
        project_type: ProjectType,
        limit: Optional[int] = None
    ) -> List[ProjectDocument]:
        """Find projects by type."""
        return await self.find_all(
            filter_criteria={"type": project_type.value},
            sort_by="created_at",
            sort_direction=DESCENDING,
            limit=limit
        )

    async def search_projects(
        self,
        search_term: str,
        limit: int = 50
    ) -> List[ProjectDocument]:
        """Search projects by name, description, or location."""
        query = {
            "$or": [
                {"name": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}},
                {"location": {"$regex": search_term, "$options": "i"}}
            ]
        }

        return await self.find_all(
            filter_criteria=query,
            sort_by="updated_at",
            sort_direction=DESCENDING,
            limit=limit
        )

    async def get_recent_projects(self, limit: int = 10) -> List[ProjectDocument]:
        """Get most recently updated projects."""
        return await self.find_all(
            sort_by="updated_at",
            sort_direction=DESCENDING,
            limit=limit
        )

    async def get_active_projects(self) -> List[ProjectDocument]:
        """Get all active projects."""
        return await self.find_by_status(ProjectStatus.ACTIVE)

    async def update_progress(
        self,
        project_id: str,
        progress_percentage: float,
        current_phase: Optional[str] = None
    ) -> bool:
        """Update project progress."""
        try:
            update_data = {
                "progress_percentage": progress_percentage,
                "updated_at": datetime.utcnow()
            }

            if current_phase:
                update_data["current_phase"] = current_phase

            result = await self.collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": update_data}
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating project progress: {e}")
            return False

    async def get_project_statistics(self) -> Dict[str, Any]:
        """Get aggregated project statistics."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "avg_progress": {"$avg": "$progress_percentage"},
                        "total_budget": {"$sum": "$budget"}
                    }
                }
            ]

            cursor = self.collection.aggregate(pipeline)
            stats = await cursor.to_list(length=None)

            return {stat["_id"]: stat for stat in stats}

        except Exception as e:
            logger.error(f"Error getting project statistics: {e}")
            return {}
```

## Database Indexing Strategy

### Index Definitions
```python
# src/infrastructure/database/indexes.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
import logging

logger = logging.getLogger(__name__)

async def create_indexes(database: AsyncIOMotorDatabase):
    """Create all necessary indexes for optimal performance."""

    # Projects Collection Indexes
    projects_indexes = [
        IndexModel([("status", ASCENDING)]),
        IndexModel([("type", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("updated_at", DESCENDING)]),
        IndexModel([("progress_percentage", ASCENDING)]),
        IndexModel([("start_date", ASCENDING)]),
        IndexModel([("estimated_end_date", ASCENDING)]),
        IndexModel([("name", TEXT), ("description", TEXT), ("location", TEXT)]),  # Text search
        IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),  # Compound
        IndexModel([("type", ASCENDING), ("status", ASCENDING)]),  # Compound
    ]

    # Analyses Collection Indexes
    analyses_indexes = [
        IndexModel([("project_id", ASCENDING)]),
        IndexModel([("type", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("completed_at", DESCENDING)]),
        IndexModel([("project_id", ASCENDING), ("type", ASCENDING)]),  # Compound
        IndexModel([("project_id", ASCENDING), ("created_at", DESCENDING)]),  # Compound
        IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),  # Compound
    ]

    # Files Collection Indexes
    files_indexes = [
        IndexModel([("project_id", ASCENDING)]),
        IndexModel([("analysis_id", ASCENDING)]),
        IndexModel([("file_type", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("file_hash", ASCENDING)], unique=True, sparse=True),
        IndexModel([("project_id", ASCENDING), ("file_type", ASCENDING)]),  # Compound
        IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),  # Compound
    ]

    # Chat Sessions Collection Indexes
    chat_sessions_indexes = [
        IndexModel([("session_id", ASCENDING)], unique=True),
        IndexModel([("project_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("last_activity", DESCENDING)]),
        IndexModel([("is_active", ASCENDING)]),
        IndexModel([("project_id", ASCENDING), ("created_at", DESCENDING)]),  # Compound
    ]

    # Create indexes
    collections_indexes = [
        ("projects", projects_indexes),
        ("analyses", analyses_indexes),
        ("files", files_indexes),
        ("chat_sessions", chat_sessions_indexes),
    ]

    for collection_name, indexes in collections_indexes:
        try:
            collection = database[collection_name]
            if indexes:
                await collection.create_indexes(indexes)
                logger.info(f"Created {len(indexes)} indexes for {collection_name}")
        except Exception as e:
            logger.error(f"Error creating indexes for {collection_name}: {e}")

async def drop_indexes(database: AsyncIOMotorDatabase, collection_name: str):
    """Drop all indexes for a collection (except _id)."""
    try:
        collection = database[collection_name]
        await collection.drop_indexes()
        logger.info(f"Dropped indexes for {collection_name}")
    except Exception as e:
        logger.error(f"Error dropping indexes for {collection_name}: {e}")
```

## Database Migrations

### Migration Framework
```python
# src/infrastructure/database/migrations/migration_runner.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

class Migration(ABC):
    """Abstract base class for database migrations."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Migration version identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Migration description."""
        pass

    @abstractmethod
    async def up(self, database: AsyncIOMotorDatabase):
        """Apply migration."""
        pass

    @abstractmethod
    async def down(self, database: AsyncIOMotorDatabase):
        """Rollback migration."""
        pass

class MigrationRunner:
    """Handles running database migrations."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.migrations_collection = database.migrations

    async def run_migrations(self, migrations: List[Migration]):
        """Run all pending migrations."""
        applied_migrations = await self._get_applied_migrations()

        for migration in migrations:
            if migration.version not in applied_migrations:
                try:
                    logger.info(f"Running migration {migration.version}: {migration.description}")
                    await migration.up(self.database)
                    await self._record_migration(migration)
                    logger.info(f"Migration {migration.version} completed")
                except Exception as e:
                    logger.error(f"Migration {migration.version} failed: {e}")
                    raise

    async def rollback_migration(self, migration: Migration):
        """Rollback a specific migration."""
        try:
            logger.info(f"Rolling back migration {migration.version}")
            await migration.down(self.database)
            await self._remove_migration_record(migration.version)
            logger.info(f"Migration {migration.version} rolled back")
        except Exception as e:
            logger.error(f"Rollback of migration {migration.version} failed: {e}")
            raise

    async def _get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        cursor = self.migrations_collection.find({}, {"version": 1})
        docs = await cursor.to_list(length=None)
        return [doc["version"] for doc in docs]

    async def _record_migration(self, migration: Migration):
        """Record migration as applied."""
        await self.migrations_collection.insert_one({
            "version": migration.version,
            "description": migration.description,
            "applied_at": datetime.utcnow()
        })

    async def _remove_migration_record(self, version: str):
        """Remove migration record."""
        await self.migrations_collection.delete_one({"version": version})
```

### Example Migration
```python
# src/infrastructure/database/migrations/v001_initial_setup.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from .migration_runner import Migration
from ..indexes import create_indexes

class InitialSetupMigration(Migration):
    """Initial database setup migration."""

    @property
    def version(self) -> str:
        return "001"

    @property
    def description(self) -> str:
        return "Initial database setup with collections and indexes"

    async def up(self, database: AsyncIOMotorDatabase):
        """Create initial collections and indexes."""
        # Create collections with validators
        await self._create_projects_collection(database)
        await self._create_analyses_collection(database)
        await self._create_files_collection(database)
        await self._create_chat_sessions_collection(database)

        # Create indexes
        await create_indexes(database)

    async def down(self, database: AsyncIOMotorDatabase):
        """Drop all collections."""
        collections = ["projects", "analyses", "files", "chat_sessions"]
        for collection_name in collections:
            await database.drop_collection(collection_name)

    async def _create_projects_collection(self, database: AsyncIOMotorDatabase):
        """Create projects collection with validation."""
        await database.create_collection(
            "projects",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["name", "location", "type", "status"],
                    "properties": {
                        "name": {"bsonType": "string", "minLength": 1, "maxLength": 200},
                        "location": {"bsonType": "string", "minLength": 1, "maxLength": 500},
                        "type": {"enum": ["residential", "commercial", "industrial", "infrastructure", "renovation"]},
                        "status": {"enum": ["active", "completed", "suspended", "cancelled"]},
                        "progress_percentage": {"bsonType": "number", "minimum": 0, "maximum": 100}
                    }
                }
            }
        )

    async def _create_analyses_collection(self, database: AsyncIOMotorDatabase):
        """Create analyses collection with validation."""
        await database.create_collection(
            "analyses",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["project_id", "type", "status"],
                    "properties": {
                        "project_id": {"bsonType": "string"},
                        "type": {"enum": ["visual", "document", "progress", "safety", "quality"]},
                        "status": {"enum": ["pending", "processing", "completed", "failed"]},
                        "confidence_score": {"bsonType": "number", "minimum": 0, "maximum": 1}
                    }
                }
            }
        )

    async def _create_files_collection(self, database: AsyncIOMotorDatabase):
        """Create files collection with validation."""
        await database.create_collection(
            "files",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["filename", "file_type", "file_size", "storage_path"],
                    "properties": {
                        "filename": {"bsonType": "string", "minLength": 1},
                        "file_type": {"enum": ["image", "document", "video", "audio", "other"]},
                        "file_size": {"bsonType": "number", "minimum": 0},
                        "storage_path": {"bsonType": "string", "minLength": 1}
                    }
                }
            }
        )

    async def _create_chat_sessions_collection(self, database: AsyncIOMotorDatabase):
        """Create chat sessions collection."""
        await database.create_collection("chat_sessions")
```

## Query Optimization

### Aggregation Pipelines
```python
# Common aggregation queries for reporting and analytics

async def get_project_progress_summary(database: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Get project progress summary using aggregation."""
    pipeline = [
        {
            "$match": {"status": "active"}
        },
        {
            "$group": {
                "_id": "$type",
                "count": {"$sum": 1},
                "avg_progress": {"$avg": "$progress_percentage"},
                "min_progress": {"$min": "$progress_percentage"},
                "max_progress": {"$max": "$progress_percentage"},
                "total_budget": {"$sum": "$budget"}
            }
        },
        {
            "$sort": {"count": -1}
        }
    ]

    cursor = database.projects.aggregate(pipeline)
    return await cursor.to_list(length=None)

async def get_analysis_trends(database: AsyncIOMotorDatabase, days: int = 30) -> List[Dict[str, Any]]:
    """Get analysis trends over time."""
    from datetime import datetime, timedelta

    start_date = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start_date},
                "status": "completed"
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "type": "$type"
                },
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$confidence_score"}
            }
        },
        {
            "$sort": {"_id.date": 1}
        }
    ]

    cursor = database.analyses.aggregate(pipeline)
    return await cursor.to_list(length=None)
```

### Performance Monitoring
```python
# Monitor database performance and slow queries

async def monitor_slow_queries(database: AsyncIOMotorDatabase):
    """Monitor and log slow queries."""
    # Enable profiling for slow operations (>100ms)
    await database.command({
        "profile": 2,
        "slowms": 100,
        "sampleRate": 1.0
    })

async def get_database_stats(database: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Get database statistics."""
    stats = await database.command("dbStats")
    return {
        "collections": stats.get("collections", 0),
        "objects": stats.get("objects", 0),
        "avgObjSize": stats.get("avgObjSize", 0),
        "dataSize": stats.get("dataSize", 0),
        "storageSize": stats.get("storageSize", 0),
        "indexes": stats.get("indexes", 0),
        "indexSize": stats.get("indexSize", 0)
    }
```

This comprehensive database documentation provides the foundation for implementing a robust, scalable, and performant MongoDB-based data layer for the Construction Analysis AI System.