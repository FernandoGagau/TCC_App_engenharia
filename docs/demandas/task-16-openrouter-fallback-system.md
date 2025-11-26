# Prompt: OpenRouter Fallback System - Sistema de Roteamento Inteligente de LLMs

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, ai-agents).
- Siga os guias: agents/backend-development.md, agents/ai-agent-development.md.

Objetivo
- Implementar sistema de fallback inteligente com OpenRouter para alta disponibilidade.
- Criar lógica de seleção de modelo baseada em custo, latência e capacidades.
- Implementar failover automático e otimização de custos.

Escopo
- Client Configuration: setup completo do OpenRouter com múltiplos modelos.
- Model Selection: algoritmo de seleção baseado em contexto e requisitos.
- Cost Optimization: escolha inteligente para minimizar custos.
- Failover Mechanism: retry automático com modelos alternativos.
- Usage Monitoring: tracking detalhado de uso e custos por modelo.

Requisitos de Configuração
- Variáveis de ambiente:
  - OPENROUTER_API_KEY=sk-or-...
  - PRIMARY_MODEL=x-ai/grok-4-fast
  - VISION_MODEL=google/gemini-2.5-flash-image-preview
  - FAST_MODEL=deepseek/deepseek-chat-v3.1:free
  - FALLBACK_MODELS=anthropic/claude-sonnet-4,google/gemini-2.5-flash
  - MAX_RETRIES=3
  - COST_THRESHOLD_USD=0.10  # por requisição
  - LATENCY_THRESHOLD_MS=5000

Arquitetura de Alto Nível
- Router Service: gerenciamento de roteamento e seleção de modelo
- Model Registry: catálogo de modelos com capacidades e custos
- Fallback Handler: lógica de retry e failover
- Cost Tracker: monitoramento de gastos em tempo real
- Performance Monitor: análise de latência e qualidade

Modelagem de Dados (MongoDB)
```python
# ModelUsage Document
{
    "usage_id": str,
    "timestamp": datetime,
    "project_id": ObjectId,
    "user_id": str,
    "model": str,
    "provider": str,
    "request": {
        "prompt_tokens": int,
        "max_tokens": int,
        "temperature": float,
        "task_type": str  # "text", "vision", "code", etc.
    },
    "response": {
        "completion_tokens": int,
        "total_tokens": int,
        "latency_ms": int,
        "success": bool,
        "error": str  # se falhou
    },
    "cost": {
        "input_cost_usd": float,
        "output_cost_usd": float,
        "total_cost_usd": float
    },
    "metadata": {
        "agent_type": str,
        "fallback_attempt": int,
        "original_model": str  # se foi fallback
    }
}

# ModelPerformance Document
{
    "model": str,
    "period": "hourly" | "daily" | "weekly",
    "timestamp": datetime,
    "metrics": {
        "total_requests": int,
        "success_rate": float,
        "avg_latency_ms": float,
        "p95_latency_ms": float,
        "p99_latency_ms": float,
        "total_cost_usd": float,
        "avg_cost_per_request": float
    },
    "error_breakdown": {
        "timeout": int,
        "rate_limit": int,
        "api_error": int,
        "other": int
    }
}
```

