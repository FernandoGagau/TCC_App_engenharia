# Database Development Agent

## Overview

The Database Development Agent specializes in MongoDB database design, optimization, and management for the Construction Analysis AI System. This agent provides guidance on data modeling, query optimization, indexing strategies, and database architecture best practices.

## Capabilities

### 🗄️ Database Design
- MongoDB schema design and modeling
- Document structure optimization
- Relationship modeling in NoSQL
- Data validation and constraints
- Migration strategies and versioning

### ⚡ Performance Optimization
- Query optimization and analysis
- Index design and management
- Aggregation pipeline optimization
- Connection pooling and management
- Caching strategies

### 🔄 Data Operations
- CRUD operations design
- Bulk operations and transactions
- Data aggregation and reporting
- Search and filtering optimization
- Data archiving and cleanup

## Core Responsibilities

### 1. Data Model Design

#### Core Collections Schema
```python
# models/schemas/project_schema.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class ProjectType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INFRASTRUCTURE = "infrastructure"
    RENOVATION = "renovation"

class Location(BaseModel):
    address: str
    city: str
    state: str
    country: str
    postal_code: str
    coordinates: Optional[Dict[str, float]] = None  # {"lat": float, "lng": float}

class Budget(BaseModel):
    total_budget: float
    allocated_budget: float
    spent_amount: float
    remaining_budget: float
    currency: str = "USD"
    last_updated: datetime

class ProjectSchema(BaseModel):
    """MongoDB document schema for projects collection"""

    # MongoDB ObjectId
    _id: Optional[ObjectId] = Field(alias="id")

    # Basic Information
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    project_type: ProjectType
    status: ProjectStatus = ProjectStatus.PLANNING

    # Dates
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    start_date: datetime
    expected_completion: datetime
    actual_completion: Optional[datetime] = None

    # Financial
    budget: Budget

    # Location
    location: Location

    # People
    owner_id: str  # User ID who owns this project
    project_manager_id: Optional[str] = None
    team_members: List[str] = []  # List of user IDs

    # Project Details
    specifications: Dict[str, Any] = {}
    requirements: List[str] = []
    tags: List[str] = []

    # Status Tracking
    progress_percentage: float = Field(0.0, ge=0, le=100)
    milestones: List[Dict[str, Any]] = []

    # File References
    documents: List[str] = []  # File IDs
    images: List[str] = []     # File IDs
    reports: List[str] = []    # Analysis report IDs

    # Metadata
    metadata: Dict[str, Any] = {}
    version: int = 1

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# MongoDB Indexes for projects collection
PROJECT_INDEXES = [
    {"owner_id": 1},                                      # User's projects
    {"status": 1, "created_at": -1},                     # Status filtering with recency
    {"project_type": 1, "status": 1},                    # Type and status filtering
    {"start_date": 1, "expected_completion": 1},         # Date range queries
    {"location.city": 1, "location.state": 1},          # Location-based queries
    {"name": "text", "description": "text"},             # Full-text search
    {"tags": 1},                                         # Tag-based filtering
    {"progress_percentage": 1},                          # Progress queries
    {"budget.total_budget": 1},                          # Budget range queries
    {"team_members": 1},                                 # Team member projects
    {"created_at": -1},                                  # Recent projects
    {"updated_at": -1},                                  # Recently updated
]
```

