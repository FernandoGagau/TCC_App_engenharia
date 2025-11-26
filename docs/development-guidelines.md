# Development Guidelines

This document establishes coding standards, best practices, and development workflows for the Construction Analysis AI System.

## Code Style and Standards

### Python (Backend)
- **Version**: Python 3.12+ required
- **Framework**: FastAPI with async/await patterns
- **Code Style**: PEP 8 with Black formatter
- **Type Hints**: Required for all functions and methods
- **Imports**: Use absolute imports, organize with isort

#### Python Code Examples
```python
# Good: Type hints and async patterns
from typing import Optional, List
from pydantic import BaseModel

async def analyze_image(
    image_path: str,
    project_id: Optional[str] = None
) -> List[dict]:
    """Analyze construction image with proper typing."""
    pass

# Good: Pydantic models for validation
class ProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    location: str
```

### JavaScript/React (Frontend)
- **Version**: React 18 with functional components
- **Style**: ES6+ with arrow functions
- **Components**: Functional components with hooks
- **Styling**: Material UI components with custom CSS

#### React Code Examples
```javascript
// Good: Functional component with hooks
import React, { useState, useEffect } from 'react';
import { TextField, Button, Box } from '@mui/material';

const ProjectForm = ({ onSubmit }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onSubmit(formData);
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      {/* Form content */}
    </Box>
  );
};
```

## Project Structure Standards

### Backend Structure (Domain-Driven Design)
```
backend/src/
├── agents/              # AI agents (LangGraph)
│   ├── interfaces/     # Agent contracts
│   ├── supervisor.py   # Main orchestrator
│   └── [agent].py     # Specialized agents
├── application/        # Application services
│   └── services/      # Business logic services
├── domain/            # Domain models
│   ├── entities/     # Core business entities
│   ├── events/       # Domain events
│   └── exceptions/   # Domain-specific exceptions
├── infrastructure/    # External concerns
│   ├── database/     # MongoDB adapters
│   ├── storage/      # MinIO file storage
│   └── config/       # Configuration
└── presentation/      # API layer
    └── api/          # FastAPI endpoints
```

### Frontend Structure
```
frontend/src/
├── components/        # Reusable UI components
│   ├── common/       # Generic components
│   ├── forms/        # Form components
│   └── layout/       # Layout components
├── services/         # API service functions
├── utils/           # Utility functions
└── App.js           # Main application component
```

## Naming Conventions

### Files and Directories
- **Python files**: `snake_case.py`
- **JavaScript files**: `PascalCase.js` for components, `camelCase.js` for utilities
- **Directories**: `kebab-case` or `snake_case`

### Variables and Functions
```python
# Python
class ProjectAnalyzer:  # PascalCase for classes
    def analyze_progress(self, project_id: str):  # snake_case for methods
        pass

project_data = {}  # snake_case for variables
```

```javascript
// JavaScript
const ProjectCard = () => {};  // PascalCase for components
const analyzeProject = () => {}; // camelCase for functions
const projectData = {};  // camelCase for variables
```

## AI Agent Development

### Agent Pattern
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from langchain.schema import HumanMessage

class BaseAgent(ABC):
    """Base class for all specialized agents."""

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return structured output."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        pass
```

### LangGraph Integration
```python
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

class AgentState(TypedDict):
    messages: List[HumanMessage]
    project_id: str
    analysis_results: Dict[str, Any]

