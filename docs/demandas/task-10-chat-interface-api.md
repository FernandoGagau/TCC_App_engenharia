# Prompt: Chat Interface API - Sistema de Comunicação em Tempo Real

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, database, auth).
- Siga os guias: agents/backend-development.md, agents/frontend-development.md, agents/api.md.

Objetivo
- Implementar API WebSocket para chat em tempo real com streaming de respostas.
- Gerenciar histórico de conversas e sessões de usuários.
- Implementar rate limiting, throttling e persistência de mensagens.

Escopo
- WebSocket Endpoint: comunicação bidirecional em tempo real.
- Message Streaming: respostas incrementais dos agents.
- Session Management: criar, restaurar e persistir conversas.
- Rate Limiting: controle de requisições por usuário.
- History Management: armazenamento e recuperação de histórico.

Requisitos de Configuração
- Dependências Python:
  - fastapi[websockets]==0.104.1
  - python-socketio==5.10.0 (opcional para fallback)
  - redis==5.0.1 para cache de sessões
  - slowapi==0.1.9 para rate limiting
- Variáveis de ambiente:
  - WEBSOCKET_MAX_CONNECTIONS=100
  - WEBSOCKET_TIMEOUT=300  # segundos
  - RATE_LIMIT_MESSAGES_PER_MINUTE=30
  - MAX_MESSAGE_LENGTH=5000

Arquitetura de Alto Nível
- WebSocket Server: FastAPI com endpoint /ws
- Connection Manager: gerenciamento de conexões ativas
- Message Queue: Redis pub/sub para escalabilidade
- Session Store: MongoDB para persistência
- Rate Limiter: Redis para contadores temporais

Modelagem de Dados (MongoDB)
```python
# ChatSession Document
{
    "session_id": str,  # UUID
    "project_id": ObjectId,
    "user_id": str,
    "started_at": datetime,
    "last_activity": datetime,
    "status": "active" | "idle" | "closed",
    "metadata": {
        "user_agent": str,
        "ip_address": str,
        "client_version": str
    },
    "settings": {
        "model_preference": str,
        "language": str,
        "stream_responses": bool
    }
}

# ChatMessage Document
{
    "message_id": str,  # UUID
    "session_id": str,
    "project_id": ObjectId,
    "timestamp": datetime,
    "role": "user" | "assistant" | "system",
    "content": str,
    "metadata": {
        "tokens_used": int,
        "processing_time": float,
        "agent_used": str,
        "attachments": []
    },
    "reactions": {
        "helpful": bool,
        "rating": int  # 1-5
    }
}

# ConnectionState (Redis)
{
    "connection_id": str,
    "session_id": str,
    "user_id": str,
    "connected_at": datetime,
    "last_ping": datetime,
    "active": bool
}
```

APIs (WebSocket & REST)
```python
# WebSocket Events
- connect: estabelecer conexão
- message: enviar mensagem do usuário
- stream_start: iniciar streaming de resposta
- stream_chunk: chunk de resposta
- stream_end: finalizar streaming
- error: erro durante processamento
- disconnect: encerrar conexão

# REST Endpoints
- GET /api/chat/sessions: listar sessões do usuário
- GET /api/chat/sessions/{session_id}: detalhes da sessão
- GET /api/chat/sessions/{session_id}/messages: histórico de mensagens
- DELETE /api/chat/sessions/{session_id}: encerrar sessão
- POST /api/chat/export: exportar conversa
```

Implementação WebSocket
```python
# backend/src/presentation/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Optional
import json
import asyncio
from uuid import uuid4
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_states: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = {
            "connected_at": datetime.utcnow(),
            "message_count": 0
        }

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            del self.session_states[session_id]

    async def send_message(self, session_id: str, message: Dict):
        if websocket := self.active_connections.get(session_id):
            await websocket.send_json(message)

    async def broadcast(self, message: Dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    current_user=Depends(get_current_user)
):
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receber mensagem do cliente
            data = await websocket.receive_json()

            # Validar rate limiting
            if not await check_rate_limit(current_user.id):
                await websocket.send_json({
                    "type": "error",
                    "message": "Rate limit exceeded"
                })
                continue

            # Processar mensagem
            response = await process_message(data, session_id, current_user)

            # Stream de resposta
            if response.get("stream"):
                await stream_response(websocket, response)
            else:
                await websocket.send_json(response)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        await save_session_state(session_id)

async def stream_response(websocket: WebSocket, response: Dict):
    """Stream de resposta incremental"""
    await websocket.send_json({
        "type": "stream_start",
        "message_id": response["message_id"]
    })

    # Simular streaming de chunks
    for chunk in response["chunks"]:
        await websocket.send_json({
            "type": "stream_chunk",
            "content": chunk,
            "message_id": response["message_id"]
        })
        await asyncio.sleep(0.05)  # Delay para efeito visual

    await websocket.send_json({
        "type": "stream_end",
        "message_id": response["message_id"],
        "metadata": response.get("metadata", {})
    })
```