#### Analysis Results Schema
```python
# models/schemas/analysis_schema.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId

class AnalysisType(str, Enum):
    PROGRESS_TRACKING = "progress_tracking"
    QUALITY_INSPECTION = "quality_inspection"
    SAFETY_ASSESSMENT = "safety_assessment"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    MATERIAL_VERIFICATION = "material_verification"
    COMPLIANCE_CHECK = "compliance_check"
    COST_ANALYSIS = "cost_analysis"

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Finding(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity
    category: str
    location: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    recommendations: List[str] = []
    images: List[str] = []  # File IDs
    metadata: Dict[str, Any] = {}

class AnalysisResult(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    findings: List[Finding] = []
    summary: str
    recommendations: List[str] = []
    risk_assessment: Dict[str, Any] = {}
    compliance_status: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class AnalysisSchema(BaseModel):
    """MongoDB document schema for analyses collection"""

    _id: Optional[ObjectId] = Field(alias="id")

    # Basic Information
    project_id: str  # Reference to project
    analysis_type: AnalysisType
    status: AnalysisStatus = AnalysisStatus.PENDING

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Input Data
    input_files: List[str] = []  # File IDs
    parameters: Dict[str, Any] = {}

    # Results
    result: Optional[AnalysisResult] = None

    # Processing Information
    agent_used: str
    model_used: str
    processing_time_seconds: Optional[float] = None
    tokens_used: Optional[int] = None

    # User Information
    requested_by: str  # User ID

    # Error Handling
    error_message: Optional[str] = None
    retry_count: int = 0

    # Version and Metadata
    version: int = 1
    metadata: Dict[str, Any] = {}

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# MongoDB Indexes for analyses collection
ANALYSIS_INDEXES = [
    {"project_id": 1, "created_at": -1},                 # Project analyses
    {"analysis_type": 1, "status": 1},                  # Type and status filtering
    {"status": 1, "created_at": -1},                    # Status with recency
    {"requested_by": 1, "created_at": -1},              # User's analyses
    {"result.overall_score": 1},                        # Score-based queries
    {"result.findings.severity": 1},                    # Severity filtering
    {"completed_at": -1},                               # Recent completions
    {"processing_time_seconds": 1},                     # Performance analysis
]
```

### 2. Repository Implementation

#### Advanced MongoDB Repository
```python
# infrastructure/repositories/mongodb/base_repository.py
from typing import Generic, TypeVar, Optional, List, Dict, Any
from abc import ABC, abstractmethod
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from bson import ObjectId
import logging

T = TypeVar('T')

class BaseMongoRepository(Generic[T], ABC):
    """Base repository class for MongoDB operations"""

    def __init__(self, database: AsyncIOMotorDatabase, collection_name: str):
        self.db = database
        self.collection: AsyncIOMotorCollection = database[collection_name]
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def _document_to_entity(self, document: Dict[str, Any]) -> T:
        """Convert MongoDB document to domain entity"""
        pass

    @abstractmethod
    def _entity_to_document(self, entity: T) -> Dict[str, Any]:
        """Convert domain entity to MongoDB document"""
        pass

    async def create(self, entity: T) -> T:
        """Create a new document"""
        try:
            document = self._entity_to_document(entity)
            result = await self.collection.insert_one(document)

            # Set the ID on the entity if it wasn't set
            if hasattr(entity, 'id') and not entity.id:
                entity.id = str(result.inserted_id)

            self.logger.info(f"Created document with ID: {result.inserted_id}")
            return entity

        except Exception as e:
            self.logger.error(f"Error creating document: {str(e)}")
            raise

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get document by ID"""
        try:
            document = await self.collection.find_one({"_id": ObjectId(entity_id)})
            return self._document_to_entity(document) if document else None

        except Exception as e:
            self.logger.error(f"Error getting document by ID {entity_id}: {str(e)}")
            return None

    async def update(self, entity: T) -> T:
        """Update existing document"""
        try:
            document = self._entity_to_document(entity)
            entity_id = document.pop("_id", None)

            if not entity_id:
                raise ValueError("Entity must have an ID for update")

            result = await self.collection.replace_one(
                {"_id": ObjectId(entity_id)},
                document
            )

            if result.matched_count == 0:
                raise ValueError(f"No document found with ID: {entity_id}")

            self.logger.info(f"Updated document with ID: {entity_id}")
            return entity

        except Exception as e:
            self.logger.error(f"Error updating document: {str(e)}")
            raise

    async def delete(self, entity_id: str) -> bool:
        """Delete document by ID"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(entity_id)})
            deleted = result.deleted_count > 0

            if deleted:
                self.logger.info(f"Deleted document with ID: {entity_id}")
            else:
                self.logger.warning(f"No document found to delete with ID: {entity_id}")

            return deleted

        except Exception as e:
            self.logger.error(f"Error deleting document {entity_id}: {str(e)}")
            return False

    async def list(self,
                   filter_dict: Dict[str, Any] = None,
                   sort: List[tuple] = None,
                   limit: int = 100,
                   offset: int = 0) -> List[T]:
        """List documents with filtering, sorting, and pagination"""
        try:
            filter_dict = filter_dict or {}
            sort = sort or [("created_at", DESCENDING)]

            cursor = self.collection.find(filter_dict)

            # Apply sorting
            cursor = cursor.sort(sort)

            # Apply pagination
            cursor = cursor.skip(offset).limit(limit)

            documents = await cursor.to_list(length=limit)
            return [self._document_to_entity(doc) for doc in documents]

        except Exception as e:
            self.logger.error(f"Error listing documents: {str(e)}")
            return []

    async def count(self, filter_dict: Dict[str, Any] = None) -> int:
        """Count documents matching filter"""
        try:
            filter_dict = filter_dict or {}
            return await self.collection.count_documents(filter_dict)

        except Exception as e:
            self.logger.error(f"Error counting documents: {str(e)}")
            return 0

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline"""
        try:
            cursor = self.collection.aggregate(pipeline)
            return await cursor.to_list(length=None)

        except Exception as e:
            self.logger.error(f"Error executing aggregation: {str(e)}")
            return []

    async def create_indexes(self, indexes: List[Dict[str, Any]]):
        """Create indexes for the collection"""
        try:
            index_models = []

            for index_spec in indexes:
                if isinstance(index_spec, dict):
                    # Simple index specification
                    index_models.append(IndexModel(list(index_spec.items())))

            if index_models:
                await self.collection.create_indexes(index_models)
                self.logger.info(f"Created {len(index_models)} indexes")

        except Exception as e:
            self.logger.error(f"Error creating indexes: {str(e)}")
```

