# Prompt: Evoluir API de Chat com Persistência e Streaming

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, ai-agents, websocket, database).
- Referências úteis: docs/backend.md, docs/ai-agents.md, docs/websocket.md (se existir), agents/backend-development.md, agents/ai-agent-development.md, agents/security-check.md.

Objetivo
- Transformar a API de chat do MVP em fluxo completo com persistência, rate limiting e streaming.
- Remover dependências in-memory (`ChatService.sessions`) e armazenar sessões/mensagens no MongoDB.
- Corrigir inicialização de WebSocket para injetar serviços configurados (sem `ChatService()` vazio) e alinhar com pipelines de streaming.

Escopo
- Refatorar `backend/src/application/services/chat_service.py` aplicando SOLID (SRP, DIP) e extraindo componentes: gerenciador de sessão, persistência e pipeline de resposta.
- Criar camada de repositório (`ChatSessionRepository`, `ChatMessageRepository`) reutilizável por HTTP e WebSocket.
- Ajustar `backend/src/presentation/api/websocket.py` para receber dependências via `Depends`/container, habilitando streaming chunked e rate limiting configurável.
- Atualizar rotas REST (`backend/src/presentation/api/v1/chat.py`) para consumir novo serviço com persistência e devolver histórico durável.
- Implementar pipeline de streaming (ex.: generator async) para respostas do agente, reutilizando LLM stream ou fallback.
- Garantir logging estruturado, tratamento `try/except` localizado e respostas consistentes.

Requisitos de Configuração
- Validar coleções MongoDB para sessões/mensagens (`SessionModel`, `MessageModel`) existentes em `infrastructure/database/models.py`.
- Confirmar variáveis de ambiente para Redis (rate limiting) e WebSocket (`REDIS_URL`, `WEBSOCKET_MAX_CONNECTIONS`).
- Ajustar settings/DI para injetar `ChatService` configurado na inicialização (`backend/main.py`).

Arquitetura de Alto Nível
- `ChatService` orquestra: recebe repositórios + agentes; expõe métodos `create_session`, `append_message`, `stream_response`.
- Repositórios Mongo implementam interface (DIP), convertendo entre documentos e entidades domain (`ChatSession`, `ChatMessage`).
- WebSocket handler usa `ChatStreamPipeline` para stream incremental (server-sent chunks) e atualização de histórico.
- Rate limiting centralizado (`RateLimiter`, `MessageRateLimiter`) reutilizado por HTTP e WS.

Princípios e Boas Práticas
- Aplicar TRY de forma pontual (I/O e streaming) com logs contextualizados (`logger.bind(session_id=...)`).
- Seguir SOLID: classes menores (<200 linhas), métodos coesos; evitar estado global.
- Garantir idempotência no reenvio de mensagens (deduplicação via message_id).
- Validar entradas com Pydantic e normalizar erros (HTTP 4xx/5xx consistentes).

Testes (Manual & Automatizados)
- Unitários: `tests/unit/test_chat_service.py` cobrindo criação, persistência, streaming e falhas.
- Integração: `tests/integration/test_chat_routes.py`, `tests/integration/test_websocket_chat.py` simulando fluxo real.
- QA Manual: iniciar chat via HTTP, continuar via WebSocket, verificar histórico salvo e rate limiting.

Entregáveis do PR
- Refatoração completa do `ChatService`, novos repositórios e ajustes em rotas/WS.
- Testes automatizados executados (`pytest`, `pytest -k chat`, etc.).
- Atualização de documentação (`docs/backend.md`, `docs/ai-agents.md`) descrevendo fluxo persistente e streaming.
- Registro em CHANGELOG ou release notes informando quebra de compatibilidade (se endpoints mudarem).

Notas
- Coordenar com tasks de persistência Mongo/ProjectRepository para reaproveitar padrões de repositório.
- Verificar impacto em dashboards (token tracker, analytics) que dependem do fluxo atual.
- Considerar feature flags para liberar streaming gradualmente (opcional).
