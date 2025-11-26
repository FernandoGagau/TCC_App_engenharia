# Backend Development Agent

## Overview

The Backend Development Agent specializes in Python FastAPI development for the Construction Analysis AI System. This agent provides guidance on API design, business logic implementation, database integration, and backend architecture following Domain-Driven Design principles.

## Capabilities

### ⚙️ API Development
- FastAPI framework with async/await patterns
- RESTful API design and implementation
- WebSocket for real-time communication
- API documentation with OpenAPI/Swagger
- Request/response validation with Pydantic

### 🏗️ Architecture Patterns
- Domain-Driven Design (DDD) implementation
- Repository and Service patterns
- Dependency injection and IoC containers
- CQRS (Command Query Responsibility Segregation)
- Event sourcing for audit trails

### 🗄️ Database Integration
- MongoDB async operations with Motor
- Data modeling and schema design
- Query optimization and indexing
- Connection pooling and management
- Migration strategies

## Core Responsibilities

### 1. Domain Layer Implementation

#### Core Entities
```python
# domain/entities/project.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"

class ProjectType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INFRASTRUCTURE = "infrastructure"

@dataclass
class Project:
    id: UUID
    name: str
    description: str
    project_type: ProjectType
    status: ProjectStatus
    start_date: datetime
    expected_completion: datetime
    actual_completion: Optional[datetime]
    budget: float
    current_cost: float
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, name: str, description: str, project_type: ProjectType,
               start_date: datetime, expected_completion: datetime,
               budget: float, owner_id: UUID) -> "Project":
        now = datetime.utcnow()
        return cls(
            id=uuid4(),
            name=name,
            description=description,
            project_type=project_type,
            status=ProjectStatus.PLANNING,
            start_date=start_date,
            expected_completion=expected_completion,
            actual_completion=None,
            budget=budget,
            current_cost=0.0,
            owner_id=owner_id,
            created_at=now,
            updated_at=now
        )

    def update_status(self, new_status: ProjectStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.utcnow()
        if new_status == ProjectStatus.COMPLETED:
            self.actual_completion = datetime.utcnow()

    def add_cost(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Cost amount cannot be negative")
        self.current_cost += amount
        self.updated_at = datetime.utcnow()

    def get_budget_utilization(self) -> float:
        return (self.current_cost / self.budget) * 100 if self.budget > 0 else 0
```

#### Value Objects
```python
# domain/value_objects/analysis_result.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class AnalysisType(str, Enum):
    PROGRESS_TRACKING = "progress_tracking"
    QUALITY_INSPECTION = "quality_inspection"
    SAFETY_ASSESSMENT = "safety_assessment"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    MATERIAL_VERIFICATION = "material_verification"

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass(frozen=True)
class Finding:
    id: str
    description: str
    severity: Severity
    location: Optional[str] = None
    recommendations: List[str] = None
    image_references: List[str] = None

    def __post_init__(self):
        if self.recommendations is None:
            object.__setattr__(self, 'recommendations', [])
        if self.image_references is None:
            object.__setattr__(self, 'image_references', [])

@dataclass(frozen=True)
class AnalysisResult:
    analysis_type: AnalysisType
    overall_score: float  # 0-100
    findings: List[Finding]
    summary: str
    metadata: Dict[str, any] = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

        if not 0 <= self.overall_score <= 100:
            raise ValueError("Overall score must be between 0 and 100")

    def get_critical_findings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    def get_findings_by_severity(self, severity: Severity) -> List[Finding]:
        return [f for f in self.findings if f.severity == severity]
```

### 2. Repository Pattern Implementation

#### Base Repository
```python
# infrastructure/repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from uuid import UUID

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):

    @abstractmethod
    async def create(self, entity: T) -> T:
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        pass

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        pass
```

