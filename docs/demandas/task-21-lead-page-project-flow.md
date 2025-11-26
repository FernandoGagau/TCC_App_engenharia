# Prompt: Lead Page Apresentando Fluxo Completo do Projeto

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral, guias de arquitetura, frontend e marketing.
- Referências úteis: docs/architecture.md, docs/frontend.md, docs/components.md, docs/ai-agents.md, agents/frontend-development.md.

Objetivo
- Criar uma landing/lead page inicial que comunique de forma didática o fluxo completo do projeto Construction Analysis AI.
- Destacar visão geral, jornadas do usuário, módulos técnicos e integrações principais com alto nível de detalhe.
- Alinhar narrativa visual com a identidade da plataforma e incentivar conversão (call to action para contato/demonstração).

Escopo
- Estruturar página em seções: hero, visão geral, pipeline técnico, cases/benefícios, diferenciais competitivos, call to action.
- Incluir diagramas ou gráficos (SVG/Canvas ou imagens) ilustrando fluxo do sistema (coleta → análise → chat → relatórios).
- Descrever integrações (AI agents, backend FastAPI, banco MongoDB, MinIO, OpenRouter) com linguagem acessível.
- Garantir responsividade, performance, acessibilidade e SEO básico.

Requisitos de Configuração
- Adicionar rota/página `frontend/src/pages/LeadPage.jsx` (ou `/landing`).
- Atualizar roteamento em `frontend/src/App.js` para expor nova página como primeira interação.
- Se necessário, criar componentes auxiliares em `frontend/src/components/landing/**` para cards, timelines, grids animados.
- Considerar uso de JSON/constantes para textos estruturados (facilitar futuras traduções).

Arquitetura de Alto Nível
- Layout base via MUI (`Container`, `Grid`, `Box`) com tema existente.
- Seções principais:
  - **Hero**: headline, subheadline, CTA, link para demo.
  - **Fluxo do Projeto**: timeline ou steps mostrando ingestão de dados, processamento, dashboards e chat.
  - **Arquitetura Técnica**: cards/banners descrevendo backend FastAPI, AI agents, banco, storage, integrações.
  - **Benefícios & KPIs**: métricas, provas sociais ou depoimentos.
  - **FAQ/CTA Final**: perguntas frequentes e formulário/link de contato.
- Incluir animações leves (MUI `Fade`, `Grow`) sem comprometer performance.

Conteúdo & Narrativa
- Utilizar copy em PT-BR com tom profissional e claro.
- Destacar diferenciais: análise em tempo real, agentes especializados (Supervisor, Visual, Document, Progress, Report), automação de relatórios.
- Explicar como dados fluem do canteiro de obras até insights no painel/chat.
- Incluir CTAs consistentes (ex.: "Solicitar demonstração", "Explorar funcionalidades").

Critérios de Aceite
- Página acessível em `/` ou `/landing` como primeira impressão do sistema.
- Fluxo descrito com detalhes suficientes para stakeholders entenderem a jornada técnica e de usuário.
- Visual alinhado ao design system, responsivo em breakpoints mobile/tablet/desktop.
- Lighthouse score >= 90 para Performance, Accessibility, Best Practices (testar localmente).

Testes (Manual & Automatizados)
- Manual: validar layout em diferentes navegadores/resoluções.
- Manual: verificar CTA funcionando (roteamento para contato/chat/demo).
- Automatizado: ajustar testes de snapshot/componentes se aplicável.

Entregáveis do PR
- Nova página e componentes criados em `frontend/src/pages/LeadPage.jsx` e `frontend/src/components/landing/**`.
- Atualização de rotas, navegação e assets.
- Documentação em `docs/frontend.md` ou novo arquivo `docs/ui/landing-page.md` com decisões de design e conteúdo.
- Evidências: capturas/Loom e resultados Lighthouse anexados na descrição do PR.

Notas
- Coordenar com time de marketing/produto para validar copy e CTAs.
- Preparar conteúdo extensível para futuras campanhas (ex.: variáveis de UTMs).
- Avaliar integração com ferramentas de analytics (Google Tag Manager) futuramente.
