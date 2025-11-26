# QA Agent

## Overview

The QA Agent specializes in quality assurance, testing automation, and quality metrics for the Construction Analysis AI System. This agent provides guidance on test strategy, automated testing implementation, code quality assessment, and continuous quality improvement processes.

## Capabilities

### ✅ Testing Strategy
- Test planning and strategy development
- Test case design and management
- Test automation framework setup
- Performance and load testing
- Security testing integration

### 🔍 Code Quality Analysis
- Static code analysis and linting
- Code coverage measurement
- Technical debt assessment
- Code review automation
- Dependency vulnerability scanning

### 📊 Quality Metrics
- Quality metrics definition and tracking
- Test results analysis and reporting
- Performance benchmarking
- Quality trend analysis
- Continuous improvement recommendations

## Core Responsibilities

### 1. Test Automation Framework

#### Backend Testing Framework (Python/FastAPI)
```python
# tests/conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
import mongomock_motor

from main import app
from infrastructure.database.mongodb import get_database
from domain.entities.project import Project, ProjectType, ProjectStatus
from application.services.project_service import ProjectService

# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """Create a test database instance"""
    # Use mongomock for testing
    client = mongomock_motor.AsyncMongoMockClient()
    database = client.test_construction_analysis
    yield database
    await client.close()

@pytest.fixture
async def test_client(test_db):
    """Create a test client with dependency overrides"""

    # Override database dependency
    app.dependency_overrides[get_database] = lambda: test_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {
        "name": "Test Construction Project",
        "description": "A test project for QA validation",
        "project_type": ProjectType.RESIDENTIAL,
        "start_date": "2025-01-01T00:00:00Z",
        "expected_completion": "2025-12-31T00:00:00Z",
        "budget": {
            "total_budget": 500000.0,
            "allocated_budget": 400000.0,
            "spent_amount": 0.0,
            "remaining_budget": 500000.0,
            "currency": "USD"
        },
        "location": {
            "address": "123 Test Street",
            "city": "Test City",
            "state": "Test State",
            "country": "Test Country",
            "postal_code": "12345"
        }
    }

@pytest.fixture
async def created_project(test_client, sample_project_data):
    """Create a project for testing"""
    response = await test_client.post("/api/v1/projects/", json=sample_project_data)
    assert response.status_code == 201
    return response.json()

# Utility fixtures
@pytest.fixture
def mock_openrouter_client():
    """Mock OpenRouter client for AI testing"""
    class MockOpenRouterClient:
        async def chat_completions_create(self, **kwargs):
            return {
                "choices": [{
                    "message": {
                        "content": "Mock AI response for testing"
                    }
                }]
            }

    return MockOpenRouterClient()

@pytest.fixture
def mock_file_storage():
    """Mock file storage for testing"""
    class MockFileStorage:
        def __init__(self):
            self.files = {}

        async def save_file(self, file_data, filename):
            file_id = f"test_file_{len(self.files)}"
            self.files[file_id] = {"data": file_data, "filename": filename}
            return file_id

        async def get_file(self, file_id):
            return self.files.get(file_id)

        async def delete_file(self, file_id):
            if file_id in self.files:
                del self.files[file_id]
                return True
            return False

    return MockFileStorage()
```

