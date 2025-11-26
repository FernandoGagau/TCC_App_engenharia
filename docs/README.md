# Documentation Index

Central documentation hub for the Construction Analysis AI System. This index provides organized access to all project documentation.

## Quick Start
- **New to the project?** Start with [Architecture](architecture.md)
- **Setting up development?** See [Development Guidelines](development-guidelines.md)
- **Building features?** Check the [Agents Guide](../AGENTS.md)

## System Overview
The Construction Analysis AI System is a multi-agent platform for intelligent analysis and documentation of construction projects.

### Core Technologies
- **Backend**: Python 3.12 + FastAPI + LangGraph/LangChain
- **Frontend**: React 18 + Material UI
- **Database**: MongoDB + MinIO
- **AI**: OpenRouter (Grok-4 Fast + Gemini 2.5 Flash)

## Documentation Structure

### Architecture & Design
- [Architecture](architecture.md) — System design, components, and technology decisions
- [Development Guidelines](development-guidelines.md) — Coding standards and best practices

### Frontend Development
- [Frontend Guide](frontend.md) — React setup, structure, and patterns
- [Components](components.md) — Reusable UI components and design system

### Backend Development
- [Backend Guide](backend.md) — FastAPI, domain design, and services
- [API Documentation](api.md) — REST endpoints and WebSocket patterns

### AI & Intelligence
- [AI Agents](ai-agents.md) — Agent architecture, LangGraph workflows
- [Agent Development](ai-agent-development.md) — Building and testing agents

### Data & Storage
- [Database](database.md) — MongoDB schemas and data patterns

### Operations
- [Authentication](authentication.md) — Security and user management
- [Testing](testing.md) — Testing strategies and quality assurance

## Development Workflow

### For New Features
1. Review [Architecture](architecture.md) for system understanding
2. Follow [Development Guidelines](development-guidelines.md) for coding standards
3. Use appropriate guides: [Frontend](frontend.md), [Backend](backend.md), or [AI Agents](ai-agents.md)
4. Implement with [Testing](testing.md) practices

### For Agent Development
1. Read [AI Agents](ai-agents.md) for agent patterns
2. Follow [AI Agent Development](ai-agent-development.md) for implementation
3. Test using [Testing](testing.md) guidelines

### For API Changes
1. Review [API Documentation](api.md)
2. Follow [Backend Guide](backend.md) patterns
3. Update [Authentication](authentication.md) if needed

## Project Structure Reference
```
agente-engenharia/
├── backend/                 # Python FastAPI backend
│   ├── src/                # Source code
│   │   ├── agents/        # AI agents (LangGraph)
│   │   ├── application/   # Application services
│   │   ├── domain/        # Domain models and logic
│   │   ├── infrastructure/# External integrations
│   │   └── presentation/  # API endpoints
│   └── requirements.txt   # Python dependencies
├── frontend/              # React frontend
│   ├── src/              # React source code
│   │   ├── components/   # UI components
│   │   └── App.js        # Main application
│   └── package.json      # Node dependencies
├── docs/                 # Documentation
├── agents/               # Agent development guides
└── docker-compose.yml    # Container orchestration
```

## Getting Help
- **Architecture questions**: See [Architecture](architecture.md)
- **Development issues**: Check [Development Guidelines](development-guidelines.md)
- **Agent development**: Review [AI Agents](ai-agents.md)
- **API usage**: Consult [API Documentation](api.md)

## Contributing
1. Read relevant documentation section
2. Follow [Development Guidelines](development-guidelines.md)
3. Use appropriate agent guides from [Agents Guide](../AGENTS.md)
4. Write tests according to [Testing](testing.md)

For quick navigation and task-specific guidance, always refer to the [Agents Guide](../AGENTS.md).