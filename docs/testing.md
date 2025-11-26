# Testing Documentation

This document provides comprehensive testing guidelines and strategies for the Construction Analysis AI System, covering both backend (Python/FastAPI) and frontend (React) testing approaches.

## Testing Philosophy

### Testing Pyramid
```
                    ┌─────────────────┐
                    │   E2E Tests     │ ← Few, High Value
                    │   (Playwright)  │
                ┌───┴─────────────────┴───┐
                │  Integration Tests      │ ← Some, Critical Paths
                │  (FastAPI TestClient)   │
            ┌───┴─────────────────────────┴───┐
            │     Unit Tests                  │ ← Many, Fast & Focused
            │  (pytest + React Testing Lib)  │
            └─────────────────────────────────┘
```

### Testing Principles
- **Test behavior, not implementation**
- **Write tests that provide confidence**
- **Prefer integration tests for user-facing features**
- **Use unit tests for complex business logic**
- **Mock external dependencies appropriately**

## Backend Testing (Python/FastAPI)

### Test Configuration

#### pytest Configuration
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    external: Tests that require external services
```

#### Test Environment Setup
```python
# tests/conftest.py
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
import os

from src.main import create_app
from src.infrastructure.database.connection import DatabaseConnection
from src.infrastructure.config.settings import Settings

# Test settings
class TestSettings(Settings):
    mongodb_url: str = "mongodb://localhost:27017/construction_ai_test"
    database_name: str = "construction_ai_test"
    testing: bool = True

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_database():
    """Create test database connection."""
    settings = TestSettings()
    DatabaseConnection._client = AsyncIOMotorClient(settings.mongodb_url)
    database = DatabaseConnection._client[settings.database_name]

    yield database

    # Cleanup: Drop test database
    await DatabaseConnection._client.drop_database(settings.database_name)
    await DatabaseConnection.close_connection()

@pytest.fixture
async def clean_database(test_database):
    """Clean database before each test."""
    # Drop all collections
    collections = await test_database.list_collection_names()
    for collection_name in collections:
        await test_database.drop_collection(collection_name)

    yield test_database

@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    app = create_app()
    return TestClient(app)

@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "name": "Test Building Project",
        "description": "A test construction project",
        "location": "123 Test Street, Test City",
        "type": "commercial",
        "status": "active",
        "budget": 1000000.0
    }
```

### Unit Testing

#### Testing Domain Entities
```python
# tests/domain/test_project.py
import pytest
from datetime import datetime

from src.domain.entities.project import Project, ProjectStatus, ProjectType
from src.domain.exceptions import DomainException

