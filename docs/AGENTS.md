# Agents Guide

This file is a navigation hub for agents working in this Construction Analysis AI project. It avoids duplicating content and points you to the authoritative docs and guides.

## Start Here
- [docs/README.md](docs/README.md) — Central documentation index: architecture, backend/frontend, API, database, AI agent workflows
- [agents/README.md](agents/README.md) — Agent guides index with checklists and PR deliverables (security, frontend, backend, database, planning, QA)

## Purpose & Scope
- Use this file to quickly find the right guide or reference.
- All detailed standards live under `docs/` and actionable playbooks under `agents/`.
- Scope: applies to the entire repository for Construction Analysis AI System.

## Key References (authoritative)
- Architecture: [docs/architecture.md](docs/architecture.md)
- Development Guidelines: [docs/development-guidelines.md](docs/development-guidelines.md)
- Frontend: [docs/frontend.md](docs/frontend.md), [docs/components.md](docs/components.md)
- Backend & API: [docs/backend.md](docs/backend.md), [docs/api.md](docs/api.md)
- AI Agents: [docs/ai-agents.md](docs/ai-agents.md)
- Database & MongoDB: [docs/database.md](docs/database.md)
- Authentication: [docs/authentication.md](docs/authentication.md)
- Testing Guide: [docs/testing.md](docs/testing.md)

## Common Tasks → Guides
- Plan a feature: [agents/architecture-planning.md](agents/architecture-planning.md)
- Build frontend UI: [agents/frontend-development.md](agents/frontend-development.md)
- Implement API/backend: [agents/backend-development.md](agents/backend-development.md)
- Develop AI agents: [agents/ai-agent-development.md](agents/ai-agent-development.md)
- Evolve database schema: [agents/database-development.md](agents/database-development.md)
- Security review checklist: [agents/security-check.md](agents/security-check.md)
- QA workflow: [agents/qa-agent.md](agents/qa-agent.md)

## Essentials (quick reminders)
- Backend structure: Python 3.12 + FastAPI with Domain-Driven Design (DDD) under `backend/src/`
- Frontend structure: React 18 + Material UI under `frontend/src/`
- AI Agents: LangGraph 0.6.7 + LangChain 0.3.27 with OpenRouter integration (Grok-4 Fast + Gemini 2.5 Flash)
- Database: MongoDB for metadata, MinIO for object storage
- API pattern: RESTful with WebSocket for real-time chat streams

## Project Map (for orientation)
### Frontend Structure (`frontend/`)
- React App: `src/App.js`
- Components: `src/components/`
- Static assets: `public/`
- Dependencies: `package.json`

### Backend Structure (`backend/`)
- Source code: `src/`
  - AI Agents: `src/agents/` (Supervisor, Visual, Document, Progress, Report)
  - Application Layer: `src/application/`
  - Domain Layer: `src/domain/`
  - Infrastructure: `src/infrastructure/`
  - API Presentation: `src/presentation/`
- Main entry: `main.py`
- Dependencies: `requirements.txt`

### Documentation (`docs/`)
- Architecture and system design
- Development guidelines and standards
- API documentation
- AI agent specifications

For setup, scripts, and workflows, follow [docs/README.md](docs/README.md).