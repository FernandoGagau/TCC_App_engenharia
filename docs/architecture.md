# Architecture

## System Overview
The Construction Analysis Agent System is an AI-powered platform that enables intelligent analysis and documentation of construction projects through conversational interfaces, automated visual inspection, and document processing. The system leverages multiple specialized AI agents coordinated by a supervisor to provide comprehensive construction project monitoring and reporting capabilities.

**Requirements**: Python 3.12+ is required for all backend services to ensure compatibility with the latest language features and performance improvements.

## Architecture Style
- **Pattern**: Microservices-oriented Monolith (Modular Monolith)
- **Approach**: Domain-Driven Design (DDD) with Clean Architecture principles
- **Communication**: REST API with WebSocket for real-time chat, Event-driven agent orchestration

## High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                           Client Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Web App     │  │  Mobile PWA  │  │  API Client  │             │
│  │  (React)     │  │   (React)    │  │  (External)  │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
└─────────┴──────────────────┴──────────────────┴────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   API Gateway    │
                    │   (FastAPI)      │
                    └────────┬────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                      Application Layer                              │
│  ┌────────────────────────────────────────────────────────┐       │
│  │               Supervisor Agent (LangGraph)              │       │
│  └──────────┬──────────┬──────────┬──────────┬───────────┘       │
│             │          │          │          │                    │
│  ┌──────────▼───┐ ┌───▼──────┐ ┌─▼──────┐ ┌▼──────────┐        │
│  │Visual Agent  │ │Document  │ │Progress│ │Report     │        │
│  │(OpenRouter) │ │Agent     │ │Agent   │ │Generator  │        │
│  └──────────────┘ └──────────┘ └────────┘ └───────────┘        │
└──────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                        Domain Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │  Project     │  │  Timeline    │  │  Location    │            │
│  │  Management  │  │  Tracking    │  │  Analysis    │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└──────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                    Infrastructure Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   MongoDB    │  │    MinIO     │  │  OpenRouter  │            │
│  │  (Metadata)  │  │  (Storage)   │  │  OpenRouter  │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

## Directory Structure
```
agente-engenharia/
├── backend/                    # Backend application
│   ├── src/                   # Source code
│   │   ├── agents/           # AI agents implementation
│   │   │   ├── interfaces/  # Agent contracts
│   │   │   ├── supervisor.py
│   │   │   ├── visual_agent.py
│   │   │   ├── document_agent.py
│   │   │   ├── progress_agent.py
│   │   │   └── report_agent.py
│   │   ├── application/      # Application services
│   │   │   └── services/    # Business services
│   │   ├── domain/          # Domain models and logic
│   │   │   ├── entities/   # Core entities
│   │   │   ├── events/     # Domain events
│   │   │   ├── exceptions/ # Domain exceptions
│   │   │   └── value_objects/
│   │   ├── infrastructure/  # Infrastructure services
│   │   │   ├── agents/     # Agent factory
│   │   │   ├── config/     # Configuration
│   │   │   ├── database/   # Database adapters
│   │   │   └── storage/    # File storage
│   │   └── presentation/   # API layer
│   │       └── api/        # API endpoints
│   ├── tests/              # Test suite
│   ├── scripts/            # Utility scripts
│   └── requirements.txt    # Python dependencies
├── frontend/               # Frontend application
│   ├── src/               # React source
│   │   ├── components/   # UI components
│   │   ├── services/     # API services
│   │   └── utils/        # Utilities
│   ├── public/           # Static assets
│   └── package.json      # Node dependencies
├── docs/                 # Documentation
├── docker-compose.yml    # Container orchestration
└── .env.example         # Environment template
```

## Core Components

### Component: Supervisor Agent
- **Purpose**: Orchestrates and coordinates all specialized agents
- **Responsibilities**:
  - Route user requests to appropriate agents
  - Manage agent workflow and state
  - Aggregate responses from multiple agents
  - Handle conversation context and memory
- **Interfaces**: LangGraph 0.6.7 StateGraph API with enhanced streaming
- **Dependencies**: LangChain 0.3.27, All specialized agents

### Component: Visual Analysis Agent
- **Purpose**: Analyzes construction site images using computer vision
- **Responsibilities**:
  - Process uploaded construction images
  - Identify construction elements and progress
  - Detect safety issues and compliance
  - Generate visual analysis reports
- **Interfaces**: OpenRouter (Gemini 2.5 Flash Image Preview)
- **Dependencies**: OpenRouter (Grok-4 Fast chat, Gemini 2.5 Flash visão), Image storage service

### Component: Document Processing Agent
- **Purpose**: Extracts and processes information from technical documents
- **Responsibilities**:
  - Parse PDF, DOCX, XLSX documents
  - Extract structured data from documents
  - Identify key project information
  - Cross-reference with project data
- **Interfaces**: Document parsing APIs
- **Dependencies**: PyPDF, python-docx, openpyxl

### Component: Progress Tracking Agent
- **Purpose**: Monitors and analyzes project progress
- **Responsibilities**:
  - Calculate completion percentages
  - Compare actual vs planned progress
  - Identify delays and bottlenecks
  - Generate progress predictions
- **Interfaces**: Timeline analysis API
- **Dependencies**: Project database, Timeline service

### Component: Report Generation Agent
- **Purpose**: Creates comprehensive project reports
- **Responsibilities**:
  - Aggregate data from all agents
  - Generate formatted reports (JSON, PDF)
  - Create executive summaries
  - Produce actionable insights
- **Interfaces**: Template engine, Export API
- **Dependencies**: All agent outputs, Jinja2

## Data Architecture