#### MongoDB Project Repository
```python
# infrastructure/repositories/mongodb/project_repository.py
from typing import Optional, List
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from domain.entities.project import Project, ProjectStatus, ProjectType
from infrastructure.repositories.base import BaseRepository
from infrastructure.database.mongodb import get_database

class MongoProjectRepository(BaseRepository[Project]):

    def __init__(self):
        self.db = get_database()
        self.collection: AsyncIOMotorCollection = self.db.projects

    async def create(self, project: Project) -> Project:
        document = self._entity_to_document(project)
        await self.collection.insert_one(document)
        return project

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        document = await self.collection.find_one({"_id": str(project_id)})
        return self._document_to_entity(document) if document else None

    async def update(self, project: Project) -> Project:
        document = self._entity_to_document(project)
        await self.collection.replace_one(
            {"_id": str(project.id)},
            document
        )
        return project

    async def delete(self, project_id: UUID) -> bool:
        result = await self.collection.delete_one({"_id": str(project_id)})
        return result.deleted_count > 0

    async def list(self, limit: int = 100, offset: int = 0) -> List[Project]:
        cursor = self.collection.find().skip(offset).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._document_to_entity(doc) for doc in documents]

    async def find_by_owner(self, owner_id: UUID) -> List[Project]:
        cursor = self.collection.find({"owner_id": str(owner_id)})
        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def find_by_status(self, status: ProjectStatus) -> List[Project]:
        cursor = self.collection.find({"status": status.value})
        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def search_by_name(self, query: str, limit: int = 50) -> List[Project]:
        cursor = self.collection.find(
            {"name": {"$regex": query, "$options": "i"}}
        ).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._document_to_entity(doc) for doc in documents]

    def _entity_to_document(self, project: Project) -> dict:
        return {
            "_id": str(project.id),
            "name": project.name,
            "description": project.description,
            "project_type": project.project_type.value,
            "status": project.status.value,
            "start_date": project.start_date,
            "expected_completion": project.expected_completion,
            "actual_completion": project.actual_completion,
            "budget": project.budget,
            "current_cost": project.current_cost,
            "owner_id": str(project.owner_id),
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }

    def _document_to_entity(self, document: dict) -> Project:
        return Project(
            id=UUID(document["_id"]),
            name=document["name"],
            description=document["description"],
            project_type=ProjectType(document["project_type"]),
            status=ProjectStatus(document["status"]),
            start_date=document["start_date"],
            expected_completion=document["expected_completion"],
            actual_completion=document.get("actual_completion"),
            budget=document["budget"],
            current_cost=document["current_cost"],
            owner_id=UUID(document["owner_id"]),
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )

    async def create_indexes(self):
        await self.collection.create_index([("owner_id", ASCENDING)])
        await self.collection.create_index([("status", ASCENDING)])
        await self.collection.create_index([("name", "text")])
        await self.collection.create_index([("created_at", DESCENDING)])
```

### 3. Service Layer Implementation

#### Project Service
```python
# application/services/project_service.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from domain.entities.project import Project, ProjectStatus, ProjectType
from infrastructure.repositories.mongodb.project_repository import MongoProjectRepository
from application.exceptions import EntityNotFoundError, ValidationError

class ProjectService:

    def __init__(self, project_repository: MongoProjectRepository):
        self.project_repository = project_repository

    async def create_project(
        self,
        name: str,
        description: str,
        project_type: ProjectType,
        start_date: datetime,
        expected_completion: datetime,
        budget: float,
        owner_id: UUID
    ) -> Project:
        # Validation
        if not name.strip():
            raise ValidationError("Project name cannot be empty")

        if budget <= 0:
            raise ValidationError("Budget must be positive")

        if start_date >= expected_completion:
            raise ValidationError("Start date must be before expected completion")

        # Create project
        project = Project.create(
            name=name.strip(),
            description=description.strip(),
            project_type=project_type,
            start_date=start_date,
            expected_completion=expected_completion,
            budget=budget,
            owner_id=owner_id
        )

        return await self.project_repository.create(project)

    async def get_project(self, project_id: UUID) -> Project:
        project = await self.project_repository.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError(f"Project with ID {project_id} not found")
        return project

    async def update_project_status(
        self,
        project_id: UUID,
        new_status: ProjectStatus
    ) -> Project:
        project = await self.get_project(project_id)
        project.update_status(new_status)
        return await self.project_repository.update(project)

    async def add_project_cost(
        self,
        project_id: UUID,
        amount: float,
        description: str
    ) -> Project:
        if amount <= 0:
            raise ValidationError("Cost amount must be positive")

        project = await self.get_project(project_id)
        project.add_cost(amount)

        # Here you might also want to log the cost addition
        # await self.cost_log_service.log_cost_addition(project_id, amount, description)

        return await self.project_repository.update(project)

    async def get_user_projects(self, user_id: UUID) -> List[Project]:
        return await self.project_repository.find_by_owner(user_id)

    async def get_projects_by_status(self, status: ProjectStatus) -> List[Project]:
        return await self.project_repository.find_by_status(status)

    async def search_projects(self, query: str, limit: int = 50) -> List[Project]:
        return await self.project_repository.search_by_name(query, limit)

    async def get_project_statistics(self, project_id: UUID) -> dict:
        project = await self.get_project(project_id)

        return {
            "budget_utilization": project.get_budget_utilization(),
            "days_elapsed": (datetime.utcnow() - project.start_date).days,
            "is_overdue": datetime.utcnow() > project.expected_completion and project.status != ProjectStatus.COMPLETED,
            "remaining_budget": project.budget - project.current_cost,
            "status": project.status.value
        }
```

