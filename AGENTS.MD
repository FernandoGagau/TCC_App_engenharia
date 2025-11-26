# Agents Guide

This file is a navigation hub for agents working in this repository. It avoids duplicating content and points you to the authoritative docs and guides.

## Start Here
- [README.md](README.md) for the top-level summary and environment setup
- [docs/README.md](docs/README.md) for the documentation index and technology stack
- [agents/README.md](agents/README.md) for agent roles, capabilities, and workflow
- [docs/context.md](docs/context.md) for project background, personas, and problem framing

## Purpose & Scope
- Use this file to quickly route to the right reference before deep-diving a task
- Detailed standards, checklists, and research notes live in `docs/`
- Actionable playbooks and delivery checklists live in `agents/`
- Scope covers backend, frontend, AI agents, data, deployment, and operations

## Key References (authoritative)
- **System overview**: [docs/architecture.md](docs/architecture.md), [docs/context.md](docs/context.md)
- **Implementation standards**: [docs/development-guidelines.md](docs/development-guidelines.md), [docs/testing.md](docs/testing.md)
- **Backend & API**: [docs/backend.md](docs/backend.md), [docs/api.md](docs/api.md), [docs/authentication.md](docs/authentication.md)
- **Frontend**: [docs/frontend.md](docs/frontend.md), [docs/components.md](docs/components.md)
- **Data & storage**: [docs/database.md](docs/database.md), [docs/demandas/task-22-mongodb-persistence-refactor.md](docs/demandas/task-22-mongodb-persistence-refactor.md)
- **AI strategy**: [docs/ai-agents.md](docs/ai-agents.md), [docs/research.md](docs/research.md)

## Common Tasks → Guides
- Plan cross-cutting features with [agents/architecture-planning.md](agents/architecture-planning.md)
- Ship React UI work with [agents/frontend-development.md](agents/frontend-development.md)
- Deliver FastAPI services via [agents/backend-development.md](agents/backend-development.md)
- Build or extend LangGraph workflows using [agents/ai-agent-development.md](agents/ai-agent-development.md)
- Adjust data models following [agents/database-development.md](agents/database-development.md)
- Secure releases and QA with [agents/security-check.md](agents/security-check.md) and [agents/qa-agent.md](agents/qa-agent.md)

## Planning & Roadmaps
- Align on milestones with [docs/CRONOGRAMA-FLUXO.md](docs/CRONOGRAMA-FLUXO.md)
- Track execution using [docs/plan.md](docs/plan.md) and [docs/PROGRESSO-DUPLO.md](docs/PROGRESSO-DUPLO.md)
- Review current backlog in [docs/demandas/tasks.md](docs/demandas/tasks.md) and task breakdowns under `docs/demandas/`
- Capture lessons learned from [docs/qa_review_report.md](docs/qa_review_report.md)

## AI Stack & Integrations
- LangChain references: [docs/langchain/langchain_v0.3.27_docs.md](docs/langchain/langchain_v0.3.27_docs.md), [docs/langchain/llms.md](docs/langchain/llms.md)
- LangGraph workflows: [docs/langgraph/langgraph_v0.6.7_docs.md](docs/langgraph/langgraph_v0.6.7_docs.md), [docs/langgraph/llms-full.md](docs/langgraph/llms-full.md)
- OpenRouter integration: [docs/open_router/open_router_overview.md](docs/open_router/open_router_overview.md), [docs/open_router/api.md](docs/open_router/api.md)
- Runtime notes: [docs/phython/3_12.md](docs/phython/3_12.md), [docs/DIAGNÓSTICO_CHAT.md](docs/DIAGNÓSTICO_CHAT.md)

## Operations & Deployment
- Deploy procedures: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [docs/DEPLOY_SUMMARY.md](docs/DEPLOY_SUMMARY.md)
- Railway setup: [docs/RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md), [docs/RAILWAY_ARCHITECTURE_OPTIONS.md](docs/RAILWAY_ARCHITECTURE_OPTIONS.md)
- Environment configuration: [docs/RAILWAY_CHECKLIST.md](docs/RAILWAY_CHECKLIST.md), [RAILWAY_CONFIG.md](RAILWAY_CONFIG.md)
- Automation scripts: [start.sh](start.sh), [docs/docker-compose.yml](docs/docker-compose.yml)

## Domain Knowledge & Reports
- Chat and document diagnostics: [docs/DIAGNÓSTICO_CHAT.md](docs/DIAGNÓSTICO_CHAT.md), [docs/PROGRESSO-ANALISE-IMAGENS.md](docs/PROGRESSO-ANALISE-IMAGENS.md)
- Progress and reporting agents: [docs/PROGRESSO-DUPLO.md](docs/PROGRESSO-DUPLO.md), [docs/demandas/task-23-progress-agent-repo-injection.md](docs/demandas/task-23-progress-agent-repo-injection.md), [docs/demandas/task-24-report-agent-repo-injection.md](docs/demandas/task-24-report-agent-repo-injection.md)
- Research dossiers: [docs/research.md](docs/research.md), [docs/089_ISARC_2024_Paper_124.pdf](docs/089_ISARC_2024_Paper_124.pdf)
- Historical deliverables: [docs/DEPLOY_SUMMARY.md](docs/DEPLOY_SUMMARY.md), [docs/qa_review_report.md](docs/qa_review_report.md)

## Essentials (quick reminders)
- Backend uses Python 3.12, FastAPI, and DDD structures documented in [docs/backend.md](docs/backend.md)
- Frontend runs React 18 with Material UI conventions in [docs/frontend.md](docs/frontend.md)
- AI agents orchestrate via LangGraph per [docs/ai-agents.md](docs/ai-agents.md) and agent guides
- Persistence relies on MongoDB plus MinIO guidelines in [docs/database.md](docs/database.md)
- Enforce coding standards from [docs/development-guidelines.md](docs/development-guidelines.md) before each PR

## Project Map (for orientation)
- `backend/` — FastAPI services, LangGraph agents, domain and infrastructure layers
- `frontend/` — React app, components, services, and page flows
- `agents/` — Delivery playbooks for planning, frontend, backend, AI, database, QA, and security
- `docs/` — Architecture, operations, research, and task specifications including `docs/demandas/`
- `start.sh` & `docs/docker-compose.yml` — Local orchestration entry points

```
agente-engenharia/
├── backend/
├── frontend/
├── agents/
├── docs/
└── start.sh
```

## Archives & Legacy
- Versioned references under [docs/v1/](docs/v1/) for the MVP baseline
- Early architecture explorations in [docs/v1/architecture/](docs/v1/architecture/)
- Historical agent docs in [docs/v1/agents/](docs/v1/agents/)
- Supporting presentations: [docs/v1/TCC_Apresentacao_Projeto.md](docs/v1/TCC_Apresentacao_Projeto.md), [docs/v1/TCC_Tecnologias_Frameworks.md](docs/v1/TCC_Tecnologias_Frameworks.md)
