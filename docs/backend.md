# Backend Development Guide

This guide covers the Python FastAPI backend development for the Construction Analysis AI System.

## Backend Overview

### Technology Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI with async/await support
- **Architecture**: Domain-Driven Design (DDD) with Clean Architecture
- **AI Framework**: LangGraph 0.6.7 + LangChain 0.3.27
- **Database**: MongoDB with Motor (async driver)
- **Object Storage**: MinIO (S3-compatible)
- **API Integration**: OpenRouter for AI models

### Project Structure
```
backend/
├── src/                    # Source code
│   ├── agents/            # AI agents (LangGraph)
│   │   ├── interfaces/    # Agent contracts
│   │   ├── supervisor.py  # Main orchestrator
│   │   ├── visual_agent.py
│   │   ├── document_agent.py
│   │   ├── progress_agent.py
│   │   └── report_agent.py
│   ├── application/       # Application layer
│   │   └── services/      # Business services
│   ├── domain/           # Domain layer
│   │   ├── entities/     # Core entities
│   │   ├── events/       # Domain events
│   │   ├── exceptions/   # Domain exceptions
│   │   └── value_objects/
│   ├── infrastructure/   # Infrastructure layer
│   │   ├── agents/      # Agent factory
│   │   ├── config/      # Configuration
│   │   ├── database/    # Database adapters
│   │   └── storage/     # File storage
│   ├── presentation/    # Presentation layer
│   │   └── api/        # API endpoints
│   └── main.py         # Application entry point
├── tests/              # Test suite
├── requirements.txt    # Dependencies
└── .env               # Environment variables
```

## Domain-Driven Design Structure

### Domain Layer

#### Core Entities
```python
# src/domain/entities/project.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class ProjectStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

@dataclass
class Project:
    """Core project entity."""
    id: str
    name: str
    description: Optional[str]
    location: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    def complete(self):
        """Mark project as completed."""
        self.status = ProjectStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if project is active."""
        return self.status == ProjectStatus.ACTIVE
```

#### Value Objects
```python
# src/domain/value_objects/analysis_result.py
from dataclasses import dataclass
from typing import List, Dict, Any
from decimal import Decimal

@dataclass(frozen=True)
class AnalysisResult:
    """Immutable analysis result value object."""
    progress_percentage: Decimal
    detected_elements: List[str]
    safety_issues: List[str]
    confidence_score: Decimal
    metadata: Dict[str, Any]

    def __post_init__(self):
        if not 0 <= self.progress_percentage <= 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        if not 0 <= self.confidence_score <= 1:
            raise ValueError("Confidence score must be between 0 and 1")

@dataclass(frozen=True)
class Location:
    """Geographic location value object."""
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def __post_init__(self):
        if self.latitude and not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")

        if self.longitude and not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")
```

#### Domain Events
```python
# src/domain/events/project_events.py
from dataclasses import dataclass
from datetime import datetime
from abc import ABC

@dataclass
class DomainEvent(ABC):
    """Base domain event."""
    occurred_at: datetime

@dataclass
class ProjectCreated(DomainEvent):
    """Event raised when a project is created."""
    project_id: str
    project_name: str

@dataclass
class AnalysisCompleted(DomainEvent):
    """Event raised when image analysis is completed."""
    project_id: str
    analysis_id: str
    result: 'AnalysisResult'

@dataclass
class ProgressUpdated(DomainEvent):
    """Event raised when project progress is updated."""
    project_id: str
    previous_progress: float
    current_progress: float
```

#### Domain Exceptions
```python
# src/domain/exceptions.py
class DomainException(Exception):
    """Base domain exception."""
    pass

class ProjectNotFoundError(DomainException):
    """Raised when project is not found."""

    def __init__(self, project_id: str):
        super().__init__(f"Project with ID {project_id} not found")
        self.project_id = project_id

class InvalidAnalysisDataError(DomainException):
    """Raised when analysis data is invalid."""
    pass

class AgentProcessingError(DomainException):
    """Raised when agent processing fails."""

    def __init__(self, agent_name: str, message: str):
        super().__init__(f"Agent {agent_name} failed: {message}")
        self.agent_name = agent_name
```