class TestProject:
    """Unit tests for Project entity."""

    def test_create_project_with_valid_data(self):
        """Test creating project with valid data."""
        project = Project(
            id="test_id",
            name="Test Project",
            description="Test Description",
            location="Test Location",
            type=ProjectType.COMMERCIAL,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        assert project.name == "Test Project"
        assert project.type == ProjectType.COMMERCIAL
        assert project.status == ProjectStatus.ACTIVE
        assert project.is_active() is True

    def test_project_completion(self):
        """Test project completion functionality."""
        project = Project(
            id="test_id",
            name="Test Project",
            location="Test Location",
            type=ProjectType.RESIDENTIAL,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        original_updated_at = project.updated_at
        project.complete()

        assert project.status == ProjectStatus.COMPLETED
        assert project.updated_at > original_updated_at

    @pytest.mark.parametrize("status,expected", [
        (ProjectStatus.ACTIVE, True),
        (ProjectStatus.COMPLETED, False),
        (ProjectStatus.SUSPENDED, False),
        (ProjectStatus.CANCELLED, False),
    ])
    def test_is_active_status(self, status, expected):
        """Test is_active method with different statuses."""
        project = Project(
            id="test_id",
            name="Test Project",
            location="Test Location",
            type=ProjectType.COMMERCIAL,
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        assert project.is_active() == expected
```

#### Testing Services
```python
# tests/application/services/test_project_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.application.services.project_service import ProjectService
from src.domain.entities.project import Project, ProjectStatus, ProjectType
from src.domain.exceptions import ProjectNotFoundError

class TestProjectService:
    """Unit tests for ProjectService."""

    @pytest.fixture
    def mock_project_repository(self):
        """Mock project repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock event publisher."""
        return AsyncMock()

    @pytest.fixture
    def project_service(self, mock_project_repository, mock_event_publisher):
        """Create ProjectService with mocked dependencies."""
        return ProjectService(mock_project_repository, mock_event_publisher)

    @pytest.mark.asyncio
    async def test_create_project_success(self, project_service, mock_project_repository, mock_event_publisher):
        """Test successful project creation."""
        # Arrange
        project_data = {
            "name": "Test Project",
            "description": "Test Description",
            "location": "Test Location"
        }

        expected_project = Project(
            id="generated_id",
            name=project_data["name"],
            description=project_data["description"],
            location=project_data["location"],
            type=ProjectType.COMMERCIAL,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        mock_project_repository.save.return_value = expected_project

        # Act
        result = await project_service.create_project(
            name=project_data["name"],
            description=project_data["description"],
            location=project_data["location"]
        )

        # Assert
        assert result.name == project_data["name"]
        assert result.status == ProjectStatus.ACTIVE
        mock_project_repository.save.assert_called_once()
        mock_event_publisher.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, project_service, mock_project_repository):
        """Test getting non-existent project."""
        # Arrange
        project_id = "non_existent_id"
        mock_project_repository.find_by_id.return_value = None

        # Act
        result = await project_service.get_project(project_id)

        # Assert
        assert result is None
        mock_project_repository.find_by_id.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_update_progress_project_not_found(self, project_service, mock_project_repository):
        """Test updating progress for non-existent project."""
        # Arrange
        project_id = "non_existent_id"
        mock_project_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ProjectNotFoundError):
            await project_service.update_progress(project_id, 50.0)
```

#### Testing AI Agents
```python
# tests/agents/test_visual_agent.py
import pytest
from unittest.mock import AsyncMock, Mock, patch
import json

from src.agents.visual_agent import VisualAnalysisAgent
from src.agents.interfaces.base_agent import AgentInput, AgentOutput
from src.domain.exceptions import AgentProcessingError

class TestVisualAnalysisAgent:
    """Unit tests for VisualAnalysisAgent."""

    @pytest.fixture
    def visual_agent(self):
        """Create VisualAnalysisAgent instance."""
        return VisualAnalysisAgent()

    @pytest.fixture
    def sample_agent_input(self):
        """Sample agent input for testing."""
        return AgentInput(
            data={"image_path": "/path/to/test/image.jpg"},
            project_id="test_project_id",
            session_id="test_session_id"
        )

    @pytest.mark.asyncio
    async def test_health_check_success(self, visual_agent):
        """Test successful health check."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            result = await visual_agent.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, visual_agent):
        """Test failed health check."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            result = await visual_agent.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_process_success(self, visual_agent, sample_agent_input):
        """Test successful image processing."""
        mock_analysis_result = {
            "progress_percentage": 75.5,
            "detected_elements": ["wall", "foundation"],
            "safety_issues": ["scaffolding issue"],
            "confidence": 0.85
        }

        with patch.object(visual_agent, '_analyze_image', return_value=mock_analysis_result):
            result = await visual_agent.process(sample_agent_input)

            assert isinstance(result, AgentOutput)
            assert result.agent_name == visual_agent.name
            assert result.result["progress_percentage"] == 75.5
            assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_process_missing_image_path(self, visual_agent):
        """Test processing without image path."""
        invalid_input = AgentInput(
            data={},  # Missing image_path
            project_id="test_project_id",
            session_id="test_session_id"
        )

        with pytest.raises(AgentProcessingError):
            await visual_agent.process(invalid_input)

    @pytest.mark.asyncio
    async def test_analyze_image_with_mocked_api(self, visual_agent):
        """Test image analysis with mocked API response."""
        mock_api_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "progress_percentage": 80.0,
                            "elements": ["concrete", "steel"],
                            "safety_issues": [],
                            "confidence": 0.9
                        })
                    }
                }
            ]
        }

        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_api_response
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            with patch.object(visual_agent, '_prepare_image', return_value="fake_base64_data"):
                result = await visual_agent._analyze_image("/fake/path/image.jpg")

                assert result["progress_percentage"] == 80.0
                assert "concrete" in result["elements"]
                assert len(result["safety_issues"]) == 0