#### Comprehensive Test Suites
```python
# tests/test_project_service.py
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from domain.entities.project import Project, ProjectType, ProjectStatus
from application.services.project_service import ProjectService
from application.exceptions import EntityNotFoundError, ValidationError
from infrastructure.repositories.mongodb.project_repository import MongoProjectRepository

class TestProjectService:
    """Comprehensive test suite for ProjectService"""

    @pytest.fixture
    async def project_service(self, test_db):
        """Create ProjectService instance with test database"""
        repository = MongoProjectRepository(test_db)
        return ProjectService(repository)

    @pytest.mark.asyncio
    async def test_create_project_success(self, project_service, sample_project_data):
        """Test successful project creation"""

        project = await project_service.create_project(
            name=sample_project_data["name"],
            description=sample_project_data["description"],
            project_type=sample_project_data["project_type"],
            start_date=datetime.fromisoformat(sample_project_data["start_date"].replace('Z', '+00:00')),
            expected_completion=datetime.fromisoformat(sample_project_data["expected_completion"].replace('Z', '+00:00')),
            budget=sample_project_data["budget"]["total_budget"],
            owner_id=str(uuid4())
        )

        assert project.name == sample_project_data["name"]
        assert project.description == sample_project_data["description"]
        assert project.project_type == sample_project_data["project_type"]
        assert project.status == ProjectStatus.PLANNING
        assert project.id is not None

    @pytest.mark.asyncio
    async def test_create_project_validation_errors(self, project_service):
        """Test project creation validation errors"""

        owner_id = str(uuid4())
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=365)

        # Test empty name
        with pytest.raises(ValidationError, match="Project name cannot be empty"):
            await project_service.create_project(
                name="",
                description="Test description",
                project_type=ProjectType.RESIDENTIAL,
                start_date=start_date,
                expected_completion=end_date,
                budget=100000.0,
                owner_id=owner_id
            )

        # Test negative budget
        with pytest.raises(ValidationError, match="Budget must be positive"):
            await project_service.create_project(
                name="Test Project",
                description="Test description",
                project_type=ProjectType.RESIDENTIAL,
                start_date=start_date,
                expected_completion=end_date,
                budget=-1000.0,
                owner_id=owner_id
            )

        # Test invalid date range
        with pytest.raises(ValidationError, match="Start date must be before expected completion"):
            await project_service.create_project(
                name="Test Project",
                description="Test description",
                project_type=ProjectType.RESIDENTIAL,
                start_date=end_date,
                expected_completion=start_date,
                budget=100000.0,
                owner_id=owner_id
            )

    @pytest.mark.asyncio
    async def test_get_project_success(self, project_service, sample_project_data):
        """Test successful project retrieval"""

        # Create project first
        created_project = await project_service.create_project(
            name=sample_project_data["name"],
            description=sample_project_data["description"],
            project_type=sample_project_data["project_type"],
            start_date=datetime.fromisoformat(sample_project_data["start_date"].replace('Z', '+00:00')),
            expected_completion=datetime.fromisoformat(sample_project_data["expected_completion"].replace('Z', '+00:00')),
            budget=sample_project_data["budget"]["total_budget"],
            owner_id=str(uuid4())
        )

        # Retrieve project
        retrieved_project = await project_service.get_project(created_project.id)

        assert retrieved_project.id == created_project.id
        assert retrieved_project.name == created_project.name

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, project_service):
        """Test project not found error"""

        non_existent_id = str(uuid4())

        with pytest.raises(EntityNotFoundError, match=f"Project with ID {non_existent_id} not found"):
            await project_service.get_project(non_existent_id)

    @pytest.mark.asyncio
    async def test_update_project_status(self, project_service, sample_project_data):
        """Test project status update"""

        # Create project
        project = await project_service.create_project(
            name=sample_project_data["name"],
            description=sample_project_data["description"],
            project_type=sample_project_data["project_type"],
            start_date=datetime.fromisoformat(sample_project_data["start_date"].replace('Z', '+00:00')),
            expected_completion=datetime.fromisoformat(sample_project_data["expected_completion"].replace('Z', '+00:00')),
            budget=sample_project_data["budget"]["total_budget"],
            owner_id=str(uuid4())
        )

        # Update status
        updated_project = await project_service.update_project_status(
            project.id, ProjectStatus.IN_PROGRESS
        )

        assert updated_project.status == ProjectStatus.IN_PROGRESS
        assert updated_project.updated_at > project.updated_at

    @pytest.mark.asyncio
    async def test_add_project_cost(self, project_service, sample_project_data):
        """Test adding cost to project"""

        # Create project
        project = await project_service.create_project(
            name=sample_project_data["name"],
            description=sample_project_data["description"],
            project_type=sample_project_data["project_type"],
            start_date=datetime.fromisoformat(sample_project_data["start_date"].replace('Z', '+00:00')),
            expected_completion=datetime.fromisoformat(sample_project_data["expected_completion"].replace('Z', '+00:00')),
            budget=sample_project_data["budget"]["total_budget"],
            owner_id=str(uuid4())
        )

        initial_cost = project.current_cost
        cost_to_add = 1000.0

        # Add cost
        updated_project = await project_service.add_project_cost(
            project.id, cost_to_add, "Test expense"
        )

        assert updated_project.current_cost == initial_cost + cost_to_add

        # Test negative cost
        with pytest.raises(ValidationError, match="Cost amount must be positive"):
            await project_service.add_project_cost(
                project.id, -500.0, "Invalid expense"
            )

    @pytest.mark.asyncio
    async def test_get_project_statistics(self, project_service, sample_project_data):
        """Test project statistics calculation"""

        # Create project
        project = await project_service.create_project(
            name=sample_project_data["name"],
            description=sample_project_data["description"],
            project_type=sample_project_data["project_type"],
            start_date=datetime.fromisoformat(sample_project_data["start_date"].replace('Z', '+00:00')),
            expected_completion=datetime.fromisoformat(sample_project_data["expected_completion"].replace('Z', '+00:00')),
            budget=sample_project_data["budget"]["total_budget"],
            owner_id=str(uuid4())
        )

        # Add some cost
        await project_service.add_project_cost(project.id, 50000.0, "Initial costs")

        # Get statistics
        stats = await project_service.get_project_statistics(project.id)

        assert "budget_utilization" in stats
        assert "days_elapsed" in stats
        assert "is_overdue" in stats
        assert "remaining_budget" in stats
        assert "status" in stats

        assert stats["budget_utilization"] == 10.0  # 50000 / 500000 * 100
        assert stats["remaining_budget"] == 450000.0
        assert stats["status"] == ProjectStatus.PLANNING.value

# API Integration Tests
# tests/test_project_api.py
import pytest
from httpx import AsyncClient

class TestProjectAPI:
    """API integration tests for project endpoints"""

    @pytest.mark.asyncio
    async def test_create_project_api(self, test_client: AsyncClient, sample_project_data):
        """Test project creation via API"""

        response = await test_client.post("/api/v1/projects/", json=sample_project_data)

        assert response.status_code == 201

        project_data = response.json()
        assert project_data["name"] == sample_project_data["name"]
        assert project_data["description"] == sample_project_data["description"]
        assert "id" in project_data

    @pytest.mark.asyncio
    async def test_get_project_api(self, test_client: AsyncClient, created_project):
        """Test project retrieval via API"""

        project_id = created_project["id"]
        response = await test_client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200

        project_data = response.json()
        assert project_data["id"] == project_id
        assert project_data["name"] == created_project["name"]

    @pytest.mark.asyncio
    async def test_list_projects_api(self, test_client: AsyncClient, created_project):
        """Test project listing via API"""

        response = await test_client.get("/api/v1/projects/")

        assert response.status_code == 200

        projects = response.json()
        assert isinstance(projects, list)
        assert len(projects) >= 1

        # Find our created project
        found_project = next((p for p in projects if p["id"] == created_project["id"]), None)
        assert found_project is not None

    @pytest.mark.asyncio
    async def test_update_project_status_api(self, test_client: AsyncClient, created_project):
        """Test project status update via API"""

        project_id = created_project["id"]
        status_update = {"status": "in_progress"}

        response = await test_client.patch(f"/api/v1/projects/{project_id}/status", json=status_update)

        assert response.status_code == 200

        updated_project = response.json()
        assert updated_project["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_get_project_statistics_api(self, test_client: AsyncClient, created_project):
        """Test project statistics via API"""

        project_id = created_project["id"]
        response = await test_client.get(f"/api/v1/projects/{project_id}/statistics")

        assert response.status_code == 200

        stats = response.json()
        assert "budget_utilization" in stats
        assert "days_elapsed" in stats
        assert "is_overdue" in stats

    @pytest.mark.asyncio
    async def test_project_not_found_api(self, test_client: AsyncClient):
        """Test 404 response for non-existent project"""

        non_existent_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
        response = await test_client.get(f"/api/v1/projects/{non_existent_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_project_data_api(self, test_client: AsyncClient):
        """Test validation errors via API"""

        invalid_data = {
            "name": "",  # Empty name
            "description": "Test",
            "project_type": "invalid_type",
            "start_date": "invalid_date",
            "expected_completion": "2025-12-31T00:00:00Z",
            "budget": -1000  # Negative budget
        }

        response = await test_client.post("/api/v1/projects/", json=invalid_data)

        assert response.status_code == 400

        error_data = response.json()
        assert "detail" in error_data
```