Implementação do OpenRouter Service
```python
# backend/src/infrastructure/openrouter_service.py
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from enum import Enum

class ModelCapability(Enum):
    TEXT = "text"
    VISION = "vision"
    CODE = "code"
    REASONING = "reasoning"
    SPEED = "speed"

class ModelRegistry:
    """Registro de modelos disponíveis com suas características"""

    MODELS = {
        "x-ai/grok-4-fast": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.CODE],
            "max_tokens": 2000000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "priority": 1,
            "timeout": 30
        },
        "google/gemini-2.5-flash-image-preview": {
            "capabilities": [ModelCapability.VISION, ModelCapability.TEXT],
            "max_tokens": 4096,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.0005,
            "priority": 1,
            "timeout": 20
        },
        "meta-llama/llama-3-70b-instruct": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.SPEED],
            "max_tokens": 8192,
            "cost_per_1k_input": 0.0007,
            "cost_per_1k_output": 0.0009,
            "priority": 2,
            "timeout": 10
        },
        "openai/gpt-4-turbo": {
            "capabilities": [ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING],
            "max_tokens": 4096,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
            "priority": 2,
            "timeout": 25
        }
    }

    @classmethod
    def get_models_for_capability(cls, capability: ModelCapability) -> List[str]:
        """Retornar modelos que suportam uma capacidade específica"""
        return [
            model for model, info in cls.MODELS.items()
            if capability in info["capabilities"]
        ]

    @classmethod
    def estimate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimar custo de uma requisição"""
        if model not in cls.MODELS:
            return 0.0

        info = cls.MODELS[model]
        input_cost = (input_tokens / 1000) * info["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * info["cost_per_1k_output"]
        return input_cost + output_cost

class OpenRouterService:
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.usage_tracker = UsageTracker()
        self.performance_monitor = PerformanceMonitor()

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task_type: str = "text",
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """Completar requisição com fallback automático"""

        # Selecionar modelo baseado no tipo de tarefa
        if not model:
            model = await self._select_model(task_type, messages)

        # Tentar com modelo primário
        attempt = 0
        errors = []
        fallback_models = self._get_fallback_chain(model, task_type)

        for current_model in [model] + fallback_models[:max_retries]:
            attempt += 1
            start_time = datetime.utcnow()

            try:
                # Verificar custo estimado
                estimated_cost = self._estimate_request_cost(current_model, messages)
                if estimated_cost > self.config.get("COST_THRESHOLD_USD", 0.10):
                    # Tentar modelo mais barato
                    current_model = await self._find_cheaper_alternative(
                        current_model,
                        task_type
                    )

                # Fazer requisição
                response = await self._make_request(
                    current_model,
                    messages,
                    **kwargs
                )

                # Registrar sucesso
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self.usage_tracker.track(
                    model=current_model,
                    input_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                    output_tokens=response.get("usage", {}).get("completion_tokens", 0),
                    latency_ms=latency_ms,
                    success=True,
                    attempt=attempt
                )

                return {
                    **response,
                    "model_used": current_model,
                    "fallback_attempt": attempt - 1,
                    "latency_ms": latency_ms
                }

            except Exception as e:
                errors.append({
                    "model": current_model,
                    "error": str(e),
                    "attempt": attempt
                })

                # Registrar falha
                await self.usage_tracker.track(
                    model=current_model,
                    success=False,
                    error=str(e),
                    attempt=attempt
                )

                # Log e continuar com próximo modelo
                logger.warning(
                    f"Model {current_model} failed (attempt {attempt}): {e}"
                )

        # Todas as tentativas falharam
        raise Exception(f"All models failed. Errors: {errors}")

    async def _select_model(
        self,
        task_type: str,
        messages: List[Dict]
    ) -> str:
        """Selecionar melhor modelo para a tarefa"""

        # Detectar se precisa visão
        has_images = any(
            "image" in msg.get("content", "") or
            isinstance(msg.get("content"), list)
            for msg in messages
        )

        if has_images:
            return self.config.get("VISION_MODEL", "google/gemini-2.5-flash-image-preview")

        # Verificar tamanho do contexto
        total_chars = sum(len(msg.get("content", "")) for msg in messages)

        # Para contextos pequenos, usar modelo rápido
        if total_chars < 1000:
            return self.config.get("FAST_MODEL", "meta-llama/llama-3-70b-instruct")

        # Para raciocínio complexo
        if task_type == "reasoning" or "analyze" in str(messages):
            return self.config.get("PRIMARY_MODEL", "x-ai/grok-4-fast")

        # Default
        return self.config.get("PRIMARY_MODEL", "x-ai/grok-4-fast")

    async def _make_request(
        self,
        model: str,
        messages: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """Fazer requisição para OpenRouter"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://construction-analysis.ai",
            "X-Title": "Construction Analysis Agent",
            "Content-Type": "application/json"
        }

        # Configurar timeout baseado no modelo
        timeout = ModelRegistry.MODELS.get(model, {}).get("timeout", 30)

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": kwargs.get("stream", False)
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        return response.json()

    def _get_fallback_chain(self, primary_model: str, task_type: str) -> List[str]:
        """Obter cadeia de fallback para um modelo"""

        # Obter capacidade necessária
        capability_map = {
            "text": ModelCapability.TEXT,
            "vision": ModelCapability.VISION,
            "code": ModelCapability.CODE,
            "reasoning": ModelCapability.REASONING
        }

        capability = capability_map.get(task_type, ModelCapability.TEXT)

        # Obter modelos compatíveis
        compatible_models = ModelRegistry.get_models_for_capability(capability)

        # Remover modelo primário e ordenar por prioridade/custo
        fallback_models = [m for m in compatible_models if m != primary_model]
        fallback_models.sort(
            key=lambda m: (
                ModelRegistry.MODELS[m]["priority"],
                ModelRegistry.MODELS[m]["cost_per_1k_input"]
            )
        )

        return fallback_models

    async def _find_cheaper_alternative(
        self,
        model: str,
        task_type: str
    ) -> str:
        """Encontrar alternativa mais barata para um modelo"""

        current_cost = ModelRegistry.MODELS[model]["cost_per_1k_input"]
        alternatives = self._get_fallback_chain(model, task_type)

        for alt in alternatives:
            alt_cost = ModelRegistry.MODELS[alt]["cost_per_1k_input"]
            if alt_cost < current_cost * 0.5:  # 50% mais barato
                return alt

        return model  # Manter original se não houver alternativa boa

    def _estimate_request_cost(
        self,
        model: str,
        messages: List[Dict]
    ) -> float:
        """Estimar custo de uma requisição"""

        # Estimar tokens (aproximado)
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        estimated_tokens = total_chars / 4  # Aproximação

        return ModelRegistry.estimate_cost(
            model,
            input_tokens=int(estimated_tokens),
            output_tokens=500  # Estimativa conservadora
        )

class UsageTracker:
    """Rastrear uso e custos"""

    def __init__(self, db_service=None):
        self.db = db_service

    async def track(self, **kwargs):
        """Registrar uso de modelo"""
        usage_data = {
            "usage_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            **kwargs
        }

        if self.db:
            await self.db.model_usage.insert_one(usage_data)

        # Atualizar métricas em tempo real
        await self._update_metrics(usage_data)

    async def get_usage_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "model"
    ) -> Dict[str, Any]:
        """Obter resumo de uso"""

        pipeline = [
            {
                "$match": {
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }
            },
            {
                "$group": {
                    "_id": f"${group_by}",
                    "total_requests": {"$sum": 1},
                    "total_cost": {"$sum": "$cost.total_cost_usd"},
                    "avg_latency": {"$avg": "$response.latency_ms"},
                    "success_rate": {
                        "$avg": {
                            "$cond": ["$response.success", 1, 0]
                        }
                    }
                }
            }
        ]

        if self.db:
            results = await self.db.model_usage.aggregate(pipeline).to_list(None)
            return {item["_id"]: item for item in results}

        return {}

class PerformanceMonitor:
    """Monitorar performance dos modelos"""

    async def analyze_model_performance(self, model: str) -> Dict[str, Any]:
        """Analisar performance de um modelo"""
        # Implementar análise de performance
        pass

    async def get_best_performing_model(self, task_type: str) -> str:
        """Obter modelo com melhor performance para uma tarefa"""
        # Implementar seleção baseada em performance histórica
        pass
```