#### Specialized Project Repository
```python
# infrastructure/repositories/mongodb/project_repository.py
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pymongo import ASCENDING, DESCENDING

from domain.entities.project import Project
from models.schemas.project_schema import ProjectSchema, ProjectStatus, ProjectType
from infrastructure.repositories.mongodb.base_repository import BaseMongoRepository

class ProjectRepository(BaseMongoRepository[Project]):

    def __init__(self, database):
        super().__init__(database, "projects")

    def _document_to_entity(self, document: Dict[str, Any]) -> Project:
        """Convert MongoDB document to Project entity"""
        # Convert document to Pydantic model first
        schema = ProjectSchema(**document)

        # Convert to domain entity
        return Project(
            id=str(schema.id) if schema.id else None,
            name=schema.name,
            description=schema.description,
            project_type=schema.project_type,
            status=schema.status,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            start_date=schema.start_date,
            expected_completion=schema.expected_completion,
            actual_completion=schema.actual_completion,
            budget=schema.budget.dict(),
            location=schema.location.dict(),
            owner_id=schema.owner_id,
            project_manager_id=schema.project_manager_id,
            team_members=schema.team_members,
            progress_percentage=schema.progress_percentage,
            specifications=schema.specifications,
            requirements=schema.requirements,
            tags=schema.tags,
            documents=schema.documents,
            images=schema.images,
            reports=schema.reports,
            metadata=schema.metadata
        )

    def _entity_to_document(self, project: Project) -> Dict[str, Any]:
        """Convert Project entity to MongoDB document"""
        document = {
            "name": project.name,
            "description": project.description,
            "project_type": project.project_type.value if isinstance(project.project_type, ProjectType) else project.project_type,
            "status": project.status.value if isinstance(project.status, ProjectStatus) else project.status,
            "created_at": project.created_at,
            "updated_at": datetime.utcnow(),  # Always update timestamp
            "start_date": project.start_date,
            "expected_completion": project.expected_completion,
            "actual_completion": project.actual_completion,
            "budget": project.budget,
            "location": project.location,
            "owner_id": project.owner_id,
            "project_manager_id": project.project_manager_id,
            "team_members": project.team_members or [],
            "progress_percentage": project.progress_percentage,
            "specifications": project.specifications or {},
            "requirements": project.requirements or [],
            "tags": project.tags or [],
            "documents": project.documents or [],
            "images": project.images or [],
            "reports": project.reports or [],
            "metadata": project.metadata or {}
        }

        if project.id:
            document["_id"] = ObjectId(project.id)

        return document

    async def find_by_owner(self, owner_id: str, limit: int = 100) -> List[Project]:
        """Find projects by owner ID"""
        return await self.list(
            filter_dict={"owner_id": owner_id},
            sort=[("updated_at", DESCENDING)],
            limit=limit
        )

    async def find_by_status(self, status: ProjectStatus, limit: int = 100) -> List[Project]:
        """Find projects by status"""
        return await self.list(
            filter_dict={"status": status.value},
            sort=[("created_at", DESCENDING)],
            limit=limit
        )

    async def find_by_team_member(self, user_id: str) -> List[Project]:
        """Find projects where user is a team member"""
        return await self.list(
            filter_dict={"team_members": user_id},
            sort=[("updated_at", DESCENDING)]
        )

    async def search_by_text(self, query: str, limit: int = 50) -> List[Project]:
        """Full-text search in project names and descriptions"""
        return await self.list(
            filter_dict={"$text": {"$search": query}},
            sort=[("score", {"$meta": "textScore"})],
            limit=limit
        )

    async def find_overdue_projects(self) -> List[Project]:
        """Find projects that are past their expected completion date"""
        current_date = datetime.utcnow()
        return await self.list(
            filter_dict={
                "expected_completion": {"$lt": current_date},
                "status": {"$ne": ProjectStatus.COMPLETED.value}
            },
            sort=[("expected_completion", ASCENDING)]
        )

    async def get_project_statistics(self, owner_id: str = None) -> Dict[str, Any]:
        """Get project statistics with optional owner filter"""
        pipeline = []

        # Optional filter by owner
        if owner_id:
            pipeline.append({"$match": {"owner_id": owner_id}})

        # Group by status and calculate statistics
        pipeline.extend([
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total_budget": {"$sum": "$budget.total_budget"},
                    "avg_progress": {"$avg": "$progress_percentage"}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "by_status": {
                        "$push": {
                            "status": "$_id",
                            "count": "$count",
                            "total_budget": "$total_budget",
                            "avg_progress": "$avg_progress"
                        }
                    },
                    "total_projects": {"$sum": "$count"},
                    "total_value": {"$sum": "$total_budget"}
                }
            }
        ])

        results = await self.aggregate(pipeline)

        if results:
            result = results[0]
            return {
                "total_projects": result.get("total_projects", 0),
                "total_value": result.get("total_value", 0),
                "by_status": {
                    item["status"]: {
                        "count": item["count"],
                        "total_budget": item["total_budget"],
                        "avg_progress": item["avg_progress"]
                    }
                    for item in result.get("by_status", [])
                }
            }

        return {"total_projects": 0, "total_value": 0, "by_status": {}}

    async def get_monthly_project_creation(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get project creation statistics by month"""
        start_date = datetime.utcnow() - timedelta(days=months * 30)

        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1},
                    "total_budget": {"$sum": "$budget.total_budget"}
                }
            },
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]

        return await self.aggregate(pipeline)
```