Rate Limiting Implementation
```python
# backend/src/infrastructure/rate_limiter.py
from typing import Optional
import redis
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        user_id: str,
        limit: int = 30,
        window: int = 60
    ) -> bool:
        """Verificar rate limit usando sliding window"""
        key = f"rate_limit:{user_id}"
        now = datetime.utcnow().timestamp()
        window_start = now - window

        # Remover entradas antigas
        self.redis.zremrangebyscore(key, 0, window_start)

        # Contar requisições na janela
        count = self.redis.zcard(key)

        if count >= limit:
            return False

        # Adicionar nova requisição
        self.redis.zadd(key, {str(uuid4()): now})
        self.redis.expire(key, window)

        return True

    async def get_remaining_quota(self, user_id: str) -> Dict:
        """Obter quota restante"""
        key = f"rate_limit:{user_id}"
        count = self.redis.zcard(key)
        return {
            "used": count,
            "limit": 30,
            "reset_in": self.redis.ttl(key)
        }
```

Message Processing
```python
# backend/src/application/services/chat_service.py
from typing import Dict, Any
import asyncio

class ChatService:
    def __init__(self, supervisor_agent, db_service):
        self.supervisor = supervisor_agent
        self.db = db_service

    async def process_message(
        self,
        message: Dict,
        session_id: str,
        user_id: str
    ) -> Dict:
        """Processar mensagem e gerar resposta"""
        # Salvar mensagem do usuário
        user_message = await self.save_message(
            session_id=session_id,
            role="user",
            content=message["content"],
            metadata=message.get("metadata", {})
        )

        # Preparar contexto
        context = await self.build_context(session_id)

        # Processar com supervisor agent
        response = await self.supervisor.process({
            "messages": context["messages"],
            "project_data": context["project_data"],
            "session_id": session_id,
            "user_id": user_id
        })

        # Salvar resposta
        assistant_message = await self.save_message(
            session_id=session_id,
            role="assistant",
            content=response["content"],
            metadata=response.get("metadata", {})
        )

        return {
            "message_id": assistant_message["message_id"],
            "content": response["content"],
            "stream": message.get("stream", True),
            "chunks": self.chunk_response(response["content"]),
            "metadata": response.get("metadata", {})
        }

    def chunk_response(self, content: str, chunk_size: int = 50) -> List[str]:
        """Dividir resposta em chunks para streaming"""
        words = content.split()
        chunks = []
        current_chunk = []

        for word in words:
            current_chunk.append(word)
            if len(current_chunk) >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    async def build_context(self, session_id: str) -> Dict:
        """Construir contexto da conversa"""
        messages = await self.db.get_session_messages(
            session_id,
            limit=10  # Últimas 10 mensagens
        )

        project = await self.db.get_project_by_session(session_id)

        return {
            "messages": messages,
            "project_data": project,
            "session_metadata": await self.db.get_session(session_id)
        }
```

Frontend WebSocket Client
```javascript
// frontend/src/services/WebSocketService.js
class WebSocketService {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.ws = null;
        this.sessionId = null;
        this.listeners = new Map();
    }

    async connect(sessionId) {
        this.sessionId = sessionId;
        const token = localStorage.getItem('auth_token');

        this.ws = new WebSocket(
            `${this.baseUrl}/ws/${sessionId}?token=${token}`
        );

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.emit('connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.emit('disconnected');
            this.reconnect();
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'stream_start':
                this.emit('streamStart', data);
                break;
            case 'stream_chunk':
                this.emit('streamChunk', data);
                break;
            case 'stream_end':
                this.emit('streamEnd', data);
                break;
            case 'error':
                this.emit('error', data);
                break;
            default:
                this.emit('message', data);
        }
    }

    sendMessage(content, metadata = {}) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'message',
                content,
                metadata,
                timestamp: new Date().toISOString()
            }));
        }
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(cb => cb(data));
        }
    }

    async reconnect() {
        console.log('Attempting to reconnect...');
        await new Promise(resolve => setTimeout(resolve, 3000));
        this.connect(this.sessionId);
    }
}

export default WebSocketService;
```

Session Persistence
- Auto-save a cada 30 segundos
- Recuperação de sessão após desconexão
- Limpeza de sessões antigas (TTL)
- Export de histórico completo

Error Handling
- Reconexão automática com backoff
- Fallback para polling se WebSocket falhar
- Queue de mensagens offline
- Retry de mensagens falhadas

Testes
```python
# backend/tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
import asyncio

class TestWebSocket:
    def test_websocket_connection(self, client):
        with client.websocket_connect("/ws/test-session") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"

    def test_message_streaming(self, client):
        # Test streaming response
        pass

    def test_rate_limiting(self, client):
        # Test rate limit enforcement
        pass

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        # Test multiple concurrent connections
        pass
```

Monitoring e Métricas
- Conexões ativas em tempo real
- Latência de mensagens
- Taxa de erro por sessão
- Uso de banda por usuário

Segurança
- Autenticação via JWT token
- Validação de origem (CORS)
- Sanitização de mensagens
- Limite de tamanho de mensagem
- Proteção contra flood

Entregáveis do PR
- WebSocket endpoint implementation
- Connection manager com Redis
- Rate limiting system
- Message streaming functionality
- Session persistence layer
- Frontend WebSocket client
- Testes de integração
- Documentação de eventos

Checklists úteis
- Revisar agents/backend-development.md para APIs
- Seguir agents/frontend-development.md para cliente
- Validar com agents/security-check.md
- Testar reconexão e fallbacks

Notas
- Implementar heartbeat/ping-pong para detectar conexões mortas
- Considerar compressão de mensagens grandes
- Adicionar suporte a attachments (imagens/docs)
- Implementar typing indicators
- Preparar para escalar com múltiplas instâncias (Redis pub/sub)