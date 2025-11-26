# API Documentation

This document provides comprehensive API documentation for the Construction Analysis AI System REST API and WebSocket endpoints.

## API Overview

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

### API Version
All endpoints are prefixed with `/api/v1`

### Authentication
Currently, the API operates without authentication for development. JWT authentication will be implemented in future versions.

### Response Format
All API responses follow a consistent JSON structure:

```json
{
  "data": {},
  "message": "Success",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Responses
Error responses include detailed information:

```json
{
  "detail": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Projects API

### Create Project
Create a new construction project.

**Endpoint**: `POST /api/v1/projects`

**Request Body**:
```json
{
  "name": "Office Building Construction",
  "description": "Modern office building with 10 floors",
  "location": "123 Main St, City, State"
}
```

**Response**: `201 Created`
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Office Building Construction",
  "description": "Modern office building with 10 floors",
  "location": "123 Main St, City, State",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### List Projects
Retrieve a list of construction projects.

**Endpoint**: `GET /api/v1/projects`

**Query Parameters**:
- `status` (optional): Filter by status (`active`, `completed`, `suspended`, `cancelled`)
- `limit` (optional): Number of results to return (default: 100, max: 1000)
- `offset` (optional): Number of results to skip (default: 0)

**Response**: `200 OK`
```json
{
  "projects": [
    {
      "id": "507f1f77bcf86cd799439011",
      "name": "Office Building Construction",
      "description": "Modern office building with 10 floors",
      "location": "123 Main St, City, State",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Get Project
Retrieve a specific project by ID.

**Endpoint**: `GET /api/v1/projects/{project_id}`

**Path Parameters**:
- `project_id`: MongoDB ObjectId of the project

**Response**: `200 OK`
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Office Building Construction",
  "description": "Modern office building with 10 floors",
  "location": "123 Main St, City, State",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update Project
Update an existing project.

**Endpoint**: `PUT /api/v1/projects/{project_id}`

**Request Body**:
```json
{
  "name": "Updated Office Building",
  "description": "Updated description",
  "location": "New location",
  "status": "active"
}
```

**Response**: `200 OK`
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Updated Office Building",
  "description": "Updated description",
  "location": "New location",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Delete Project
Delete a project and all associated data.

**Endpoint**: `DELETE /api/v1/projects/{project_id}`

**Response**: `204 No Content`

## Analysis API

### Visual Analysis
Submit an image for AI-powered visual analysis.

**Endpoint**: `POST /api/v1/analysis/visual`

**Request**: Multipart form data
- `file`: Image file (JPEG, PNG, max 10MB)
- `project_id` (optional): Associate analysis with a project

**Response**: `200 OK`
```json
{
  "analysis_id": "507f1f77bcf86cd799439012",
  "progress_percentage": 75.5,
  "detected_elements": [
    "foundation",
    "walls",
    "roof_structure"
  ],
  "safety_issues": [
    "Scaffolding appears unstable",
    "Workers without hard hats visible"
  ],
  "quality_observations": [
    "Concrete surface appears smooth and well-finished",
    "Structural alignment looks proper"
  ],
  "confidence_score": 0.85,
  "processing_time": 2.3,
  "recommendations": [
    "Install additional scaffolding supports",
    "Ensure all workers wear proper PPE"
  ],
  "metadata": {
    "image_dimensions": "1920x1080",
    "file_size": 2048576,
    "analysis_timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Document Processing
Submit a document for AI-powered information extraction.

**Endpoint**: `POST /api/v1/analysis/document`

**Request**: Multipart form data
- `file`: Document file (PDF, DOCX, XLSX, max 10MB)
- `project_id` (optional): Associate analysis with a project

**Response**: `200 OK`
```json
{
  "analysis_id": "507f1f77bcf86cd799439013",
  "document_type": "pdf",
  "extracted_data": {
    "title": "Construction Plans - Phase 1",
    "dates": ["2024-01-15", "2024-06-30"],
    "key_specifications": {
      "building_height": "10 floors",
      "total_area": "50,000 sq ft",
      "materials": ["concrete", "steel", "glass"]
    },
    "compliance_items": [
      "Building code section 12.3.4 - Fire safety",
      "ADA compliance requirements"
    ]
  },
  "processing_time": 5.2,
  "confidence_score": 0.92,
  "page_count": 45
}
```

### Batch Analysis
Submit multiple files for analysis in a single request.

**Endpoint**: `POST /api/v1/analysis/batch`

**Request**: Multipart form data
- `files`: Multiple files (images and documents)
- `project_id`: Project to associate analyses with

**Response**: `202 Accepted`
```json
{
  "batch_id": "507f1f77bcf86cd799439014",
  "status": "processing",
  "total_files": 5,
  "estimated_completion": "2024-01-01T00:10:00Z"
}
```

## Reports API

### Generate Report
Generate a comprehensive project report.

**Endpoint**: `POST /api/v1/reports`

**Request Body**:
```json
{
  "project_id": "507f1f77bcf86cd799439011",
  "report_type": "progress",
  "include_sections": [
    "summary",
    "visual_analysis",
    "progress_tracking",
    "recommendations"
  ],
  "format": "json"
}
```

**Response**: `201 Created`
```json
{
  "report_id": "507f1f77bcf86cd799439015",
  "status": "generating",
  "estimated_completion": "2024-01-01T00:05:00Z",
  "download_url": "/api/v1/reports/507f1f77bcf86cd799439015/download"
}
```

### Get Report
Retrieve a generated report.

**Endpoint**: `GET /api/v1/reports/{report_id}`

**Response**: `200 OK`
```json
{
  "report_id": "507f1f77bcf86cd799439015",
  "project_id": "507f1f77bcf86cd799439011",
  "report_type": "progress",
  "status": "completed",
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:00Z",
  "data": {
    "summary": {
      "overall_progress": 75.5,
      "project_status": "on_track",
      "completion_estimate": "2024-06-30"
    },
    "visual_analysis": {
      "total_images_analyzed": 25,
      "average_progress": 75.5,
      "trend": "increasing"
    },
    "recommendations": [
      "Focus on roof construction to maintain schedule",
      "Address safety concerns in scaffolding area"
    ]
  }
}
```

### Download Report
Download a report in the specified format.

**Endpoint**: `GET /api/v1/reports/{report_id}/download`

**Query Parameters**:
- `format` (optional): `json`, `pdf`, `excel` (default: original format)

**Response**: File download with appropriate Content-Type

## Timeline API

### Get Project Timeline
Retrieve project timeline and milestones.

**Endpoint**: `GET /api/v1/timeline/{project_id}`

**Response**: `200 OK`
```json
{
  "project_id": "507f1f77bcf86cd799439011",
  "timeline": [
    {
      "phase": "foundation",
      "start_date": "2024-01-01",
      "end_date": "2024-02-15",
      "status": "completed",
      "progress": 100
    },
    {
      "phase": "framing",
      "start_date": "2024-02-16",
      "end_date": "2024-04-30",
      "status": "in_progress",
      "progress": 60
    },
    {
      "phase": "roofing",
      "start_date": "2024-05-01",
      "end_date": "2024-05-31",
      "status": "planned",
      "progress": 0
    }
  ],
  "overall_progress": 55.5,
  "projected_completion": "2024-06-30"
}
```

### Update Timeline
Update project timeline milestones.

**Endpoint**: `PUT /api/v1/timeline/{project_id}`

**Request Body**:
```json
{
  "milestones": [
    {
      "phase": "framing",
      "progress": 75,
      "notes": "Ahead of schedule due to good weather"
    }
  ]
}
```

## WebSocket API

### Real-time Chat
Connect to the AI assistant for real-time conversation.

**Endpoint**: `WS /api/v1/chat/{session_id}`

**Connection Parameters**:
- `session_id`: Unique session identifier
- `project_id` (optional): Associate chat with a project

**Message Format**:
```json
{
  "type": "message",
  "content": "Analyze the latest uploaded image",
  "project_id": "507f1f77bcf86cd799439011",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Response Format**:
```json
{
  "type": "response",
  "content": "I've analyzed the image and found 75% completion...",
  "agent": "supervisor",
  "confidence": 0.85,
  "timestamp": "2024-01-01T00:00:05Z",
  "metadata": {
    "processing_time": 2.3,
    "agents_used": ["visual_analysis", "progress_tracking"]
  }
}
```

**Special Message Types**:

**File Upload**:
```json
{
  "type": "file_upload",
  "file_info": {
    "name": "construction_photo.jpg",
    "size": 2048576,
    "type": "image/jpeg"
  },
  "content": "Please analyze this construction photo"
}
```

**Status Update**:
```json
{
  "type": "status",
  "status": "processing",
  "message": "Analyzing uploaded image..."
}
```

**Error Message**:
```json
{
  "type": "error",
  "error_code": "PROCESSING_FAILED",
  "message": "Failed to process image",
  "details": "Image format not supported"
}
```

## Health and Status

### Health Check
Check API health and status.

**Endpoint**: `GET /health`

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "database": "connected",
    "storage": "connected",
    "ai_agents": "ready"
  }
}
```

### System Status
Get detailed system status information.

**Endpoint**: `GET /api/v1/status`

**Response**: `200 OK`
```json
{
  "system": {
    "uptime": 86400,
    "memory_usage": "2.5GB",
    "cpu_usage": "15%"
  },
  "services": {
    "mongodb": {
      "status": "connected",
      "response_time": "5ms"
    },
    "minio": {
      "status": "connected",
      "response_time": "12ms"
    },
    "openrouter": {
      "status": "connected",
      "response_time": "250ms"
    }
  },
  "agents": {
    "supervisor": "ready",
    "visual_analysis": "ready",
    "document_processing": "ready",
    "progress_tracking": "ready",
    "report_generation": "ready"
  }
}
```

## Error Codes

### HTTP Status Codes
- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `202 Accepted`: Request accepted for processing
- `204 No Content`: Successful request with no content
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Application Error Codes
- `PROJECT_NOT_FOUND`: Project does not exist
- `INVALID_FILE_FORMAT`: Unsupported file format
- `FILE_TOO_LARGE`: File exceeds size limit
- `PROCESSING_FAILED`: AI agent processing failed
- `ANALYSIS_ERROR`: Error during analysis
- `REPORT_GENERATION_FAILED`: Report generation failed
- `INVALID_PROJECT_STATUS`: Invalid status transition
- `DATABASE_ERROR`: Database operation failed
- `STORAGE_ERROR`: File storage operation failed

## Rate Limiting

### Limits
- **General API**: 1000 requests per hour per IP
- **File Upload**: 100 uploads per hour per IP
- **WebSocket**: 10 concurrent connections per IP
- **Report Generation**: 10 reports per hour per IP

### Headers
Rate limit information is included in response headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641024000
```

## Authentication (Future)

### JWT Token
When authentication is implemented, include JWT token in headers:
```
Authorization: Bearer <jwt_token>
```

### Token Endpoints
- `POST /api/v1/auth/login`: Authenticate and receive token
- `POST /api/v1/auth/refresh`: Refresh expired token
- `POST /api/v1/auth/logout`: Invalidate token

## SDK and Examples

### Python SDK Example
```python
import aiohttp
import asyncio

class ConstructionAI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    async def create_project(self, name, location, description=None):
        async with aiohttp.ClientSession() as session:
            data = {
                "name": name,
                "location": location,
                "description": description
            }
            async with session.post(
                f"{self.base_url}/api/v1/projects",
                json=data
            ) as response:
                return await response.json()

    async def analyze_image(self, image_path, project_id=None):
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('file', open(image_path, 'rb'))
            if project_id:
                data.add_field('project_id', project_id)

            async with session.post(
                f"{self.base_url}/api/v1/analysis/visual",
                data=data
            ) as response:
                return await response.json()

# Usage
async def main():
    ai = ConstructionAI()

    # Create project
    project = await ai.create_project(
        name="My Building",
        location="123 Main St"
    )

    # Analyze image
    result = await ai.analyze_image(
        "construction_photo.jpg",
        project_id=project["id"]
    )

    print(f"Progress: {result['progress_percentage']}%")

asyncio.run(main())
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class ConstructionAI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async createProject(name, location, description = null) {
        const response = await axios.post(`${this.baseUrl}/api/v1/projects`, {
            name,
            location,
            description
        });
        return response.data;
    }

    async analyzeImage(imagePath, projectId = null) {
        const form = new FormData();
        form.append('file', fs.createReadStream(imagePath));
        if (projectId) {
            form.append('project_id', projectId);
        }

        const response = await axios.post(
            `${this.baseUrl}/api/v1/analysis/visual`,
            form,
            { headers: form.getHeaders() }
        );
        return response.data;
    }
}

// Usage
(async () => {
    const ai = new ConstructionAI();

    // Create project
    const project = await ai.createProject(
        'My Building',
        '123 Main St'
    );

    // Analyze image
    const result = await ai.analyzeImage(
        'construction_photo.jpg',
        project.id
    );

    console.log(`Progress: ${result.progress_percentage}%`);
})();
```

This API documentation provides comprehensive coverage of all endpoints, request/response formats, error handling, and practical examples for integrating with the Construction Analysis AI System.