def create_supervisor_graph() -> StateGraph:
    """Create the main supervisor workflow graph."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("visual_analysis", visual_agent_node)
    workflow.add_node("document_processing", document_agent_node)

    # Define edges
    workflow.add_edge("visual_analysis", "document_processing")
    workflow.add_edge("document_processing", END)

    return workflow
```

## API Design Standards

### Endpoint Patterns
- **RESTful URLs**: `/api/v1/resource/{id}`
- **HTTP Methods**: GET (read), POST (create), PUT (update), DELETE (remove)
- **Response Format**: JSON with consistent structure

```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1")

class ProjectResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime

@router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectRequest) -> ProjectResponse:
    """Create a new construction project."""
    try:
        # Implementation
        return ProjectResponse(...)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### WebSocket Patterns
```python
from fastapi import WebSocket

@router.websocket("/chat/{session_id}")
async def chat_endpoint(websocket: WebSocket, session_id: str):
    """Real-time chat with AI agents."""
    await websocket.accept()

    try:
        while True:
            message = await websocket.receive_text()
            # Process with supervisor agent
            response = await supervisor.process_message(message, session_id)
            await websocket.send_text(response)
    except Exception as e:
        await websocket.close(code=1000)
```

## Database Patterns

### MongoDB Schema Design
```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId

class ProjectDocument(BaseModel):
    """MongoDB document for construction projects."""
    id: Optional[str] = Field(alias="_id")
    name: str
    description: Optional[str] = None
    location: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
```

### Data Access Patterns
```python
from motor.motor_asyncio import AsyncIOMotorClient

class ProjectRepository:
    """Repository for project data operations."""

    def __init__(self, database: AsyncIOMotorClient):
        self.collection = database.projects

    async def create(self, project: ProjectDocument) -> str:
        """Create new project and return ID."""
        result = await self.collection.insert_one(project.dict(exclude={"id"}))
        return str(result.inserted_id)

    async def find_by_id(self, project_id: str) -> Optional[ProjectDocument]:
        """Find project by ID."""
        doc = await self.collection.find_one({"_id": ObjectId(project_id)})
        return ProjectDocument(**doc) if doc else None
```

## Testing Standards

### Unit Testing
```python
import pytest
from unittest.mock import Mock, AsyncMock

class TestVisualAgent:
    """Test suite for Visual Analysis Agent."""

    @pytest.fixture
    def visual_agent(self):
        """Create visual agent instance for testing."""
        return VisualAgent(api_client=Mock())

    @pytest.mark.asyncio
    async def test_analyze_image_success(self, visual_agent):
        """Test successful image analysis."""
        # Mock API response
        visual_agent.api_client.analyze.return_value = {
            "elements": ["wall", "window"],
            "progress": 0.75
        }

        result = await visual_agent.analyze_image("test.jpg")

        assert result["progress"] == 0.75
        assert "wall" in result["elements"]
```

### Frontend Testing
```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import ProjectForm from './ProjectForm';

describe('ProjectForm', () => {
  test('submits form with correct data', async () => {
    const mockSubmit = jest.fn();
    render(<ProjectForm onSubmit={mockSubmit} />);

    fireEvent.change(screen.getByLabelText('Project Name'), {
      target: { value: 'Test Project' }
    });

    fireEvent.click(screen.getByText('Submit'));

    expect(mockSubmit).toHaveBeenCalledWith({
      name: 'Test Project'
    });
  });
});
```

## Error Handling

### Backend Error Patterns
```python
from enum import Enum
from fastapi import HTTPException, status

class ErrorCode(Enum):
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    INVALID_IMAGE_FORMAT = "INVALID_IMAGE_FORMAT"
    AGENT_PROCESSING_ERROR = "AGENT_PROCESSING_ERROR"

class ProjectNotFoundError(Exception):
    """Raised when project is not found."""
    pass

async def get_project(project_id: str) -> ProjectDocument:
    """Get project with proper error handling."""
    try:
        project = await project_repository.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": ErrorCode.PROJECT_NOT_FOUND.value,
                    "message": f"Project {project_id} not found"
                }
            )
        return project
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {e}")
        raise
```

### Frontend Error Handling
```javascript
const useApiCall = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const makeRequest = async (apiCall) => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall();
      return result;
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { makeRequest, loading, error };
};
```

## Security Guidelines

### API Security
- **Authentication**: JWT tokens for protected endpoints
- **Input Validation**: Pydantic models for all inputs
- **Rate Limiting**: Per-user request limits
- **CORS**: Configured for frontend domains only

### File Upload Security
```python
from fastapi import UploadFile, HTTPException
import magic

ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file(file: UploadFile):
    """Validate uploaded file type and size."""
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")

    # Check MIME type
    mime_type = magic.from_buffer(content, mime=True)
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Invalid file type")

    # Reset file position
    await file.seek(0)
```

## Performance Guidelines

### Database Optimization
- **Indexes**: Create indexes for frequently queried fields
- **Aggregation**: Use MongoDB aggregation pipeline for complex queries
- **Connection Pooling**: Configure appropriate connection limits

### Caching Strategy
```python
from functools import lru_cache
import asyncio

@lru_cache(maxsize=100)
async def get_cached_analysis(image_hash: str) -> dict:
    """Cache image analysis results."""
    return await perform_expensive_analysis(image_hash)
```

## Environment Configuration

### Environment Variables
```bash
# Backend (.env)
MONGODB_URL=mongodb://localhost:27017/construction_ai
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
OPENROUTER_API_KEY=your_api_key_here
LOG_LEVEL=INFO

# Frontend (.env)
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

### Configuration Management
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings from environment variables."""
    mongodb_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    openrouter_api_key: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

## Git Workflow

### Commit Messages
```
type(scope): description

Examples:
feat(agents): add visual analysis agent
fix(api): handle file upload errors
docs(readme): update setup instructions
refactor(database): optimize query performance
```

### Branch Naming
- **Features**: `feat/feature-name`
- **Fixes**: `fix/bug-description`
- **Documentation**: `docs/update-description`

### Pull Request Process
1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure all tests pass
4. Update documentation if needed
5. Create PR with descriptive title and description
6. Code review and approval
7. Merge to `main`

## Code Review Checklist

### Backend Review
- [ ] Type hints present and correct
- [ ] Async/await used properly
- [ ] Error handling implemented
- [ ] Tests written and passing
- [ ] Database queries optimized
- [ ] Security considerations addressed

### Frontend Review
- [ ] Components are functional with hooks
- [ ] Props validation included
- [ ] Error states handled
- [ ] Loading states implemented
- [ ] Accessibility considerations
- [ ] Responsive design verified

### AI Agent Review
- [ ] Agent follows base pattern
- [ ] LangGraph integration correct
- [ ] Input/output schemas defined
- [ ] Error handling for API calls
- [ ] Logging and monitoring included