### 2. Frontend Testing Framework (React/Jest)

#### Component Testing Setup
```typescript
// frontend/src/setupTests.ts
import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';
import { server } from './mocks/server';

// Configure testing library
configure({ testIdAttribute: 'data-testid' });

// Establish API mocking before all tests
beforeAll(() => server.listen());

// Reset any request handlers that we may add during the tests
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished
afterAll(() => server.close());

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});
```

#### Mock Service Worker Setup
```typescript
// frontend/src/mocks/handlers.ts
import { rest } from 'msw';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const handlers = [
  // Projects API
  rest.get(`${API_BASE_URL}/projects`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          id: '1',
          name: 'Test Project 1',
          description: 'Test project description',
          project_type: 'residential',
          status: 'planning',
          created_at: '2025-01-01T00:00:00Z',
          start_date: '2025-01-01T00:00:00Z',
          expected_completion: '2025-12-31T00:00:00Z',
          budget: {
            total_budget: 500000,
            allocated_budget: 400000,
            spent_amount: 50000,
            remaining_budget: 450000,
            currency: 'USD'
          },
          progress_percentage: 25.0
        }
      ])
    );
  }),

  rest.post(`${API_BASE_URL}/projects`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: '2',
        name: 'New Test Project',
        description: 'New project description',
        project_type: 'commercial',
        status: 'planning',
        created_at: new Date().toISOString(),
        progress_percentage: 0.0
      })
    );
  }),

  rest.get(`${API_BASE_URL}/projects/:id`, (req, res, ctx) => {
    const { id } = req.params;

    return res(
      ctx.status(200),
      ctx.json({
        id,
        name: `Project ${id}`,
        description: 'Project description',
        project_type: 'residential',
        status: 'in_progress',
        progress_percentage: 45.0
      })
    );
  }),

  // File upload API
  rest.post(`${API_BASE_URL}/files/upload`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        success: true,
        file_id: 'test-file-id',
        message: 'File uploaded successfully'
      })
    );
  }),

  // Analysis API
  rest.post(`${API_BASE_URL}/analyses`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: 'analysis-1',
        project_id: '1',
        analysis_type: 'progress_tracking',
        status: 'completed',
        result: {
          overall_score: 85.0,
          findings: [
            {
              id: 'finding-1',
              title: 'Good Progress',
              description: 'Project is on track',
              severity: 'info'
            }
          ],
          summary: 'Analysis completed successfully'
        }
      })
    );
  }),

  // Error responses
  rest.get(`${API_BASE_URL}/projects/non-existent`, (req, res, ctx) => {
    return res(
      ctx.status(404),
      ctx.json({ detail: 'Project not found' })
    );
  }),

  rest.post(`${API_BASE_URL}/projects/invalid`, (req, res, ctx) => {
    return res(
      ctx.status(400),
      ctx.json({ detail: 'Invalid project data' })
    );
  })
];

// frontend/src/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

#### Component Tests
```typescript
// frontend/src/components/__tests__/ProjectCard.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { createTheme } from '@mui/material/styles';
import { ProjectCard } from '../ProjectCard';

const theme = createTheme();

