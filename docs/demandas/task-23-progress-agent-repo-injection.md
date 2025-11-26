# Prompt: Garantir Repositório no Progress Agent e Refatorar Arquitetura

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, ai-agents, database).
- Referências úteis: docs/ai-agents.md, docs/backend.md, docs/development-guidelines.md, agents/backend-development.md, agents/ai-agent-development.md, agents/database-development.md.

Objetivo
- Garantir que o Progress Agent receba um repositório de projetos válido, permitindo acesso aos dados do MongoDB.
- Refatorar a criação e injeção de dependências na AgentFactory aplicando SOLID e divisões de responsabilidade claras.
- Assegurar que `_get_project` nunca retorne `None` por ausência de dependência, desbloqueando cálculos de progresso, atrasos e previsões.

Escopo
- Atualizar `backend/src/infrastructure/agents/agent_factory.py` para injetar um `ProjectRepository` real ao `ProgressAgent` e outros agentes que dependam de dados persistidos.
- Criar interface/abstração de repositório (ex.: `backend/src/domain/repositories/project_repository.py`) e implementação MongoDB em `backend/src/infrastructure/repositories/project_repository.py` reutilizável por agentes e serviços.
- Revisar `backend/src/agents/progress_agent.py` dividindo responsabilidades em métodos auxiliares menores e garantindo `try/except` localizados.
- Ajustar Supervisor/AgentFactory para receber dependências via construtor ou provider configurável (DIP).
- Atualizar testes existentes ou criar novos para cobrir cenários de injeção faltante, carregamento de projeto e fluxo completo do agente.

Requisitos de Configuração
- Confirmar conexão MongoDB funcional (`DB_MONGODB_URL`, `DB_DATABASE_NAME`).
- Garantir registros mínimos de projeto para testes (fixtures ou seed).
- Verificar compatibilidade com demais serviços que consomem ProjectRepository (ChatService, ReportAgent).

Arquitetura de Alto Nível
- `ProjectRepository` (interface) define operações necessárias aos agentes.
- `MongoProjectRepository` implementa interface usando Beanie/Motor.
- `AgentFactory` orquestra construção dos agentes recebendo repositórios via construtor (injeção explícita).
- `ProgressAgent` depende apenas da interface, facilitando mocks em testes.

Princípios e Boas Práticas
- Aplicar SOLID (SRP para classes, DIP para dependências, ISP para interfaces enxutas).
- Utilizar `try/except` em blocos críticos de I/O com logs significativos.
- Evitar funções/métodos gigantes; extrair helpers para cálculo de métricas, predições e análise de atrasos.
- Cobrir mensagens de erro claras quando projeto não encontrado ou repositório retorna vazio.

Testes (Manual & Automatizados)
- Unitários: mocks do repositório para validar caminhos de sucesso/erro no ProgressAgent.
- Integração: testes end-to-end acionando AgentFactory + ProgressAgent com MongoDB real/fixtures.
- QA Manual: executar fluxo de análise de progresso via Supervisor e checar logs/resultados.

Entregáveis do PR
- Novas interfaces/implementações de repositório + ajustes na AgentFactory e ProgressAgent.
- Testes atualizados (`tests/unit/test_progress_agent.py`, `tests/integration/test_agent_factory.py` ou similares).
- Documentação atualizada (seções em docs/ai-agents.md ou docs/backend.md explicando injeção).
- Notas de migração se necessário (ex.: inicialização de AgentFactory mudando assinatura).

Notas
- Verificar se outros agentes (ReportAgent) podem reaproveitar a mesma interface.
- Garantir compatibilidade com instâncias locais, QA e produção (Railway).
- Planejar monitoramento futuro (logs métricas quando repositório indisponível).