```

### Integration Testing

#### Testing API Endpoints
```python
# tests/integration/test_project_api.py
import pytest
from fastapi.testclient import TestClient
import json

from src.main import create_app

class TestProjectAPI:
    """Integration tests for project API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_create_project_success(self, client, sample_project_data):
        """Test successful project creation via API."""
        response = client.post("/api/v1/projects", json=sample_project_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_project_data["name"]
        assert data["location"] == sample_project_data["location"]
        assert "id" in data

    def test_create_project_invalid_data(self, client):
        """Test project creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "location": "Test Location"
        }

        response = client.post("/api/v1/projects", json=invalid_data)
        assert response.status_code == 422

    def test_get_project_success(self, client, sample_project_data):
        """Test getting existing project."""
        # First create a project
        create_response = client.post("/api/v1/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == sample_project_data["name"]

    def test_get_project_not_found(self, client):
        """Test getting non-existent project."""
        response = client.get("/api/v1/projects/507f1f77bcf86cd799439011")  # Valid ObjectId format
        assert response.status_code == 404

    def test_list_projects(self, client, sample_project_data):
        """Test listing projects."""
        # Create multiple projects
        for i in range(3):
            project_data = sample_project_data.copy()
            project_data["name"] = f"Test Project {i}"
            client.post("/api/v1/projects", json=project_data)

        # List projects
        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert len(data["projects"]) >= 3

    def test_update_project(self, client, sample_project_data):
        """Test updating existing project."""
        # Create project
        create_response = client.post("/api/v1/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Update project
        update_data = sample_project_data.copy()
        update_data["name"] = "Updated Project Name"
        update_data["status"] = "completed"

        response = client.put(f"/api/v1/projects/{project_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["status"] == "completed"

    def test_delete_project(self, client, sample_project_data):
        """Test deleting project."""
        # Create project
        create_response = client.post("/api/v1/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Delete project
        response = client.delete(f"/api/v1/projects/{project_id}")
        assert response.status_code == 204

        # Verify project is deleted
        get_response = client.get(f"/api/v1/projects/{project_id}")
        assert get_response.status_code == 404
```

#### Testing Database Operations
```python
# tests/integration/test_database_repositories.py
import pytest
from datetime import datetime

from src.infrastructure.database.repositories.project_repository import ProjectRepository
from src.domain.entities.project import ProjectDocument, ProjectStatus, ProjectType

class TestProjectRepository:
    """Integration tests for ProjectRepository."""

    @pytest.fixture
    async def project_repository(self, clean_database):
        """Create ProjectRepository with clean database."""
        return ProjectRepository(clean_database)

    @pytest.fixture
    def sample_project(self):
        """Sample project document for testing."""
        return ProjectDocument(
            name="Integration Test Project",
            description="Test project for integration testing",
            location="Test Location",
            type=ProjectType.COMMERCIAL,
            status=ProjectStatus.ACTIVE,
            budget=500000.0
        )

    @pytest.mark.asyncio
    async def test_save_new_project(self, project_repository, sample_project):
        """Test saving new project to database."""
        # Save project
        saved_project = await project_repository.save(sample_project)

        # Verify project was saved
        assert saved_project.id is not None
        assert saved_project.name == sample_project.name
        assert saved_project.created_at is not None

    @pytest.mark.asyncio
    async def test_find_by_id(self, project_repository, sample_project):
        """Test finding project by ID."""
        # Save project
        saved_project = await project_repository.save(sample_project)

        # Find by ID
        found_project = await project_repository.find_by_id(saved_project.id)

        # Verify
        assert found_project is not None
        assert found_project.id == saved_project.id
        assert found_project.name == saved_project.name

    @pytest.mark.asyncio
    async def test_find_by_name(self, project_repository, sample_project):
        """Test finding project by name."""
        # Save project
        await project_repository.save(sample_project)

        # Find by name
        found_project = await project_repository.find_by_name(sample_project.name)

        # Verify
        assert found_project is not None
        assert found_project.name == sample_project.name

    @pytest.mark.asyncio
    async def test_find_by_status(self, project_repository, sample_project):
        """Test finding projects by status."""
        # Save multiple projects with different statuses
        project1 = sample_project.copy(update={"name": "Active Project"})
        project2 = sample_project.copy(update={"name": "Completed Project", "status": ProjectStatus.COMPLETED})

        await project_repository.save(project1)
        await project_repository.save(project2)

        # Find active projects
        active_projects = await project_repository.find_by_status(ProjectStatus.ACTIVE)

        # Verify
        assert len(active_projects) >= 1
        assert all(p.status == ProjectStatus.ACTIVE for p in active_projects)

    @pytest.mark.asyncio
    async def test_update_progress(self, project_repository, sample_project):
        """Test updating project progress."""
        # Save project
        saved_project = await project_repository.save(sample_project)

        # Update progress
        success = await project_repository.update_progress(
            saved_project.id,
            75.5,
            "construction_phase"
        )

        # Verify
        assert success is True

        # Get updated project
        updated_project = await project_repository.find_by_id(saved_project.id)
        assert updated_project.progress_percentage == 75.5
        assert updated_project.current_phase == "construction_phase"

    @pytest.mark.asyncio
    async def test_search_projects(self, project_repository):
        """Test searching projects by text."""
        # Create projects with different names
        projects = [
            ProjectDocument(
                name="Office Building Construction",
                location="Downtown",
                type=ProjectType.COMMERCIAL,
                status=ProjectStatus.ACTIVE
            ),
            ProjectDocument(
                name="Residential Complex",
                location="Suburb",
                type=ProjectType.RESIDENTIAL,
                status=ProjectStatus.ACTIVE
            ),
            ProjectDocument(
                name="Shopping Mall",
                location="Commercial District",
                type=ProjectType.COMMERCIAL,
                status=ProjectStatus.ACTIVE
            )
        ]

        for project in projects:
            await project_repository.save(project)

        # Search for "Building"
        results = await project_repository.search_projects("Building")
        assert len(results) >= 1
        assert any("Building" in p.name for p in results)

        # Search for "Commercial"
        results = await project_repository.search_projects("Commercial")
        assert len(results) >= 1
        assert any("Commercial" in p.location for p in results)
```

## Frontend Testing (React)

### Test Configuration

#### Jest Configuration
```javascript
// frontend/jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  moduleNameMapping: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/index.js',
    '!src/serviceWorker.js',
    '!src/**/*.test.{js,jsx}',
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
};
```

#### Test Setup
```javascript
// frontend/src/setupTests.js
import '@testing-library/jest-dom';
import { server } from './mocks/server';

// Establish API mocking before all tests
beforeAll(() => server.listen());

// Reset any request handlers that we may add during the tests
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished
afterAll(() => server.close());

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});
```

### Component Testing

#### Testing Form Components
```javascript
// frontend/src/components/forms/__tests__/ProjectForm.test.js
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '../../../theme';
import ProjectForm from '../ProjectForm';

const renderWithTheme = (component) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ProjectForm', () => {
  const mockOnSubmit = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders all form fields', () => {
    renderWithTheme(
      <ProjectForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />
    );

    expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/project type/i)).toBeInTheDocument();
    expect(screen.getByText(/save project/i)).toBeInTheDocument();
    expect(screen.getByText(/cancel/i)).toBeInTheDocument();
  });

  test('validates required fields', async () => {
    const user = userEvent.setup();

    renderWithTheme(
      <ProjectForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />
    );

    // Try to submit without filling required fields
    await user.click(screen.getByText(/save project/i));

    await waitFor(() => {
      expect(screen.getByText(/project name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/location is required/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  test('submits form with valid data', async () => {
    const user = userEvent.setup();

    renderWithTheme(
      <ProjectForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />
    );

    // Fill out form
    await user.type(screen.getByLabelText(/project name/i), 'Test Project');
    await user.type(screen.getByLabelText(/location/i), 'Test Location');
    await user.type(screen.getByLabelText(/description/i), 'Test Description');

    // Select project type
    await user.click(screen.getByLabelText(/project type/i));
    await user.click(screen.getByText(/commercial/i));

    // Submit form
    await user.click(screen.getByText(/save project/i));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Project',
        location: 'Test Location',
        description: 'Test Description',
        type: 'commercial',
        startDate: '',
        estimatedEndDate: '',
        budget: '',
        contractor: ''
      });
    });
  });

  test('validates date fields', async () => {
    const user = userEvent.setup();

    renderWithTheme(
      <ProjectForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />
    );

    // Fill required fields
    await user.type(screen.getByLabelText(/project name/i), 'Test Project');
    await user.type(screen.getByLabelText(/location/i), 'Test Location');

    // Set end date before start date
    await user.type(screen.getByLabelText(/start date/i), '2024-12-31');
    await user.type(screen.getByLabelText(/estimated end date/i), '2024-01-01');

    await user.click(screen.getByText(/save project/i));

    await waitFor(() => {
      expect(screen.getByText(/end date must be after start date/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  test('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();

    renderWithTheme(
      <ProjectForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />
    );

    await user.click(screen.getByText(/cancel/i));

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  test('shows loading state', () => {
    renderWithTheme(
      <ProjectForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        loading={true}
      />
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText(/save project/i)).toBeDisabled();
    expect(screen.getByText(/cancel/i)).toBeDisabled();
  });

  test('populates form with initial data', () => {
    const initialData = {
      name: 'Existing Project',
      description: 'Existing Description',
      location: 'Existing Location',
      type: 'residential'
    };

    renderWithTheme(
      <ProjectForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        initialData={initialData}
      />
    );

    expect(screen.getByDisplayValue('Existing Project')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Existing Description')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Existing Location')).toBeInTheDocument();
  });
});
```

#### Testing Custom Hooks
```javascript
// frontend/src/hooks/__tests__/useApi.test.js
import { renderHook, waitFor } from '@testing-library/react';
import { useApi } from '../useApi';
import { server } from '../../mocks/server';
import { rest } from 'msw';

describe('useApi', () => {
  test('should fetch data successfully', async () => {
    const mockData = { id: 1, name: 'Test Project' };

    server.use(
      rest.get('/api/test', (req, res, ctx) => {
        return res(ctx.json(mockData));
      })
    );

    const apiCall = () => fetch('/api/test').then(res => res.json());

    const { result } = renderHook(() => useApi(apiCall));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe(null);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBe(null);
  });

  test('should handle API errors', async () => {
    server.use(
      rest.get('/api/test', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ message: 'Server Error' }));
      })
    );

    const apiCall = () => fetch('/api/test').then(res => {
      if (!res.ok) throw new Error('API Error');
      return res.json();
    });

    const { result } = renderHook(() => useApi(apiCall));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBe(null);
    expect(result.current.error).toEqual(expect.any(Error));
  });
});
```

### Mock Service Worker (MSW) Setup
```javascript
// frontend/src/mocks/handlers.js
import { rest } from 'msw';

export const handlers = [
  // Projects API
  rest.get('/api/v1/projects', (req, res, ctx) => {
    return res(
      ctx.json({
        projects: [
          {
            id: '1',
            name: 'Test Project 1',
            location: 'Test Location 1',
            status: 'active',
            progress_percentage: 45.5
          },
          {
            id: '2',
            name: 'Test Project 2',
            location: 'Test Location 2',
            status: 'completed',
            progress_percentage: 100
          }
        ],
        total: 2,
        limit: 100,
        offset: 0
      })
    );
  }),

  rest.post('/api/v1/projects', (req, res, ctx) => {
    const newProject = {
      id: 'new-project-id',
      ...req.body,
      status: 'active',
      progress_percentage: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    return res(
      ctx.status(201),
      ctx.json(newProject)
    );
  }),

  rest.get('/api/v1/projects/:id', (req, res, ctx) => {
    const { id } = req.params;

    if (id === 'not-found') {
      return res(
        ctx.status(404),
        ctx.json({ detail: 'Project not found' })
      );
    }

    return res(
      ctx.json({
        id,
        name: `Project ${id}`,
        location: `Location ${id}`,
        status: 'active',
        progress_percentage: 75.0
      })
    );
  }),

  // Analysis API
  rest.post('/api/v1/analysis/visual', (req, res, ctx) => {
    return res(
      ctx.json({
        analysis_id: 'analysis-123',
        progress_percentage: 80.5,
        detected_elements: ['wall', 'foundation', 'roof'],
        safety_issues: ['Scaffolding requires inspection'],
        confidence_score: 0.92,
        processing_time: 2.3
      })
    );
  }),

  // Authentication API
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    const { username, password } = req.body;

    if (username === 'test@example.com' && password === 'password') {
      return res(
        ctx.json({
          access_token: 'mock-jwt-token',
          refresh_token: 'mock-refresh-token',
          token_type: 'bearer',
          expires_in: 1800
        })
      );
    }

    return res(
      ctx.status(401),
      ctx.json({ detail: 'Invalid credentials' })
    );
  }),

  rest.get('/api/v1/auth/me', (req, res, ctx) => {
    const authHeader = req.headers.get('Authorization');

    if (!authHeader || !authHeader.includes('mock-jwt-token')) {
      return res(
        ctx.status(401),
        ctx.json({ detail: 'Invalid token' })
      );
    }

    return res(
      ctx.json({
        id: 'user-123',
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
        roles: ['user'],
        permissions: ['read:projects', 'write:projects']
      })
    );
  }),
];
```

```javascript
// frontend/src/mocks/server.js
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

## End-to-End Testing

### Playwright Configuration
```javascript
// e2e/playwright.config.js
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: [
    {
      command: 'npm start',
      cwd: '../frontend',
      port: 3000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'python -m uvicorn main:app --reload --port 8000',
      cwd: '../backend',
      port: 8000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

### E2E Test Examples
```javascript
// e2e/tests/project-management.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Project Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should create a new project', async ({ page }) => {
    // Navigate to create project page
    await page.click('[data-testid="create-project-button"]');

    // Fill out project form
    await page.fill('[data-testid="project-name"]', 'E2E Test Project');
    await page.fill('[data-testid="project-location"]', 'E2E Test Location');
    await page.fill('[data-testid="project-description"]', 'Created by E2E test');

    // Select project type
    await page.click('[data-testid="project-type"]');
    await page.click('text=Commercial');

    // Submit form
    await page.click('[data-testid="save-project"]');

    // Verify success
    await expect(page.locator('text=Project created successfully')).toBeVisible();
    await expect(page.locator('text=E2E Test Project')).toBeVisible();
  });

  test('should upload and analyze an image', async ({ page }) => {
    // Create a project first
    await page.click('[data-testid="create-project-button"]');
    await page.fill('[data-testid="project-name"]', 'Image Analysis Test');
    await page.fill('[data-testid="project-location"]', 'Test Location');
    await page.click('[data-testid="project-type"]');
    await page.click('text=Commercial');
    await page.click('[data-testid="save-project"]');

    // Navigate to project detail
    await page.click('text=Image Analysis Test');

    // Upload image
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('[data-testid="upload-image-button"]');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles('./test-fixtures/construction-image.jpg');

    // Wait for analysis to complete
    await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 10000 });

    // Verify analysis results are displayed
    await expect(page.locator('[data-testid="progress-percentage"]')).toBeVisible();
    await expect(page.locator('[data-testid="detected-elements"]')).toBeVisible();
  });

  test('should handle chat interaction', async ({ page }) => {
    // Navigate to chat
    await page.click('[data-testid="chat-tab"]');

    // Send a message
    await page.fill('[data-testid="chat-input"]', 'What is the current progress of my projects?');
    await page.click('[data-testid="send-message"]');

    // Wait for AI response
    await expect(page.locator('[data-testid="ai-message"]')).toBeVisible({ timeout: 15000 });

    // Verify response contains relevant information
    const response = await page.locator('[data-testid="ai-message"]').last().textContent();
    expect(response).toContain('progress');
  });

  test('should generate and download report', async ({ page }) => {
    // Navigate to reports section
    await page.click('[data-testid="reports-tab"]');

    // Generate new report
    await page.click('[data-testid="generate-report-button"]');
    await page.selectOption('[data-testid="report-type"]', 'progress');
    await page.click('[data-testid="generate-button"]');

    // Wait for report generation
    await expect(page.locator('text=Report generated successfully')).toBeVisible({ timeout: 30000 });

    // Download report
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="download-report"]');
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toMatch(/.*\.pdf$/);
  });
});
```

## Performance Testing

### Load Testing with Locust
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import json

class ConstructionAIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login before starting tests."""
        response = self.client.post("/api/v1/auth/login", data={
            "username": "test@example.com",
            "password": "password"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(3)
    def list_projects(self):
        """List projects - most common operation."""
        self.client.get("/api/v1/projects")

    @task(2)
    def get_project_detail(self):
        """Get project details."""
        # Assume we have some test project IDs
        project_id = "507f1f77bcf86cd799439011"
        self.client.get(f"/api/v1/projects/{project_id}")

    @task(1)
    def create_project(self):
        """Create new project - less frequent."""
        project_data = {
            "name": f"Load Test Project {self.environment.stats.num_requests}",
            "location": "Load Test Location",
            "type": "commercial",
            "description": "Created by load test"
        }
        self.client.post("/api/v1/projects", json=project_data)

    @task(1)
    def upload_and_analyze_image(self):
        """Simulate image upload and analysis."""
        # This would require a test image file
        files = {'file': ('test.jpg', b'fake_image_data', 'image/jpeg')}
        self.client.post("/api/v1/analysis/visual", files=files)
```

## Continuous Integration Testing

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      mongodb:
        image: mongo:7.0
        ports:
          - 27017:27017
        env:
          MONGO_INITDB_DATABASE: construction_ai_test

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio

    - name: Run unit tests
      run: |
        cd backend
        pytest tests/unit/ -v --cov=src --cov-report=xml

    - name: Run integration tests
      run: |
        cd backend
        pytest tests/integration/ -v
      env:
        MONGODB_URL: mongodb://localhost:27017/construction_ai_test

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json

    - name: Install dependencies
      run: |
        cd frontend
        npm ci

    - name: Run tests
      run: |
        cd frontend
        npm test -- --coverage --watchAll=false

    - name: Run build test
      run: |
        cd frontend
        npm run build

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'

    - name: Install Playwright
      run: |
        cd e2e
        npm ci
        npx playwright install --with-deps

    - name: Run E2E tests
      run: |
        cd e2e
        npx playwright test

    - name: Upload Playwright Report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: playwright-report
        path: e2e/playwright-report/
```

This comprehensive testing documentation provides the foundation for implementing a robust testing strategy that ensures the reliability, performance, and quality of the Construction Analysis AI System across all layers of the application.