### Application Layer

#### Services
```python
# src/application/services/project_service.py
from typing import List, Optional
from datetime import datetime

from ..domain.entities.project import Project, ProjectStatus
from ..domain.events.project_events import ProjectCreated, ProgressUpdated
from ..infrastructure.database.repositories.project_repository import ProjectRepository
from ..infrastructure.events.event_publisher import EventPublisher

class ProjectService:
    """Application service for project operations."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        event_publisher: EventPublisher
    ):
        self.project_repository = project_repository
        self.event_publisher = event_publisher

    async def create_project(
        self,
        name: str,
        description: Optional[str],
        location: str
    ) -> Project:
        """Create a new project."""
        project = Project(
            id=None,  # Will be generated by repository
            name=name,
            description=description,
            location=location,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        saved_project = await self.project_repository.save(project)

        # Publish domain event
        event = ProjectCreated(
            occurred_at=datetime.utcnow(),
            project_id=saved_project.id,
            project_name=saved_project.name
        )
        await self.event_publisher.publish(event)

        return saved_project

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return await self.project_repository.find_by_id(project_id)

    async def list_projects(
        self,
        status: Optional[ProjectStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Project]:
        """List projects with optional filtering."""
        return await self.project_repository.find_all(
            status=status,
            limit=limit,
            offset=offset
        )

    async def update_progress(
        self,
        project_id: str,
        new_progress: float
    ) -> Project:
        """Update project progress."""
        project = await self.project_repository.find_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        old_progress = getattr(project, 'progress', 0.0)
        project.progress = new_progress
        project.updated_at = datetime.utcnow()

        updated_project = await self.project_repository.save(project)

        # Publish progress update event
        event = ProgressUpdated(
            occurred_at=datetime.utcnow(),
            project_id=project_id,
            previous_progress=old_progress,
            current_progress=new_progress
        )
        await self.event_publisher.publish(event)

        return updated_project
```

## AI Agents Implementation

### Base Agent Interface
```python
# src/agents/interfaces/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class AgentInput:
    """Standardized input for agents."""
    data: Dict[str, Any]
    project_id: str
    session_id: str

@dataclass
class AgentOutput:
    """Standardized output from agents."""
    result: Dict[str, Any]
    confidence: float
    processing_time: float
    agent_name: str

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of agent capabilities."""
        pass

    @abstractmethod
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process input and return structured output."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if agent is healthy and ready."""
        pass
```