Integração com Agents
```python
# backend/src/infrastructure/llm_service.py
from infrastructure.openrouter_service import OpenRouterService

class LLMService:
    def __init__(self, config: Dict[str, Any]):
        self.openrouter = OpenRouterService(
            api_key=config["OPENROUTER_API_KEY"],
            config=config
        )
        self.cache = {}  # Cache de respostas

    async def generate(
        self,
        prompt: str,
        agent_type: str,
        **kwargs
    ) -> str:
        """Interface unificada para agents"""

        # Determinar tipo de tarefa baseado no agent
        task_type_map = {
            "visual": "vision",
            "document": "text",
            "progress": "reasoning",
            "report": "text",
            "supervisor": "reasoning"
        }

        task_type = task_type_map.get(agent_type, "text")

        # Criar mensagens
        messages = [
            {"role": "system", "content": self._get_system_prompt(agent_type)},
            {"role": "user", "content": prompt}
        ]

        # Chamar OpenRouter com fallback
        response = await self.openrouter.complete(
            messages=messages,
            task_type=task_type,
            **kwargs
        )

        return response["choices"][0]["message"]["content"]

    def _get_system_prompt(self, agent_type: str) -> str:
        """Obter prompt do sistema para cada tipo de agent"""
        prompts = {
            "visual": "You are a construction visual analysis expert...",
            "document": "You are a document processing specialist...",
            "progress": "You are a project progress analyst...",
            "report": "You are a report generation expert...",
            "supervisor": "You are an AI supervisor coordinating multiple agents..."
        }
        return prompts.get(agent_type, "You are a helpful AI assistant.")
```

