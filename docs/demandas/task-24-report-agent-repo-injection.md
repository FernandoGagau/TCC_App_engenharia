# Prompt: Injetar Repositório no Report Agent e Refatorar Arquitetura

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, ai-agents, reporting).
- Referências úteis: docs/ai-agents.md, docs/backend.md, docs/reporting.md (se existir), agents/backend-development.md, agents/ai-agent-development.md, agents/database-development.md.

Objetivo
- Garantir que o Report Agent receba um repositório de projetos válido, permitindo operar sobre dados reais no MongoDB.
- Refatorar o arquivo do agente aplicando TRY e princípios SOLID, dividindo responsabilidades em módulos/métodos menores.
- Permitir que os fluxos de geração de relatórios recuperem projetos, análises e métricas sem encerrar precocemente.

Escopo
- Atualizar `backend/src/infrastructure/agents/agent_factory.py` para injetar `ProjectRepository` (mesmo provider da task Progress Agent) no Report Agent.
- Revisar `backend/src/agents/report_agent.py`, extraindo componentes internos (ex.: geradores de seções, métricas, gráficos) em helpers/classes dedicadas.
- Adicionar tratamento de erros com `try/except` localizados, garantindo logs e mensagens claras quando projeto não encontrado ou dependência ausente.
- Assegurar que a interface do repositório seja reutilizada (ou expandida) para atender às necessidades do Report Agent.
- Atualizar Supervisor Agent caso dependa de nova assinatura/injeção.

Requisitos de Configuração
- Confirmar conexão com MongoDB (`DB_MONGODB_URL`, `DB_DATABASE_NAME`).
- Validar disponibilidade de dados de projeto para testar relatórios (fixtures ou seeding).
- Verificar compatibilidade com ReportAgent em pipelines existentes (ex.: chat, dashboards).

Arquitetura de Alto Nível
- `ProjectRepository` (interface) provê métodos para recuperar projetos, métricas e históricos.
- `ReportAgent` recebe dependência via construtor (DIP), focando apenas na lógica de composição de relatórios.
- Helpers dedicados para geração de gráficos, estatísticas e templates (ex.: `ReportDataAssembler`, `ChartBuilder`).
- Supervisor/AgentFactory responsáveis por montagem e orquestração.

Princípios e Boas Práticas
- Aplicar SRP: separar cálculo de métricas, renderização de gráficos e montagem de PDF/JSON.
- Usar `try/except` somente em pontos críticos de I/O e geração, com logs contextuais.
- Garantir que todas as saídas do agente sejam serializadas (dict/bytes) e livres de dependências diretas da camada infra.
- Evitar métodos com mais de ~50 linhas; preferir classes auxiliares ou módulos específicos.

Testes (Manual & Automatizados)
- Unitários: validar que `_get_project` utiliza repositório injetado, que geradores de seção funcionam com mocks.
- Integração: executar ReportAgent através do Supervisor em ambiente de teste com Mongo real/fixtures.
- QA Manual: gerar relatório para projeto de exemplo, verificando conteúdo, gráficos e logs.

Entregáveis do PR
- Ajustes na AgentFactory e no ReportAgent com nova injeção + refatoração modular.
- Novos helpers/módulos (se necessários) com cobertura de testes.
- Documentação atualizada (docs/ai-agents.md, docs/reporting.md) descrevendo arquitetura e dependências.
- Atualização de changelog/notas se a assinatura pública do agente ou factory mudar.

Notas
- Aproveitar interfaces criadas na task Progress Agent (ProjectRepository) para reduzir duplicação.
- Verificar se pipeline de geração PDF/PNG (ReportLab, Matplotlib) continua funcional após refator.
- Planejar monitoramento de erros em produção (ex.: eventos/reporting logs).