### 3. Query Optimization

#### Query Performance Analyzer
```python
# infrastructure/database/query_analyzer.py
import time
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorCollection
import logging

class QueryPerformanceAnalyzer:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.slow_query_threshold = 1000  # milliseconds

    async def analyze_query_performance(self,
                                      collection: AsyncIOMotorCollection,
                                      filter_dict: Dict[str, Any],
                                      operation: str = "find") -> Dict[str, Any]:
        """Analyze query performance and suggest optimizations"""

        start_time = time.time()

        # Execute explain for the query
        if operation == "find":
            explain_result = await collection.find(filter_dict).explain()
        elif operation == "aggregate":
            explain_result = await collection.aggregate([{"$match": filter_dict}]).explain()
        else:
            explain_result = {}

        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        analysis = {
            "execution_time_ms": execution_time,
            "is_slow_query": execution_time > self.slow_query_threshold,
            "filter": filter_dict,
            "operation": operation,
            "explain_result": explain_result,
            "optimization_suggestions": []
        }

        # Analyze execution stats
        if explain_result:
            execution_stats = explain_result.get("executionStats", {})

            analysis.update({
                "documents_examined": execution_stats.get("totalDocsExamined", 0),
                "documents_returned": execution_stats.get("totalDocsReturned", 0),
                "index_used": execution_stats.get("winningPlan", {}).get("stage") == "IXSCAN"
            })

            # Generate optimization suggestions
            analysis["optimization_suggestions"] = self._generate_optimization_suggestions(
                filter_dict, execution_stats
            )

        # Log slow queries
        if analysis["is_slow_query"]:
            self.logger.warning(
                f"Slow query detected: {execution_time:.2f}ms - {filter_dict}"
            )

        return analysis

    def _generate_optimization_suggestions(self,
                                         filter_dict: Dict[str, Any],
                                         execution_stats: Dict[str, Any]) -> List[str]:
        """Generate optimization suggestions based on query analysis"""
        suggestions = []

        # Check if index was used
        winning_plan = execution_stats.get("winningPlan", {})
        if winning_plan.get("stage") != "IXSCAN":
            suggestions.append("Consider adding an index for the filter fields")

        # Check documents examined vs returned ratio
        docs_examined = execution_stats.get("totalDocsExamined", 0)
        docs_returned = execution_stats.get("totalDocsReturned", 0)

        if docs_examined > 0 and docs_returned > 0:
            efficiency_ratio = docs_returned / docs_examined
            if efficiency_ratio < 0.1:  # Less than 10% efficiency
                suggestions.append("Query is examining too many documents. Consider more selective filters or compound indexes")

        # Check for complex filter patterns
        for field, value in filter_dict.items():
            if isinstance(value, dict):
                if "$regex" in value:
                    suggestions.append(f"Regex query on '{field}' may be slow. Consider full-text search or prefix matching")
                elif "$in" in value and len(value["$in"]) > 100:
                    suggestions.append(f"Large $in array on '{field}' may be slow. Consider alternative query structure")

        return suggestions

# Usage example
async def optimized_query_execution(collection: AsyncIOMotorCollection,
                                  filter_dict: Dict[str, Any],
                                  enable_analysis: bool = True):
    """Execute query with optional performance analysis"""

    if enable_analysis:
        analyzer = QueryPerformanceAnalyzer()
        analysis = await analyzer.analyze_query_performance(collection, filter_dict)

        # Log analysis results
        logger = logging.getLogger(__name__)
        logger.info(f"Query analysis: {analysis}")

    # Execute the actual query
    cursor = collection.find(filter_dict)
    return await cursor.to_list(length=None)
```