const mockProject = {
  id: '1',
  name: 'Test Construction Project',
  description: 'A test project for validation',
  project_type: 'residential',
  status: 'in_progress',
  progress_percentage: 65.0,
  budget: {
    total_budget: 500000,
    spent_amount: 200000,
    remaining_budget: 300000,
    currency: 'USD'
  },
  start_date: '2025-01-01T00:00:00Z',
  expected_completion: '2025-12-31T00:00:00Z'
};

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ProjectCard', () => {
  const mockOnUpdate = jest.fn();
  const mockOnDelete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders project information correctly', () => {
    renderWithTheme(
      <ProjectCard
        project={mockProject}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('Test Construction Project')).toBeInTheDocument();
    expect(screen.getByText('A test project for validation')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('displays budget information', () => {
    renderWithTheme(
      <ProjectCard
        project={mockProject}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('$500,000')).toBeInTheDocument(); // Total budget
    expect(screen.getByText('$200,000')).toBeInTheDocument(); // Spent amount
    expect(screen.getByText('$300,000')).toBeInTheDocument(); // Remaining
  });

  it('shows correct progress visualization', () => {
    renderWithTheme(
      <ProjectCard
        project={mockProject}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '65');
  });

  it('calls onUpdate when edit button is clicked', async () => {
    renderWithTheme(
      <ProjectCard
        project={mockProject}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    const editButton = screen.getByLabelText('Edit project');
    fireEvent.click(editButton);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(mockProject.id);
    });
  });

  it('calls onDelete when delete button is clicked', async () => {
    renderWithTheme(
      <ProjectCard
        project={mockProject}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    const deleteButton = screen.getByLabelText('Delete project');
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockOnDelete).toHaveBeenCalledWith(mockProject.id);
    });
  });

  it('renders different status colors correctly', () => {
    const completedProject = { ...mockProject, status: 'completed' };

    renderWithTheme(
      <ProjectCard
        project={completedProject}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('handles missing budget data gracefully', () => {
    const projectWithoutBudget = { ...mockProject, budget: undefined };

    renderWithTheme(
      <ProjectCard
        project={projectWithoutBudget}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('Budget not available')).toBeInTheDocument();
  });

  it('displays project type correctly', () => {
    renderWithTheme(
      <ProjectCard
        project={mockProject}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('Residential')).toBeInTheDocument();
  });
});

// frontend/src/hooks/__tests__/useProjects.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useProjects } from '../useProjects';

describe('useProjects hook', () => {
  it('fetches projects successfully', async () => {
    const { result } = renderHook(() => useProjects());

    expect(result.current.loading).toBe(true);
    expect(result.current.projects).toEqual([]);
    expect(result.current.error).toBe(null);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(1);
    expect(result.current.projects[0].name).toBe('Test Project 1');
    expect(result.current.error).toBe(null);
  });

  it('handles fetch errors', async () => {
    // Mock API to return error
    server.use(
      rest.get('http://localhost:8000/api/v1/projects', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ detail: 'Internal server error' }));
      })
    );

    const { result } = renderHook(() => useProjects());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.projects).toEqual([]);
    expect(result.current.error).toContain('Failed to fetch projects');
  });

  it('refetches projects when refetch is called', async () => {
    const { result } = renderHook(() => useProjects());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(1);

    // Call refetch
    result.current.refetch();

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(1);
  });
});
```

### 3. End-to-End Testing with Playwright

#### E2E Test Configuration
```typescript
// e2e/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/test-results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
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
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  webServer: [
    {
      command: 'npm run dev',
      port: 3000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd ../backend && python -m uvicorn main:app --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
    }
  ],
});
```

#### E2E Test Cases
```typescript
// e2e/tests/project-management.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Project Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');

    // Wait for the page to load
    await expect(page.locator('h1')).toContainText('Construction Analysis');
  });

  test('should create a new project', async ({ page }) => {
    // Click create project button
    await page.click('[data-testid="create-project-button"]');

    // Fill project form
    await page.fill('[data-testid="project-name-input"]', 'E2E Test Project');
    await page.fill('[data-testid="project-description-input"]', 'Created by E2E test');
    await page.selectOption('[data-testid="project-type-select"]', 'residential');
    await page.fill('[data-testid="start-date-input"]', '2025-01-01');
    await page.fill('[data-testid="completion-date-input"]', '2025-12-31');
    await page.fill('[data-testid="budget-input"]', '500000');

    // Submit form
    await page.click('[data-testid="submit-project-button"]');

    // Verify project was created
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
    await expect(page.locator('text=E2E Test Project')).toBeVisible();
  });

  test('should display project list', async ({ page }) => {
    // Navigate to projects page
    await page.click('a[href="/projects"]');

    // Wait for projects to load
    await page.waitForSelector('[data-testid="project-card"]');

    // Verify at least one project is displayed
    const projectCards = page.locator('[data-testid="project-card"]');
    await expect(projectCards).toHaveCountGreaterThan(0);

    // Verify project card contains expected elements
    const firstCard = projectCards.first();
    await expect(firstCard.locator('[data-testid="project-name"]')).toBeVisible();
    await expect(firstCard.locator('[data-testid="project-status"]')).toBeVisible();
    await expect(firstCard.locator('[data-testid="project-progress"]')).toBeVisible();
  });

  test('should update project status', async ({ page }) => {
    // Navigate to projects page
    await page.click('a[href="/projects"]');

    // Wait for projects to load
    await page.waitForSelector('[data-testid="project-card"]');

    // Click on first project
    const firstCard = page.locator('[data-testid="project-card"]').first();
    await firstCard.click();

    // Click status update button
    await page.click('[data-testid="update-status-button"]');

    // Select new status
    await page.selectOption('[data-testid="status-select"]', 'in_progress');

    // Confirm update
    await page.click('[data-testid="confirm-status-update"]');

    // Verify status was updated
    await expect(page.locator('[data-testid="project-status"]')).toContainText('In Progress');
  });

  test('should upload and analyze files', async ({ page }) => {
    // Navigate to analysis page
    await page.click('a[href="/analysis"]');

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./test-files/sample-image.jpg');

    // Wait for file to upload
    await expect(page.locator('[data-testid="upload-success"]')).toBeVisible();

    // Start analysis
    await page.click('[data-testid="start-analysis-button"]');

    // Wait for analysis to complete
    await page.waitForSelector('[data-testid="analysis-result"]', { timeout: 30000 });

    // Verify analysis results are displayed
    await expect(page.locator('[data-testid="analysis-score"]')).toBeVisible();
    await expect(page.locator('[data-testid="analysis-findings"]')).toBeVisible();
  });

  test('should handle real-time chat', async ({ page }) => {
    // Navigate to chat page
    await page.click('a[href="/chat"]');

    // Wait for chat interface to load
    await page.waitForSelector('[data-testid="chat-interface"]');

    // Send a message
    await page.fill('[data-testid="chat-input"]', 'Hello, can you help me analyze this project?');
    await page.click('[data-testid="send-message-button"]');

    // Verify message appears in chat
    await expect(page.locator('[data-testid="user-message"]').last()).toContainText('Hello, can you help me analyze this project?');

    // Wait for AI response
    await page.waitForSelector('[data-testid="ai-message"]', { timeout: 10000 });

    // Verify AI response appears
    await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible();
  });

  test('should be responsive on mobile devices', async ({ page, browserName }) => {
    // Skip on desktop browsers
    if (browserName === 'chromium' || browserName === 'firefox' || browserName === 'webkit') {
      test.skip(page.viewportSize()?.width && page.viewportSize()?.width > 768);
    }

    // Test mobile navigation
    await page.click('[data-testid="mobile-menu-button"]');
    await expect(page.locator('[data-testid="mobile-navigation"]')).toBeVisible();

    // Test mobile project cards
    await page.click('a[href="/projects"]');
    const projectCards = page.locator('[data-testid="project-card"]');

    // Verify cards stack vertically on mobile
    const firstCard = projectCards.first();
    const secondCard = projectCards.nth(1);

    if (await secondCard.isVisible()) {
      const firstCardBox = await firstCard.boundingBox();
      const secondCardBox = await secondCard.boundingBox();

      // Second card should be below the first card
      expect(secondCardBox?.y).toBeGreaterThan((firstCardBox?.y || 0) + (firstCardBox?.height || 0));
    }
  });
});