### Visual Analysis Agent
```python
# src/agents/visual_agent.py
import asyncio
import time
from typing import Dict, Any, List
import aiohttp
from PIL import Image
import io

from .interfaces.base_agent import BaseAgent, AgentInput, AgentOutput
from ..infrastructure.config.settings import settings

class VisualAnalysisAgent(BaseAgent):
    """Agent for analyzing construction site images."""

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = "anthropic/claude-3-5-sonnet-20241022"  # Gemini alternative
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    @property
    def name(self) -> str:
        return "visual_analysis"

    @property
    def capabilities(self) -> List[str]:
        return [
            "image_analysis",
            "progress_detection",
            "safety_assessment",
            "element_identification",
            "quality_inspection"
        ]

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Analyze construction images using OpenRouter."""
        start_time = time.time()

        try:
            image_path = input_data.data.get("image_path")
            if not image_path:
                raise ValueError("No image path provided")

            # Process image
            analysis_result = await self._analyze_image(image_path)

            processing_time = time.time() - start_time

            return AgentOutput(
                result=analysis_result,
                confidence=analysis_result.get("confidence", 0.8),
                processing_time=processing_time,
                agent_name=self.name
            )

        except Exception as e:
            raise AgentProcessingError(self.name, str(e))

    async def _analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Send image to OpenRouter for analysis."""

        # Prepare image data
        image_data = await self._prepare_image(image_path)

        # Prepare prompt for construction analysis
        prompt = """
        Analyze this construction site image and provide:
        1. Overall progress percentage (0-100)
        2. Detected construction elements (walls, foundations, etc.)
        3. Safety issues or concerns
        4. Quality observations
        5. Recommendations

        Return response in JSON format.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                        }
                    ]
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"API call failed: {response.status}")

                result = await response.json()
                content = result["choices"][0]["message"]["content"]

                # Parse JSON response
                import json
                try:
                    analysis = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback if not valid JSON
                    analysis = {
                        "progress_percentage": 50,
                        "elements": ["structure"],
                        "safety_issues": [],
                        "quality_observations": content,
                        "confidence": 0.7
                    }

                return analysis

    async def _prepare_image(self, image_path: str) -> str:
        """Prepare image for API submission."""
        import base64

        # Open and resize image if needed
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()

        # Convert to base64
        return base64.b64encode(image_data).decode()

    async def health_check(self) -> bool:
        """Check OpenRouter API connectivity."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Simple test call
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200

        except Exception:
            return False
```