### 4. Data Validation and Constraints

#### Document Validation Schema
```python
# infrastructure/database/validation.py
from typing import Dict, Any
from pymongo.errors import WriteError
import logging

class DocumentValidator:

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def get_project_validation_schema() -> Dict[str, Any]:
        """MongoDB validation schema for projects collection"""
        return {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["name", "description", "project_type", "status", "start_date", "expected_completion", "budget", "owner_id"],
                "properties": {
                    "name": {
                        "bsonType": "string",
                        "minLength": 1,
                        "maxLength": 200,
                        "description": "Project name must be a string between 1-200 characters"
                    },
                    "description": {
                        "bsonType": "string",
                        "maxLength": 2000,
                        "description": "Project description must be a string with max 2000 characters"
                    },
                    "project_type": {
                        "enum": ["residential", "commercial", "industrial", "infrastructure", "renovation"],
                        "description": "Project type must be one of the specified values"
                    },
                    "status": {
                        "enum": ["planning", "in_progress", "under_review", "completed", "on_hold", "cancelled"],
                        "description": "Status must be one of the specified values"
                    },
                    "start_date": {
                        "bsonType": "date",
                        "description": "Start date must be a valid date"
                    },
                    "expected_completion": {
                        "bsonType": "date",
                        "description": "Expected completion must be a valid date"
                    },
                    "budget": {
                        "bsonType": "object",
                        "required": ["total_budget", "allocated_budget", "spent_amount", "remaining_budget"],
                        "properties": {
                            "total_budget": {
                                "bsonType": "number",
                                "minimum": 0,
                                "description": "Total budget must be a positive number"
                            },
                            "allocated_budget": {
                                "bsonType": "number",
                                "minimum": 0,
                                "description": "Allocated budget must be a positive number"
                            },
                            "spent_amount": {
                                "bsonType": "number",
                                "minimum": 0,
                                "description": "Spent amount must be a positive number"
                            },
                            "remaining_budget": {
                                "bsonType": "number",
                                "description": "Remaining budget must be a number"
                            }
                        }
                    },
                    "owner_id": {
                        "bsonType": "string",
                        "minLength": 1,
                        "description": "Owner ID must be a non-empty string"
                    },
                    "progress_percentage": {
                        "bsonType": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Progress percentage must be between 0 and 100"
                    },
                    "team_members": {
                        "bsonType": "array",
                        "items": {
                            "bsonType": "string"
                        },
                        "description": "Team members must be an array of strings"
                    },
                    "tags": {
                        "bsonType": "array",
                        "items": {
                            "bsonType": "string"
                        },
                        "maxItems": 20,
                        "description": "Tags must be an array of strings with max 20 items"
                    }
                }
            }
        }

    async def setup_collection_validation(self, database, collection_name: str, validation_schema: Dict[str, Any]):
        """Setup validation rules for a collection"""
        try:
            await database.create_collection(
                collection_name,
                validator=validation_schema,
                validationLevel="strict",
                validationAction="error"
            )
            self.logger.info(f"Validation schema applied to {collection_name}")

        except Exception as e:
            # Collection might already exist, try to modify validation
            try:
                await database.command({
                    "collMod": collection_name,
                    "validator": validation_schema,
                    "validationLevel": "strict",
                    "validationAction": "error"
                })
                self.logger.info(f"Validation schema updated for {collection_name}")

            except Exception as modify_error:
                self.logger.error(f"Failed to set validation for {collection_name}: {modify_error}")
```