// e2e/tests/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y, getViolations } from 'axe-playwright';

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await injectAxe(page);
  });

  test('should have no accessibility violations on home page', async ({ page }) => {
    await checkA11y(page, null, {
      detailedReport: true,
      detailedReportOptions: { html: true }
    });
  });

  test('should have no accessibility violations on projects page', async ({ page }) => {
    await page.click('a[href="/projects"]');
    await page.waitForLoadState('networkidle');

    await checkA11y(page, null, {
      detailedReport: true,
      detailedReportOptions: { html: true }
    });
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Test tab navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();

    // Navigate through main menu items
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
    }
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();

    expect(headings.length).toBeGreaterThan(0);

    // Check that h1 exists
    const h1Elements = await page.locator('h1').count();
    expect(h1Elements).toBeGreaterThanOrEqual(1);
  });

  test('should have proper alt text for images', async ({ page }) => {
    const images = await page.locator('img').all();

    for (const image of images) {
      const altText = await image.getAttribute('alt');
      expect(altText).not.toBeNull();
      expect(altText).not.toBe('');
    }
  });
});
```

### 4. Performance Testing

#### Load Testing with Locust
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import json
import random
from datetime import datetime, timedelta

class ConstructionAnalysisUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Setup test data"""
        self.project_id = None
        self.auth_token = None

        # Simulate login (if auth is implemented)
        # self.login()

        # Create a test project
        self.create_test_project()

    def login(self):
        """Simulate user login"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": f"test_{random.randint(1000, 9999)}@example.com",
            "password": "testpassword123"
        })

        if response.status_code == 200:
            self.auth_token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})

    def create_test_project(self):
        """Create a test project for load testing"""
        project_data = {
            "name": f"Load Test Project {random.randint(1000, 9999)}",
            "description": "Project created for load testing",
            "project_type": random.choice(["residential", "commercial", "industrial"]),
            "start_date": datetime.utcnow().isoformat() + "Z",
            "expected_completion": (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z",
            "budget": {
                "total_budget": random.randint(100000, 1000000),
                "allocated_budget": 0,
                "spent_amount": 0,
                "remaining_budget": 0,
                "currency": "USD"
            },
            "location": {
                "address": "123 Load Test St",
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
                "postal_code": "12345"
            }
        }

        response = self.client.post("/api/v1/projects/", json=project_data)
        if response.status_code == 201:
            self.project_id = response.json().get("id")

    @task(3)
    def list_projects(self):
        """Test project listing endpoint"""
        self.client.get("/api/v1/projects/")

    @task(2)
    def get_project_details(self):
        """Test project details endpoint"""
        if self.project_id:
            self.client.get(f"/api/v1/projects/{self.project_id}")

    @task(1)
    def update_project_status(self):
        """Test project status update"""
        if self.project_id:
            status_data = {
                "status": random.choice(["planning", "in_progress", "under_review", "completed"])
            }
            self.client.patch(f"/api/v1/projects/{self.project_id}/status", json=status_data)

    @task(1)
    def get_project_statistics(self):
        """Test project statistics endpoint"""
        if self.project_id:
            self.client.get(f"/api/v1/projects/{self.project_id}/statistics")

    @task(1)
    def create_analysis(self):
        """Test analysis creation"""
        if self.project_id:
            analysis_data = {
                "project_id": self.project_id,
                "analysis_type": random.choice([
                    "progress_tracking", "quality_inspection", "safety_assessment"
                ]),
                "parameters": {
                    "threshold": 0.8,
                    "detailed": True
                }
            }
            self.client.post("/api/v1/analyses/", json=analysis_data)

    @task(1)
    def health_check(self):
        """Test health check endpoint"""
        self.client.get("/health")

class DatabaseLoadUser(HttpUser):
    """User class for testing database operations"""
    wait_time = between(0.5, 2)

    @task
    def complex_project_query(self):
        """Test complex project queries"""
        params = {
            "status": random.choice(["planning", "in_progress", "completed"]),
            "project_type": random.choice(["residential", "commercial"]),
            "limit": 50
        }
        self.client.get("/api/v1/projects/", params=params)

    @task
    def search_projects(self):
        """Test project search"""
        search_terms = ["test", "construction", "building", "project"]
        params = {"q": random.choice(search_terms)}
        self.client.get("/api/v1/projects/search", params=params)

class FileUploadUser(HttpUser):
    """User class for testing file upload operations"""
    wait_time = between(2, 5)

    @task
    def upload_file(self):
        """Test file upload"""
        # Simulate uploading a small test file
        files = {
            'file': ('test.txt', b'This is a test file for load testing', 'text/plain')
        }
        self.client.post("/api/v1/files/upload", files=files)

# Performance test configuration
# tests/performance/run_tests.py
import subprocess
import sys
import time
from datetime import datetime

def run_performance_tests():
    """Run comprehensive performance tests"""

    print("🚀 Starting Performance Test Suite")
    print("=" * 50)

    # Test configurations
    test_configs = [
        {
            "name": "Light Load Test",
            "users": 10,
            "spawn_rate": 2,
            "duration": "2m",
            "user_class": "ConstructionAnalysisUser"
        },
        {
            "name": "Medium Load Test",
            "users": 50,
            "spawn_rate": 5,
            "duration": "5m",
            "user_class": "ConstructionAnalysisUser"
        },
        {
            "name": "Heavy Load Test",
            "users": 100,
            "spawn_rate": 10,
            "duration": "10m",
            "user_class": "ConstructionAnalysisUser"
        },
        {
            "name": "Database Stress Test",
            "users": 30,
            "spawn_rate": 5,
            "duration": "3m",
            "user_class": "DatabaseLoadUser"
        },
        {
            "name": "File Upload Test",
            "users": 20,
            "spawn_rate": 2,
            "duration": "3m",
            "user_class": "FileUploadUser"
        }
    ]

    results = []

    for config in test_configs:
        print(f"\n📊 Running {config['name']}")
        print(f"Users: {config['users']}, Duration: {config['duration']}")

        start_time = datetime.now()

        # Run locust test
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--headless",
            "--users", str(config['users']),
            "--spawn-rate", str(config['spawn_rate']),
            "--run-time", config['duration'],
            "--host", "http://localhost:8000",
            "--html", f"reports/{config['name'].lower().replace(' ', '_')}_report.html",
            "--csv", f"reports/{config['name'].lower().replace(' ', '_')}",
            config['user_class']
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            test_result = {
                "name": config['name'],
                "duration": duration,
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr
            }

            results.append(test_result)

            if result.returncode == 0:
                print(f"✅ {config['name']} completed successfully")
            else:
                print(f"❌ {config['name']} failed")
                print(f"Error: {result.stderr}")

        except subprocess.TimeoutExpired:
            print(f"⏰ {config['name']} timed out")
            results.append({
                "name": config['name'],
                "duration": 900,
                "success": False,
                "output": "Test timed out"
            })

        # Wait between tests
        time.sleep(10)

    # Generate summary report
    print("\n📈 Performance Test Summary")
    print("=" * 50)

    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"{result['name']}: {status} ({result['duration']:.1f}s)")

    return results

if __name__ == "__main__":
    run_performance_tests()
```

