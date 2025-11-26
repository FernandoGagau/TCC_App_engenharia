# Prompt: Registrar WebSocket Endpoints no Backend

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, database, auth).
- Siga os guias: agents/backend-development.md, agents/api.md.

Objetivo
- Integrar os endpoints WebSocket e REST criados ao arquivo main.py do backend.
- Configurar middleware de CORS para WebSocket e inicialização do Redis.
- Garantir que os endpoints estejam funcionais e acessíveis.

Escopo
- Registro de routers: importar e incluir routers WebSocket e REST no FastAPI.
- Configuração de eventos: startup e shutdown para inicialização de serviços.
- Middleware: configuração adequada de CORS para WebSocket.
- Health check: endpoint para verificar status do WebSocket.

Requisitos de Configuração
- Variáveis de ambiente:
  - REDIS_URL=redis://localhost:6379
  - WEBSOCKET_MAX_CONNECTIONS=100
  - WEBSOCKET_TIMEOUT=300
  - RATE_LIMIT_MESSAGES_PER_MINUTE=30
- Dependências já instaladas: websockets, python-socketio, slowapi, redis

Arquitetura de Alto Nível
- Main App: FastAPI com suporte a WebSocket
- Routers: WebSocket endpoint + REST API para chat
- Redis: conexão para rate limiting e session state
- Startup/Shutdown: inicialização e limpeza de recursos

Implementação no main.py
```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import WebSocket components
from src.presentation.api.websocket import (
    router as ws_router,
    api_router as chat_api_router,
    startup_event,
    shutdown_event
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()

app = FastAPI(
    title="Construction Analysis API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ws_router)
app.include_router(chat_api_router)

# Health check endpoint
@app.get("/health/websocket")
async def websocket_health():
    """Check WebSocket service health."""
    return {
        "status": "healthy",
        "service": "websocket",
        "timestamp": datetime.utcnow().isoformat()
    }
```

Configuração do Docker Compose
```yaml
# docker-compose.yml addition
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

Testes de Integração
- Verificar registro correto dos endpoints
- Testar conexão WebSocket via cliente
- Validar CORS para requisições cross-origin
- Confirmar rate limiting funcional

Segurança
- Validar tokens de autenticação
- Implementar sanitização de mensagens
- Configurar limite de conexões por IP
- Logs sem dados sensíveis

Monitoramento
- Métricas de conexões ativas
- Latência de mensagens
- Taxa de erro por endpoint
- Health checks periódicos

Entregáveis do PR
- Atualização do main.py com routers WebSocket
- Configuração de lifecycle events
- Docker Compose com Redis
- Variáveis de ambiente em .env.example
- Testes de integração básicos

Checklists úteis
- Revisar agents/backend-development.md para estrutura
- Seguir agents/api.md para padrões de API
- Validar com agents/security-check.md

Notas
- Garantir que Redis esteja rodando antes de iniciar o backend
- Configurar reconnect automático para Redis
- Considerar usar Redis Sentinel para alta disponibilidade em produção