### 5. Database Migration System

#### Migration Framework
```python
# infrastructure/database/migrations/migration_manager.py
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime
import logging

class BaseMigration(ABC):
    """Base class for database migrations"""

    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.timestamp = datetime.utcnow()

    @abstractmethod
    async def up(self, database) -> bool:
        """Apply the migration"""
        pass

    @abstractmethod
    async def down(self, database) -> bool:
        """Rollback the migration"""
        pass

class MigrationManager:
    """Manages database migrations"""

    def __init__(self, database):
        self.database = database
        self.migrations_collection = database.migrations
        self.logger = logging.getLogger(__name__)
        self.migrations: List[BaseMigration] = []

    def register_migration(self, migration: BaseMigration):
        """Register a migration"""
        self.migrations.append(migration)
        self.migrations.sort(key=lambda m: m.version)

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        cursor = self.migrations_collection.find({}, {"version": 1})
        documents = await cursor.to_list(length=None)
        return [doc["version"] for doc in documents]

    async def apply_migrations(self) -> bool:
        """Apply all pending migrations"""
        applied_versions = await self.get_applied_migrations()

        for migration in self.migrations:
            if migration.version not in applied_versions:
                self.logger.info(f"Applying migration {migration.version}: {migration.description}")

                try:
                    success = await migration.up(self.database)

                    if success:
                        # Record migration as applied
                        await self.migrations_collection.insert_one({
                            "version": migration.version,
                            "description": migration.description,
                            "applied_at": datetime.utcnow()
                        })
                        self.logger.info(f"Migration {migration.version} applied successfully")
                    else:
                        self.logger.error(f"Migration {migration.version} failed")
                        return False

                except Exception as e:
                    self.logger.error(f"Error applying migration {migration.version}: {str(e)}")
                    return False

        return True

    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration"""
        migration = next((m for m in self.migrations if m.version == version), None)

        if not migration:
            self.logger.error(f"Migration {version} not found")
            return False

        try:
            success = await migration.down(self.database)

            if success:
                # Remove migration record
                await self.migrations_collection.delete_one({"version": version})
                self.logger.info(f"Migration {version} rolled back successfully")
                return True
            else:
                self.logger.error(f"Rollback of migration {version} failed")
                return False

        except Exception as e:
            self.logger.error(f"Error rolling back migration {version}: {str(e)}")
            return False

# Example migration
class CreateProjectIndexesMigration(BaseMigration):
    """Migration to create initial indexes for projects collection"""

    def __init__(self):
        super().__init__("001", "Create initial indexes for projects collection")

    async def up(self, database) -> bool:
        """Create indexes"""
        try:
            projects_collection = database.projects

            # Create indexes
            await projects_collection.create_index([("owner_id", 1)])
            await projects_collection.create_index([("status", 1), ("created_at", -1)])
            await projects_collection.create_index([("name", "text"), ("description", "text")])
            await projects_collection.create_index([("start_date", 1), ("expected_completion", 1)])

            return True

        except Exception as e:
            logging.error(f"Failed to create indexes: {str(e)}")
            return False

    async def down(self, database) -> bool:
        """Drop indexes"""
        try:
            projects_collection = database.projects

            # Drop created indexes (except _id which is automatic)
            await projects_collection.drop_index([("owner_id", 1)])
            await projects_collection.drop_index([("status", 1), ("created_at", -1)])
            await projects_collection.drop_index([("name", "text"), ("description", "text")])
            await projects_collection.drop_index([("start_date", 1), ("expected_completion", 1)])

            return True

        except Exception as e:
            logging.error(f"Failed to drop indexes: {str(e)}")
            return False
```