### 4. FastAPI Application Structure

#### Main Application
```python
# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from api.routes import projects, analyses, files, chat
from infrastructure.database.mongodb import connect_to_mongo, close_mongo_connection
from middleware.error_handler import ErrorHandlerMiddleware
from middleware.logging import LoggingMiddleware
from core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title="Construction Analysis API",
    description="AI-powered construction project analysis system",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

# Routes
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(analyses.router, prefix="/api/v1/analyses", tags=["analyses"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

#### API Routes
```python
# api/routes/projects.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from application.services.project_service import ProjectService
from domain.entities.project import ProjectStatus, ProjectType
from api.dependencies import get_project_service, get_current_user
from api.schemas.project_schemas import (
    ProjectCreate, ProjectResponse, ProjectUpdate, ProjectStatistics
)

router = APIRouter()

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
    current_user = Depends(get_current_user)
):
    try:
        project = await project_service.create_project(
            name=project_data.name,
            description=project_data.description,
            project_type=project_data.project_type,
            start_date=project_data.start_date,
            expected_completion=project_data.expected_completion,
            budget=project_data.budget,
            owner_id=current_user.id
        )
        return ProjectResponse.from_entity(project)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    project_service: ProjectService = Depends(get_project_service),
    current_user = Depends(get_current_user)
):
    try:
        project = await project_service.get_project(project_id)
        return ProjectResponse.from_entity(project)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[ProjectStatus] = None,
    project_service: ProjectService = Depends(get_project_service),
    current_user = Depends(get_current_user)
):
    if status:
        projects = await project_service.get_projects_by_status(status)
    else:
        projects = await project_service.get_user_projects(current_user.id)

    return [ProjectResponse.from_entity(project) for project in projects]

@router.patch("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: UUID,
    status_update: ProjectStatusUpdate,
    project_service: ProjectService = Depends(get_project_service),
    current_user = Depends(get_current_user)
):
    try:
        project = await project_service.update_project_status(
            project_id, status_update.status
        )
        return ProjectResponse.from_entity(project)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.get("/{project_id}/statistics", response_model=ProjectStatistics)
async def get_project_statistics(
    project_id: UUID,
    project_service: ProjectService = Depends(get_project_service),
    current_user = Depends(get_current_user)
):
    try:
        stats = await project_service.get_project_statistics(project_id)
        return ProjectStatistics(**stats)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
```

### 5. WebSocket Implementation

#### Chat WebSocket Handler
```python
# api/websocket/chat.py
from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json
import asyncio

from application.services.chat_service import ChatService
from application.services.ai_agent_service import AIAgentService

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_session(self, message: str, session_id: str):
        if session_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.add(connection)

            # Remove disconnected connections
            for connection in disconnected:
                self.active_connections[session_id].discard(connection)

manager = ConnectionManager()

