# Prompt: Integrar OpenRouterService no LLM Routing com Failover

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, ai-agents, infrastructure).
- Referências úteis: docs/ai-agents.md, docs/backend.md, docs/openrouter.md (se existir), agents/backend-development.md, agents/ai-agent-development.md, agents/security-check.md.

Objetivo
- Ativar o serviço de roteamento OpenRouter em tempo de execução com fallback, custo e latência monitorados.
- Substituir chamadas diretas ao `ChatOpenAI` por uma camada que utiliza `OpenRouterService` quando configurado.
- Aplicar SOLID/TRY à implementação, quebrando responsabilidades em módulos menores (seleção, monitoramento, métricas).

Escopo
- Refatorar `backend/src/infrastructure/llm_service.py` para delegar ao `OpenRouterService` (quando `USE_OPENROUTER=true`) e manter fallback local (OpenAI direto).
- Revisar `backend/src/infrastructure/openrouter_service.py`, extraindo componentes para seleção de modelo, cálculo de custo, failover e observabilidade.
- Atualizar AgentFactory/serviços que dependem de `get_llm_service()` para receber instâncias configuradas e suportar streaming.
- Implementar métricas/logs para registrar modelo escolhido, custo estimado, retries e falhas.
- Garantir configuração via `.env` (`OPENROUTER_API_KEY`, modelos preferenciais, thresholds) conforme task 16.

Requisitos de Configuração
- Validar variáveis (`USE_OPENROUTER`, `OPENROUTER_API_KEY`, `PRIMARY_MODEL`, `FALLBACK_MODELS`, `COST_THRESHOLD_USD`, etc.).
- Certificar-se de que `requirements.txt` contém dependências necessárias (httpx, etc.).
- Atualizar `.env.example` e docs explicando flags e prioridades de modelos.

Arquitetura de Alto Nível
- `LLMService` atua como fachada: decide se usa OpenRouterService ou fallback.
- `OpenRouterService` composto por módulos: `ModelSelector`, `CostManager`, `FailureHandler`, `UsageTracker`.
- Serviços/agents consomem LLM via interface comum (`invoke`, `stream`, `estimate_cost`).

Princípios e Boas Práticas
- Aplicar DIP: camadas de aplicação dependem de interface `BaseLLMClient` em vez de classes concretas.
- Usar `try/except` controlado para retries e fallback, com logs estruturados (`logger.bind(model=...)`).
- Evitar métodos extensos; separar em arquivos auxiliares quando necessário.
- Garantir que erros de roteamento não interrompam fluxo principal (fallback transparente).

Testes (Manual & Automatizados)
- Unitários: mocks do OpenRouter API validando seleção, retries, fallback, custo.
- Integração: fluxo end-to-end disparando `OpenRouterService` com responses simuladas.
- QA Manual: configurar `USE_OPENROUTER=true`, testar fallback (forçar erro) e verificar logs/monitoramento.

Entregáveis do PR
- `llm_service.py` e `openrouter_service.py` refatorados + novos módulos auxiliares.
- Testes unitários/integrados cobrindo seleção e fallback.
- Documentação atualizada (docs/ai-agents.md, docs/openrouter.md, `.env.example`).
- Notas em changelog destacando mudança no fluxo LLM.

Notas
- Coordenar com tasks de monitoramento/token tracker para registrar custos por modelo.
- Validar compatibilidade com agents de visão (sem suporte OpenRouter, usar fallback).
- Planejar futura instrumentação (prometheus/log events) para latência e custo.