### 6. Performance Monitoring

#### Database Performance Monitor
```python
# infrastructure/database/monitoring.py
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

class DatabasePerformanceMonitor:
    """Monitor database performance and health"""

    def __init__(self, database):
        self.database = database
        self.logger = logging.getLogger(__name__)
        self.metrics = {}

    async def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive performance metrics"""
        try:
            # Server status
            server_status = await self.database.command("serverStatus")

            # Database stats
            db_stats = await self.database.command("dbStats")

            # Collection stats for key collections
            collections_stats = {}
            for collection_name in ["projects", "analyses", "files", "chat_sessions"]:
                try:
                    stats = await self.database.command("collStats", collection_name)
                    collections_stats[collection_name] = {
                        "count": stats.get("count", 0),
                        "size": stats.get("size", 0),
                        "avgObjSize": stats.get("avgObjSize", 0),
                        "storageSize": stats.get("storageSize", 0),
                        "totalIndexSize": stats.get("totalIndexSize", 0)
                    }
                except Exception:
                    collections_stats[collection_name] = {"error": "Collection not found"}

            # Current operations
            current_ops = await self.database.command("currentOp")

            metrics = {
                "timestamp": datetime.utcnow(),
                "server": {
                    "uptime": server_status.get("uptime", 0),
                    "connections": server_status.get("connections", {}),
                    "opcounters": server_status.get("opcounters", {}),
                    "memory": server_status.get("mem", {})
                },
                "database": {
                    "collections": db_stats.get("collections", 0),
                    "objects": db_stats.get("objects", 0),
                    "dataSize": db_stats.get("dataSize", 0),
                    "storageSize": db_stats.get("storageSize", 0),
                    "indexSize": db_stats.get("indexSize", 0)
                },
                "collections": collections_stats,
                "operations": {
                    "active": len(current_ops.get("inprog", [])),
                    "slow_queries": [
                        op for op in current_ops.get("inprog", [])
                        if op.get("microsecs_running", 0) > 1000000  # > 1 second
                    ]
                }
            }

            self.metrics = metrics
            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting performance metrics: {str(e)}")
            return {}

    async def analyze_slow_queries(self, duration_hours: int = 24) -> List[Dict[str, Any]]:
        """Analyze slow queries from the profiler"""
        try:
            # Enable profiling for slow operations (>100ms)
            await self.database.command("profile", 2, slowms=100)

            # Query the profiler collection
            start_time = datetime.utcnow() - timedelta(hours=duration_hours)

            profiler_cursor = self.database.system.profile.find({
                "ts": {"$gte": start_time}
            }).sort("ts", -1).limit(100)

            slow_queries = await profiler_cursor.to_list(length=100)

            # Analyze and categorize slow queries
            analysis = []
            for query in slow_queries:
                analysis.append({
                    "timestamp": query.get("ts"),
                    "duration_ms": query.get("millis", 0),
                    "operation": query.get("op"),
                    "namespace": query.get("ns"),
                    "command": query.get("command", {}),
                    "docs_examined": query.get("docsExamined", 0),
                    "docs_returned": query.get("docsReturned", 0)
                })

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing slow queries: {str(e)}")
            return []

    async def get_index_usage_stats(self) -> Dict[str, Any]:
        """Get index usage statistics"""
        try:
            index_stats = {}

            for collection_name in ["projects", "analyses", "files", "chat_sessions"]:
                try:
                    collection = self.database[collection_name]
                    stats = await collection.aggregate([
                        {"$indexStats": {}}
                    ]).to_list(length=None)

                    index_stats[collection_name] = stats

                except Exception:
                    index_stats[collection_name] = []

            return index_stats

        except Exception as e:
            self.logger.error(f"Error getting index usage stats: {str(e)}")
            return {}

    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive database health check"""
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow()
        }

        try:
            # Check database connectivity
            await self.database.command("ping")
            health_status["checks"]["connectivity"] = {"status": "ok"}

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["connectivity"] = {"status": "error", "error": str(e)}

        try:
            # Check disk space
            stats = await self.database.command("dbStats")
            disk_usage = stats.get("dataSize", 0) / stats.get("storageSize", 1)

            if disk_usage > 0.9:  # > 90% usage
                health_status["checks"]["disk_space"] = {"status": "warning", "usage": disk_usage}
            else:
                health_status["checks"]["disk_space"] = {"status": "ok", "usage": disk_usage}

        except Exception as e:
            health_status["checks"]["disk_space"] = {"status": "error", "error": str(e)}

        try:
            # Check active connections
            server_status = await self.database.command("serverStatus")
            connections = server_status.get("connections", {})
            current_connections = connections.get("current", 0)
            available_connections = connections.get("available", 0)

            if current_connections > available_connections * 0.8:  # > 80% of available
                health_status["checks"]["connections"] = {
                    "status": "warning",
                    "current": current_connections,
                    "available": available_connections
                }
            else:
                health_status["checks"]["connections"] = {
                    "status": "ok",
                    "current": current_connections,
                    "available": available_connections
                }

        except Exception as e:
            health_status["checks"]["connections"] = {"status": "error", "error": str(e)}

        return health_status

# Usage example
async def setup_monitoring():
    """Setup database monitoring"""
    from infrastructure.database.mongodb import get_database

    database = get_database()
    monitor = DatabasePerformanceMonitor(database)

    # Collect metrics every 5 minutes
    while True:
        metrics = await monitor.collect_performance_metrics()

        # Log metrics or send to monitoring system
        logger = logging.getLogger(__name__)
        logger.info(f"Database metrics: {metrics}")

        await asyncio.sleep(300)  # 5 minutes
```

This Database Development Agent provides comprehensive guidance for building a robust, scalable MongoDB database system for the Construction Analysis AI System with focus on performance, reliability, and maintainability.