class ChatWebSocketHandler:
    def __init__(
        self,
        chat_service: ChatService,
        ai_agent_service: AIAgentService
    ):
        self.chat_service = chat_service
        self.ai_agent_service = ai_agent_service

    async def handle_connection(self, websocket: WebSocket, session_id: str):
        await manager.connect(websocket, session_id)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Process different message types
                if message_data.get("type") == "message":
                    await self._handle_chat_message(websocket, session_id, message_data)
                elif message_data.get("type") == "typing":
                    await self._handle_typing_indicator(session_id, message_data)
                elif message_data.get("type") == "analysis_request":
                    await self._handle_analysis_request(websocket, session_id, message_data)

        except WebSocketDisconnect:
            manager.disconnect(websocket, session_id)

    async def _handle_chat_message(self, websocket: WebSocket, session_id: str, message_data: dict):
        user_message = message_data.get("content", "")

        # Save user message
        await self.chat_service.save_message(
            session_id=session_id,
            content=user_message,
            sender="user"
        )

        # Send typing indicator
        typing_message = {
            "type": "typing",
            "isTyping": True
        }
        await manager.broadcast_to_session(json.dumps(typing_message), session_id)

        # Process with AI agent
        try:
            ai_response = await self.ai_agent_service.process_message(
                session_id=session_id,
                message=user_message
            )

            # Save AI response
            await self.chat_service.save_message(
                session_id=session_id,
                content=ai_response.content,
                sender="agent",
                metadata=ai_response.metadata
            )

            # Send AI response
            response_message = {
                "type": "message",
                "id": ai_response.id,
                "content": ai_response.content,
                "sender": "agent",
                "timestamp": ai_response.timestamp.isoformat(),
                "messageType": ai_response.message_type,
                "metadata": ai_response.metadata
            }

            await manager.broadcast_to_session(json.dumps(response_message), session_id)

        except Exception as e:
            error_message = {
                "type": "error",
                "content": f"Sorry, I encountered an error: {str(e)}"
            }
            await manager.send_personal_message(json.dumps(error_message), websocket)

        finally:
            # Stop typing indicator
            typing_message = {
                "type": "typing",
                "isTyping": False
            }
            await manager.broadcast_to_session(json.dumps(typing_message), session_id)

    async def _handle_analysis_request(self, websocket: WebSocket, session_id: str, message_data: dict):
        analysis_type = message_data.get("analysisType")
        project_id = message_data.get("projectId")
        file_ids = message_data.get("fileIds", [])

        # Start analysis process
        try:
            analysis_result = await self.ai_agent_service.start_analysis(
                project_id=project_id,
                analysis_type=analysis_type,
                file_ids=file_ids,
                session_id=session_id
            )

            # Send analysis result
            result_message = {
                "type": "analysis_result",
                "analysisId": analysis_result.id,
                "result": analysis_result.to_dict()
            }

            await manager.send_personal_message(json.dumps(result_message), websocket)

        except Exception as e:
            error_message = {
                "type": "error",
                "content": f"Analysis failed: {str(e)}"
            }
            await manager.send_personal_message(json.dumps(error_message), websocket)

    async def _handle_typing_indicator(self, session_id: str, message_data: dict):
        # Broadcast typing indicator to other clients in the session
        await manager.broadcast_to_session(json.dumps(message_data), session_id)
```

### 6. Dependency Injection

```python
# api/dependencies.py
from fastapi import Depends
from functools import lru_cache

from application.services.project_service import ProjectService
from application.services.chat_service import ChatService
from application.services.ai_agent_service import AIAgentService
from infrastructure.repositories.mongodb.project_repository import MongoProjectRepository

@lru_cache()
def get_project_repository() -> MongoProjectRepository:
    return MongoProjectRepository()

def get_project_service(
    repository: MongoProjectRepository = Depends(get_project_repository)
) -> ProjectService:
    return ProjectService(repository)

def get_chat_service() -> ChatService:
    return ChatService()

def get_ai_agent_service() -> AIAgentService:
    return AIAgentService()

# Authentication dependency (placeholder)
async def get_current_user():
    # This would implement JWT token validation
    # For now, return a mock user
    from dataclasses import dataclass
    from uuid import uuid4

    @dataclass
    class User:
        id: UUID
        email: str
        name: str

    return User(id=uuid4(), email="user@example.com", name="Test User")
```

## Performance Optimization

### Connection Pooling
```python
# infrastructure/database/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import asyncio

class DatabaseManager:
    client: AsyncIOMotorClient = None
    database = None

db_manager = DatabaseManager()

async def connect_to_mongo():
    db_manager.client = AsyncIOMotorClient(
        "mongodb://localhost:27017",
        maxPoolSize=50,
        minPoolSize=10,
        maxIdleTimeMS=30000,
        server_api=ServerApi('1')
    )
    db_manager.database = db_manager.client.construction_analysis

async def close_mongo_connection():
    if db_manager.client:
        db_manager.client.close()

def get_database():
    return db_manager.database
```

### Caching with Redis
```python
# infrastructure/cache/redis_cache.py
import redis.asyncio as redis
import json
from typing import Optional, Any
from datetime import timedelta

class RedisCache:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, expire: timedelta = timedelta(hours=1)):
        try:
            await self.redis.setex(
                key,
                int(expire.total_seconds()),
                json.dumps(value, default=str)
            )
        except Exception:
            pass

    async def delete(self, key: str):
        try:
            await self.redis.delete(key)
        except Exception:
            pass

# Usage with decorator
from functools import wraps

def cache_result(expire: timedelta = timedelta(hours=1)):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = RedisCache()
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, expire)
            return result
        return wrapper
    return decorator
```

This Backend Development Agent provides comprehensive guidance for building a robust, scalable Python FastAPI backend for the Construction Analysis AI System.