### Supervisor Agent with LangGraph
```python
# src/agents/supervisor.py
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
import asyncio

from .interfaces.base_agent import AgentInput, AgentOutput
from .visual_agent import VisualAnalysisAgent
from .document_agent import DocumentProcessingAgent
from .progress_agent import ProgressTrackingAgent
from .report_agent import ReportGenerationAgent

class SupervisorState(TypedDict):
    """State managed by supervisor."""
    project_id: str
    session_id: str
    messages: List[Dict[str, Any]]
    current_task: str
    agent_results: Dict[str, Any]
    final_response: Optional[str]

class SupervisorAgent:
    """Main supervisor agent that orchestrates other agents."""

    def __init__(self):
        # Initialize specialized agents
        self.visual_agent = VisualAnalysisAgent()
        self.document_agent = DocumentProcessingAgent()
        self.progress_agent = ProgressTrackingAgent()
        self.report_agent = ReportGenerationAgent()

        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        self.memory = MemorySaver()
        self.app = self.workflow.compile(checkpointer=self.memory)

    def _build_workflow(self) -> StateGraph:
        """Build the supervisor workflow graph."""
        workflow = StateGraph(SupervisorState)

        # Add nodes
        workflow.add_node("classify_task", self._classify_task)
        workflow.add_node("visual_analysis", self._visual_analysis_node)
        workflow.add_node("document_processing", self._document_processing_node)
        workflow.add_node("progress_tracking", self._progress_tracking_node)
        workflow.add_node("generate_response", self._generate_response)

        # Set entry point
        workflow.set_entry_point("classify_task")

        # Add conditional edges
        workflow.add_conditional_edges(
            "classify_task",
            self._route_task,
            {
                "visual": "visual_analysis",
                "document": "document_processing",
                "progress": "progress_tracking",
                "general": "generate_response"
            }
        )

        # Connect to response generation
        workflow.add_edge("visual_analysis", "generate_response")
        workflow.add_edge("document_processing", "generate_response")
        workflow.add_edge("progress_tracking", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow

    async def process_message(
        self,
        message: str,
        project_id: str,
        session_id: str,
        files: Optional[List[str]] = None
    ) -> str:
        """Process user message through the supervisor workflow."""

        initial_state = SupervisorState(
            project_id=project_id,
            session_id=session_id,
            messages=[{"role": "user", "content": message}],
            current_task="",
            agent_results={},
            final_response=None
        )

        # Add file information if provided
        if files:
            initial_state["files"] = files

        # Run workflow
        config = {"configurable": {"thread_id": session_id}}
        result = await self.app.ainvoke(initial_state, config)

        return result["final_response"]

    async def _classify_task(self, state: SupervisorState) -> SupervisorState:
        """Classify the user's task to determine routing."""
        message = state["messages"][-1]["content"].lower()

        # Simple classification logic
        if any(word in message for word in ["image", "photo", "picture", "analyze", "visual"]):
            task_type = "visual"
        elif any(word in message for word in ["document", "pdf", "file", "upload"]):
            task_type = "document"
        elif any(word in message for word in ["progress", "status", "timeline", "completion"]):
            task_type = "progress"
        else:
            task_type = "general"

        state["current_task"] = task_type
        return state

    def _route_task(self, state: SupervisorState) -> str:
        """Route to appropriate agent based on task classification."""
        return state["current_task"]

    async def _visual_analysis_node(self, state: SupervisorState) -> SupervisorState:
        """Process visual analysis request."""
        try:
            # Check if files were provided
            files = state.get("files", [])
            if not files:
                state["agent_results"]["visual"] = {
                    "error": "No image file provided for visual analysis"
                }
                return state

            # Process first image file
            image_path = files[0]
            agent_input = AgentInput(
                data={"image_path": image_path},
                project_id=state["project_id"],
                session_id=state["session_id"]
            )

            result = await self.visual_agent.process(agent_input)
            state["agent_results"]["visual"] = result.result

        except Exception as e:
            state["agent_results"]["visual"] = {"error": str(e)}

        return state

    async def _document_processing_node(self, state: SupervisorState) -> SupervisorState:
        """Process document analysis request."""
        try:
            files = state.get("files", [])
            if not files:
                state["agent_results"]["document"] = {
                    "error": "No document file provided"
                }
                return state

            agent_input = AgentInput(
                data={"document_path": files[0]},
                project_id=state["project_id"],
                session_id=state["session_id"]
            )

            result = await self.document_agent.process(agent_input)
            state["agent_results"]["document"] = result.result

        except Exception as e:
            state["agent_results"]["document"] = {"error": str(e)}

        return state

    async def _progress_tracking_node(self, state: SupervisorState) -> SupervisorState:
        """Process progress tracking request."""
        try:
            agent_input = AgentInput(
                data={"request_type": "progress_update"},
                project_id=state["project_id"],
                session_id=state["session_id"]
            )

            result = await self.progress_agent.process(agent_input)
            state["agent_results"]["progress"] = result.result

        except Exception as e:
            state["agent_results"]["progress"] = {"error": str(e)}

        return state

    async def _generate_response(self, state: SupervisorState) -> SupervisorState:
        """Generate final response based on agent results."""
        agent_results = state["agent_results"]
        task_type = state["current_task"]

        if task_type == "visual" and "visual" in agent_results:
            result = agent_results["visual"]
            if "error" in result:
                response = f"I encountered an error analyzing the image: {result['error']}"
            else:
                progress = result.get("progress_percentage", 0)
                elements = result.get("elements", [])
                safety = result.get("safety_issues", [])

                response = f"""
Based on the image analysis:

📊 **Progress**: {progress}% complete

🏗️ **Detected Elements**: {', '.join(elements) if elements else 'None identified'}

⚠️ **Safety Observations**: {', '.join(safety) if safety else 'No issues detected'}

Would you like me to provide more detailed analysis or generate a report?
                """.strip()

        elif task_type == "progress" and "progress" in agent_results:
            result = agent_results["progress"]
            response = f"Current project progress: {result.get('current_progress', 0)}%"

        else:
            response = "I'm ready to help with your construction project analysis. You can upload images for visual analysis, documents for processing, or ask about project progress."

        state["final_response"] = response
        return state
```

## Infrastructure Layer