### 5. Quality Metrics and Reporting

#### Code Quality Dashboard
```python
# tests/quality/quality_dashboard.py
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, Any, List

class QualityMetricsCollector:
    """Collect and analyze quality metrics"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.backend_path = os.path.join(project_root, "backend")
        self.frontend_path = os.path.join(project_root, "frontend")

    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive quality metrics"""

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "backend": self.collect_backend_metrics(),
            "frontend": self.collect_frontend_metrics(),
            "security": self.collect_security_metrics(),
            "performance": self.collect_performance_metrics()
        }

        return metrics

    def collect_backend_metrics(self) -> Dict[str, Any]:
        """Collect Python/FastAPI quality metrics"""

        metrics = {}

        # Code coverage
        try:
            coverage_result = subprocess.run(
                ["coverage", "report", "--format=json"],
                capture_output=True,
                text=True,
                cwd=self.backend_path
            )

            if coverage_result.returncode == 0:
                coverage_data = json.loads(coverage_result.stdout)
                metrics["coverage"] = {
                    "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                    "lines_covered": coverage_data.get("totals", {}).get("covered_lines", 0),
                    "lines_total": coverage_data.get("totals", {}).get("num_statements", 0)
                }
        except Exception as e:
            metrics["coverage"] = {"error": str(e)}

        # Code complexity with radon
        try:
            complexity_result = subprocess.run(
                ["radon", "cc", ".", "--json"],
                capture_output=True,
                text=True,
                cwd=self.backend_path
            )

            if complexity_result.returncode == 0:
                complexity_data = json.loads(complexity_result.stdout)
                total_complexity = 0
                file_count = 0

                for file_data in complexity_data.values():
                    for item in file_data:
                        if isinstance(item, dict) and 'complexity' in item:
                            total_complexity += item['complexity']
                            file_count += 1

                metrics["complexity"] = {
                    "average_complexity": total_complexity / file_count if file_count > 0 else 0,
                    "total_complexity": total_complexity,
                    "file_count": file_count
                }
        except Exception as e:
            metrics["complexity"] = {"error": str(e)}

        # Code style with flake8
        try:
            style_result = subprocess.run(
                ["flake8", ".", "--format=json"],
                capture_output=True,
                text=True,
                cwd=self.backend_path
            )

            if style_result.returncode == 0:
                violations = style_result.stdout.count('\n') if style_result.stdout else 0
                metrics["style"] = {
                    "violations": violations,
                    "status": "clean" if violations == 0 else "issues_found"
                }
            else:
                violations = style_result.stdout.count('\n') if style_result.stdout else 0
                metrics["style"] = {
                    "violations": violations,
                    "status": "issues_found"
                }
        except Exception as e:
            metrics["style"] = {"error": str(e)}

        # Type checking with mypy
        try:
            type_result = subprocess.run(
                ["mypy", ".", "--json-report", "/tmp/mypy-report"],
                capture_output=True,
                text=True,
                cwd=self.backend_path
            )

            type_errors = type_result.stdout.count("error:")
            metrics["type_checking"] = {
                "errors": type_errors,
                "status": "clean" if type_errors == 0 else "errors_found"
            }
        except Exception as e:
            metrics["type_checking"] = {"error": str(e)}

        return metrics

    def collect_frontend_metrics(self) -> Dict[str, Any]:
        """Collect React/TypeScript quality metrics"""

        metrics = {}

        # Jest test coverage
        try:
            coverage_result = subprocess.run(
                ["npm", "run", "test:coverage", "--", "--watchAll=false", "--coverage", "--coverageReporters=json"],
                capture_output=True,
                text=True,
                cwd=self.frontend_path
            )

            coverage_file = os.path.join(self.frontend_path, "coverage", "coverage-final.json")
            if os.path.exists(coverage_file):
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)

                total_lines = 0
                covered_lines = 0

                for file_data in coverage_data.values():
                    statements = file_data.get('s', {})
                    total_lines += len(statements)
                    covered_lines += sum(1 for count in statements.values() if count > 0)

                metrics["coverage"] = {
                    "total_coverage": (covered_lines / total_lines * 100) if total_lines > 0 else 0,
                    "lines_covered": covered_lines,
                    "lines_total": total_lines
                }
        except Exception as e:
            metrics["coverage"] = {"error": str(e)}

        # ESLint for code style
        try:
            lint_result = subprocess.run(
                ["npx", "eslint", "src", "--format=json"],
                capture_output=True,
                text=True,
                cwd=self.frontend_path
            )

            if lint_result.stdout:
                lint_data = json.loads(lint_result.stdout)
                total_errors = sum(len(file_data.get('messages', [])) for file_data in lint_data)

                metrics["style"] = {
                    "violations": total_errors,
                    "status": "clean" if total_errors == 0 else "issues_found"
                }
            else:
                metrics["style"] = {"violations": 0, "status": "clean"}

        except Exception as e:
            metrics["style"] = {"error": str(e)}

        # TypeScript compilation
        try:
            tsc_result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                capture_output=True,
                text=True,
                cwd=self.frontend_path
            )

            type_errors = tsc_result.stderr.count("error TS") if tsc_result.stderr else 0
            metrics["type_checking"] = {
                "errors": type_errors,
                "status": "clean" if type_errors == 0 else "errors_found"
            }
        except Exception as e:
            metrics["type_checking"] = {"error": str(e)}

        # Bundle size analysis
        try:
            build_result = subprocess.run(
                ["npm", "run", "build"],
                capture_output=True,
                text=True,
                cwd=self.frontend_path
            )

            build_dir = os.path.join(self.frontend_path, "build", "static", "js")
            if os.path.exists(build_dir):
                js_files = [f for f in os.listdir(build_dir) if f.endswith('.js')]
                total_size = sum(os.path.getsize(os.path.join(build_dir, f)) for f in js_files)

                metrics["bundle_size"] = {
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "file_count": len(js_files)
                }
        except Exception as e:
            metrics["bundle_size"] = {"error": str(e)}

        return metrics

    def collect_security_metrics(self) -> Dict[str, Any]:
        """Collect security-related metrics"""

        metrics = {}

        # Backend security scan with bandit
        try:
            bandit_result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                capture_output=True,
                text=True,
                cwd=self.backend_path
            )

            if bandit_result.stdout:
                bandit_data = json.loads(bandit_result.stdout)
                metrics["backend_security"] = {
                    "high_severity": len([r for r in bandit_data.get('results', []) if r.get('issue_severity') == 'HIGH']),
                    "medium_severity": len([r for r in bandit_data.get('results', []) if r.get('issue_severity') == 'MEDIUM']),
                    "low_severity": len([r for r in bandit_data.get('results', []) if r.get('issue_severity') == 'LOW']),
                    "total_issues": len(bandit_data.get('results', []))
                }
        except Exception as e:
            metrics["backend_security"] = {"error": str(e)}

        # Frontend security scan with npm audit
        try:
            audit_result = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True,
                text=True,
                cwd=self.frontend_path
            )

            if audit_result.stdout:
                audit_data = json.loads(audit_result.stdout)
                vulnerabilities = audit_data.get('metadata', {}).get('vulnerabilities', {})

                metrics["frontend_security"] = {
                    "critical": vulnerabilities.get('critical', 0),
                    "high": vulnerabilities.get('high', 0),
                    "moderate": vulnerabilities.get('moderate', 0),
                    "low": vulnerabilities.get('low', 0),
                    "total": vulnerabilities.get('total', 0)
                }
        except Exception as e:
            metrics["frontend_security"] = {"error": str(e)}

        return metrics

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance-related metrics"""

        # This would integrate with performance test results
        # For now, return placeholder data
        return {
            "api_response_time": {
                "average_ms": 150,
                "p95_ms": 300,
                "p99_ms": 500
            },
            "database_query_time": {
                "average_ms": 25,
                "slow_queries": 2
            },
            "frontend_load_time": {
                "first_contentful_paint_ms": 800,
                "largest_contentful_paint_ms": 1200
            }
        }

    def generate_quality_report(self, metrics: Dict[str, Any]) -> str:
        """Generate HTML quality report"""

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Construction Analysis - Quality Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .metric-card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 5px; }
                .metric-title { font-size: 18px; font-weight: bold; color: #333; }
                .metric-value { font-size: 24px; margin: 10px 0; }
                .status-clean { color: #28a745; }
                .status-warning { color: #ffc107; }
                .status-error { color: #dc3545; }
                .coverage-bar { background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden; }
                .coverage-fill { background: #28a745; height: 100%; transition: width 0.3s; }
            </style>
        </head>
        <body>
            <h1>Construction Analysis System - Quality Report</h1>
            <p>Generated on: {timestamp}</p>

            <h2>Backend Quality Metrics</h2>
            {backend_metrics}

            <h2>Frontend Quality Metrics</h2>
            {frontend_metrics}

            <h2>Security Metrics</h2>
            {security_metrics}

            <h2>Performance Metrics</h2>
            {performance_metrics}
        </body>
        </html>
        """

        # Format metrics sections (simplified implementation)
        backend_html = self._format_metrics_section(metrics.get("backend", {}))
        frontend_html = self._format_metrics_section(metrics.get("frontend", {}))
        security_html = self._format_metrics_section(metrics.get("security", {}))
        performance_html = self._format_metrics_section(metrics.get("performance", {}))

        return html_template.format(
            timestamp=metrics["timestamp"],
            backend_metrics=backend_html,
            frontend_metrics=frontend_html,
            security_metrics=security_html,
            performance_metrics=performance_html
        )

    def _format_metrics_section(self, section_metrics: Dict[str, Any]) -> str:
        """Format metrics section as HTML"""

        html = ""
        for metric_name, metric_data in section_metrics.items():
            if isinstance(metric_data, dict) and "error" not in metric_data:
                html += f"""
                <div class="metric-card">
                    <div class="metric-title">{metric_name.replace('_', ' ').title()}</div>
                    <div class="metric-details">
                        {self._format_metric_details(metric_data)}
                    </div>
                </div>
                """

        return html

    def _format_metric_details(self, metric_data: Dict[str, Any]) -> str:
        """Format individual metric details"""

        details = ""
        for key, value in metric_data.items():
            if isinstance(value, (int, float)):
                if key.endswith("_coverage") or key == "total_coverage":
                    details += f"""
                    <div>
                        <strong>{key.replace('_', ' ').title()}:</strong> {value:.1f}%
                        <div class="coverage-bar">
                            <div class="coverage-fill" style="width: {value}%"></div>
                        </div>
                    </div>
                    """
                else:
                    details += f"<div><strong>{key.replace('_', ' ').title()}:</strong> {value}</div>"
            else:
                details += f"<div><strong>{key.replace('_', ' ').title()}:</strong> {value}</div>"

        return details

# Usage
def run_quality_analysis():
    """Run comprehensive quality analysis"""

    collector = QualityMetricsCollector("/path/to/project")
    metrics = collector.collect_all_metrics()

    # Save metrics to JSON
    with open("quality_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Generate HTML report
    html_report = collector.generate_quality_report(metrics)
    with open("quality_report.html", "w") as f:
        f.write(html_report)

    print("Quality analysis complete!")
    print(f"Coverage: Backend {metrics['backend'].get('coverage', {}).get('total_coverage', 0):.1f}%")
    print(f"Coverage: Frontend {metrics['frontend'].get('coverage', {}).get('total_coverage', 0):.1f}%")

if __name__ == "__main__":
    run_quality_analysis()
```

This QA Agent provides comprehensive quality assurance guidance and implementation for the Construction Analysis AI System, covering testing strategy, automated testing, code quality analysis, performance testing, and quality metrics reporting.