Monitoring Dashboard
```python
# backend/src/presentation/api/monitoring_routes.py
@router.get("/api/monitoring/model-usage")
async def get_model_usage(
    start_date: datetime,
    end_date: datetime,
    current_user=Depends(require_admin)
):
    """Obter estatísticas de uso de modelos"""

    usage = await usage_tracker.get_usage_summary(
        start_date,
        end_date,
        group_by="model"
    )

    return {
        "period": {
            "start": start_date,
            "end": end_date
        },
        "models": usage,
        "total_cost": sum(m["total_cost"] for m in usage.values()),
        "total_requests": sum(m["total_requests"] for m in usage.values())
    }

@router.get("/api/monitoring/model-performance")
async def get_model_performance(
    model: Optional[str] = None
):
    """Obter métricas de performance dos modelos"""

    if model:
        return await performance_monitor.analyze_model_performance(model)

    # Retornar performance de todos os modelos
    all_models = ModelRegistry.MODELS.keys()
    performance = {}

    for model_name in all_models:
        performance[model_name] = await performance_monitor.analyze_model_performance(
            model_name
        )

    return performance
```

Testes
```python
# backend/tests/test_openrouter.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

class TestOpenRouterService:
    @pytest.mark.asyncio
    async def test_model_selection(self):
        # Test seleção de modelo baseada em tarefa
        pass

    @pytest.mark.asyncio
    async def test_fallback_mechanism(self):
        # Test fallback quando modelo primário falha
        pass

    @pytest.mark.asyncio
    async def test_cost_optimization(self):
        # Test seleção de modelo mais barato
        pass

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        # Test retry com backoff
        pass
```

Alertas e Notificações
```python
class AlertSystem:
    async def check_thresholds(self):
        """Verificar thresholds e enviar alertas"""

        # Alerta de custo
        daily_cost = await self.get_daily_cost()
        if daily_cost > self.config["DAILY_COST_LIMIT"]:
            await self.send_alert(
                "Cost threshold exceeded",
                f"Daily cost: ${daily_cost:.2f}"
            )

        # Alerta de latência
        avg_latency = await self.get_average_latency()
        if avg_latency > self.config["LATENCY_THRESHOLD_MS"]:
            await self.send_alert(
                "High latency detected",
                f"Average: {avg_latency}ms"
            )

        # Alerta de taxa de erro
        error_rate = await self.get_error_rate()
        if error_rate > 0.05:  # 5%
            await self.send_alert(
                "High error rate",
                f"Error rate: {error_rate*100:.1f}%"
            )
```

Entregáveis do PR
- OpenRouter service com fallback inteligente
- Model registry com capacidades e custos
- Sistema de tracking de uso e custos
- Performance monitoring
- Integração com todos os agents
- Dashboard de monitoramento
- Testes unitários e integração
- Documentação de configuração

Checklists úteis
- Revisar agents/ai-agent-development.md para integração
- Seguir agents/backend-development.md para APIs
- Validar com agents/security-check.md
- Testar fallback com diferentes cenários de falha

Notas
- Implementar cache de respostas para economizar
- Adicionar circuit breaker para modelos problemáticos
- Considerar pré-pagamento/créditos para controle de custos
- Implementar A/B testing para comparar modelos
- Adicionar logs estruturados para análise posterior