### Database Repository Pattern
```python
# src/infrastructure/database/repositories/project_repository.py
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ...domain.entities.project import Project, ProjectStatus
from ...domain.exceptions import ProjectNotFoundError

class ProjectRepository:
    """MongoDB repository for projects."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.projects

    async def save(self, project: Project) -> Project:
        """Save project to database."""
        project_dict = self._to_dict(project)

        if project.id:
            # Update existing
            await self.collection.replace_one(
                {"_id": ObjectId(project.id)},
                project_dict
            )
        else:
            # Create new
            result = await self.collection.insert_one(project_dict)
            project.id = str(result.inserted_id)

        return project

    async def find_by_id(self, project_id: str) -> Optional[Project]:
        """Find project by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(project_id)})
            return self._from_dict(doc) if doc else None
        except Exception:
            return None

    async def find_all(
        self,
        status: Optional[ProjectStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Project]:
        """Find projects with optional filtering."""
        query = {}
        if status:
            query["status"] = status.value

        cursor = self.collection.find(query).skip(offset).limit(limit)
        docs = await cursor.to_list(length=limit)

        return [self._from_dict(doc) for doc in docs]

    async def delete(self, project_id: str) -> bool:
        """Delete project by ID."""
        result = await self.collection.delete_one({"_id": ObjectId(project_id)})
        return result.deleted_count > 0

    def _to_dict(self, project: Project) -> dict:
        """Convert project entity to dict."""
        data = {
            "name": project.name,
            "description": project.description,
            "location": project.location,
            "status": project.status.value,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }

        if project.id:
            data["_id"] = ObjectId(project.id)

        return data

    def _from_dict(self, data: dict) -> Project:
        """Convert dict to project entity."""
        return Project(
            id=str(data["_id"]),
            name=data["name"],
            description=data.get("description"),
            location=data["location"],
            status=ProjectStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )
```

### Configuration Management
```python
# src/infrastructure/config/settings.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    mongodb_url: str = "mongodb://localhost:27017/construction_ai"
    database_name: str = "construction_ai"

    # MinIO Object Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "construction-files"
    minio_secure: bool = False

    # OpenRouter API
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Application
    app_name: str = "Construction Analysis AI"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # API Configuration
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## API Layer

### FastAPI Application Setup
```python
# src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import logging

from .infrastructure.config.settings import settings
from .infrastructure.database.connection import get_database
from .presentation.api.v1 import router as api_router

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Add middlewares
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")

        # Initialize database connection
        await get_database()

        # Initialize other services
        # await initialize_agents()

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down application")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}

    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
```

### API Endpoints
```python
# src/presentation/api/v1/projects.py
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from pydantic import BaseModel

from ....application.services.project_service import ProjectService
from ....domain.entities.project import ProjectStatus
from ....domain.exceptions import ProjectNotFoundError
from ....infrastructure.dependencies import get_project_service

router = APIRouter(prefix="/projects", tags=["projects"])

# Request/Response Models
class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    location: str

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    location: str
    status: str
    created_at: str
    updated_at: str

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    limit: int
    offset: int

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    project_service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """Create a new construction project."""
    try:
        project = await project_service.create_project(
            name=request.name,
            description=request.description,
            location=request.location
        )

        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            location=project.location,
            status=project.status.value,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    project_service: ProjectService = Depends(get_project_service)
) -> ProjectListResponse:
    """List construction projects."""
    try:
        status_enum = None
        if status_filter:
            status_enum = ProjectStatus(status_filter)

        projects = await project_service.list_projects(
            status=status_enum,
            limit=limit,
            offset=offset
        )

        project_responses = [
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                location=p.location,
                status=p.status.value,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat()
            ) for p in projects
        ]

        return ProjectListResponse(
            projects=project_responses,
            total=len(project_responses),
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """Get project by ID."""
    try:
        project = await project_service.get_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            location=project.location,
            status=project.status.value,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

This backend guide provides a comprehensive foundation for building the Python FastAPI backend with proper Domain-Driven Design architecture, AI agent integration, and modern async patterns.