### Data Storage
| Store | Type | Purpose | Technology |
|-------|------|---------|------------|
| Primary | NoSQL | Project metadata, chat history | MongoDB |
| Object Storage | Blob | Images, documents, reports | MinIO |
| Cache | In-memory | Session data, temp results | Redis (optional) |
| Vector Store | Embeddings | Document search, RAG | ChromaDB (future) |

### Data Flow
1. User uploads image/document or sends chat message
2. API Gateway validates and routes request
3. Supervisor Agent determines workflow
4. Specialized agents process data in parallel/sequence
5. Results aggregated and stored in MongoDB
6. Files stored in MinIO with metadata reference
7. Response returned to user via WebSocket/REST

## API Design

### Endpoints Structure
- **Pattern**: RESTful with WebSocket for real-time
- **Versioning**: URL path versioning (/api/v1/)
- **Authentication**: JWT tokens (future)
- **Rate Limiting**: Token-based quotas

### Key APIs
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/v1/chat | POST | Send message to agents |
| /api/v1/chat/stream | WS | Real-time chat stream |
| /api/v1/projects | GET/POST | Manage projects |
| /api/v1/projects/{id} | GET/PUT/DELETE | Project operations |
| /api/v1/analysis/visual | POST | Submit image for analysis |
| /api/v1/analysis/document | POST | Submit document for processing |
| /api/v1/reports/{id} | GET | Retrieve generated reports |
| /api/v1/timeline/{project_id} | GET | Get project timeline |

## Security Architecture

### Security Layers
1. **Network**: HTTPS/TLS encryption, CORS configuration
2. **Application**: JWT authentication, Role-based access
3. **Data**: Encryption at rest (MinIO), Encrypted connections
4. **Monitoring**: Request logging, Error tracking

### Security Measures
- Authentication: JWT tokens with refresh mechanism
- Authorization: Role-based access control (RBAC)
- Encryption: TLS 1.3 for transport, AES-256 for storage
- Input Validation: Pydantic models, file type verification
- API Key Management: Secure storage in environment variables

## Integration Architecture

### External Systems
| System | Protocol | Purpose | Fallback |
|--------|----------|---------|----------|
| OpenRouter API | HTTPS/REST | Grok-4 Fast chat & Gemini 2.5 Flash visão | Primary channel |
| MinIO | S3-compatible | File storage | Local filesystem |
| MongoDB Atlas | MongoDB Protocol | Cloud database | Local MongoDB |

## Performance Architecture

### Optimization Strategies
- **Caching**: Agent response caching, Image analysis results
- **Load Balancing**: Nginx reverse proxy (production)
- **Database**: Indexed queries, connection pooling
- **Async Processing**: FastAPI async endpoints, Background tasks

### Scalability Plan
- **Horizontal**: Container orchestration with Kubernetes
- **Vertical**: Resource limits per container
- **Data**: MongoDB sharding, MinIO distributed mode

## Deployment Architecture

### Environment Strategy
| Environment | Purpose | Configuration |
|-------------|---------|---------------|
| Development | Local development | Docker Compose, local services |
| Staging | Testing & validation | Railway/Render deployment |
| Production | Live system | Cloud deployment (AWS/GCP) |

### Infrastructure
- **Platform**: Railway (current), AWS/GCP (future)
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions for automated deployment
- **Monitoring**: Prometheus + Grafana (future)

## Technology Stack

### Core Technologies
| Layer | Technology | Justification |
|-------|------------|---------------|
| Frontend | React 18 + Material UI | Modern UI, component ecosystem |
| Backend | Python 3.12 + FastAPI | Async support, AI libraries |
| AI/ML | LangChain 0.3.27 + LangGraph 0.6.7 | Enhanced agent orchestration, production-ready features |
| Database | MongoDB 7.0 | Flexible schema, document store |
| Object Storage | MinIO | S3-compatible, self-hosted |
| Real-time | WebSocket | Streaming chat responses |

## Design Decisions (ADRs)

### ADR-001: Multi-Agent Architecture
- **Status**: Accepted
- **Context**: Need for specialized analysis across different domains
- **Decision**: Implement supervisor pattern with specialized agents using LangGraph 0.6.7
- **Consequences**: Better modularity, easier scaling, production-ready orchestration with enhanced streaming

### ADR-002: MongoDB for Primary Storage
- **Status**: Accepted
- **Context**: Variable project structures and evolving schema
- **Decision**: Use MongoDB for flexibility and JSON-native storage
- **Consequences**: Schema flexibility, eventual consistency considerations

### ADR-003: OpenRouter Integration
- **Status**: Accepted
- **Context**: Cost optimization and model diversity needs
- **Decision**: OpenRouter centraliza roteamento para Grok-4 Fast e Gemini 2.5 Flash
- **Consequences**: Better cost control, model selection flexibility

### ADR-004: MinIO for Object Storage
- **Status**: Accepted
- **Context**: Need for scalable file storage with S3 compatibility
- **Decision**: Use MinIO for self-hosted object storage
- **Consequences**: S3-compatible APIs, easy cloud migration path

## Quality Attributes

### Performance Requirements
- Response Time: < 3000ms for chat responses
- Image Analysis: < 10 seconds per image
- Document Processing: < 5 seconds per page
- Concurrent Users: 100+ simultaneous

### Reliability Requirements
- Uptime: 99.5% availability
- Recovery Time: < 5 minutes
- Data Loss: Zero tolerance for project data
- Error Rate: < 1% for API calls

### Scalability Requirements
- Projects: Support 1000+ active projects
- Storage: 100GB+ file storage capacity
- Messages: 10,000+ messages per day
- Growth: 10x user base within 6 months