# Prompt: Padronizar Textos para PT-BR e Otimizar UX do Frontend

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (frontend, design system, UX).
- Referências úteis: docs/frontend.md, docs/components.md, agents/frontend-development.md, agents/qa-agent.md.

Objetivo
- Revisar todo o frontend para remover nomenclaturas em inglês presentes na UI e padronizar o texto para PT-BR.
- Garantir consistência de tom, voz e terminologia em todas as páginas e componentes.
- Implementar melhorias visuais que favoreçam o fluxo do usuário, mantendo a identidade visual oficial.

Escopo
- Levantamento completo dos textos exibidos (componentes, páginas, menus, mensagens de erro, toasts, placeholders, labels, etc.).
- Atualização dos arquivos de strings (ou componentes) para PT-BR, mantendo semântica correta e linguagem inclusiva.
- Ajuste de componentes para refletir melhorias visuais (hierarquia de informação, espaçamentos, botões, feedbacks).
- Verificação de estados vazios, loaders, mensagens de confirmação e avisos para garantir coerência.
- Registrar padrões linguísticos e de UX em documentação para futuros desenvolvimentos.

Requisitos de Configuração
- Identificar se há mecanismo de i18n existente (ex.: arquivos de tradução); se inexistente, considerar criar estrutura simples (`frontend/src/locales/pt-BR.json`).
- Garantir que novos textos possam ser reutilizados em contextos futuros (evitar hardcode repetido).
- Manter temas e componentes MUI alinhados ao branding definido em `frontend/src/theme` (se disponível).

Arquitetura de Alto Nível
- Organização de textos: centralizar strings em módulo/layer de tradução ou constantes.
- Layout: revisar `frontend/src/pages/*.jsx` e `frontend/src/components/**` para aplicar melhorias visuais.
- Serviços: assegurar que mensagens retornadas de `frontend/src/services/**` sejam exibidas em PT-BR no UI.

Fluxo de Trabalho Sugerido
1. Mapear componentes e páginas com textos em inglês usando `rg` ou lint personalizado.
2. Criar/atualizar arquivo de traduções ou consts, aplicando PT-BR padronizado.
3. Ajustar componentes/páginas para consumir novas strings.
4. Revisar layout (spacing, tipografia, cores) visando clareza e acessibilidade.
5. Validar fluxos principais (login, cadastro, dashboard, chat) garantindo consistência textual e visual.

Critérios de Aceite
- Nenhum texto residual em inglês na interface final.
- Todos os textos possuem tradução aprovada e seguem guia de estilo (formalidade, gênero neutro quando possível).
- Layouts principais exibem melhoria perceptível (ex.: alinhamento, contraste, mensagens contexto).
- Acessibilidade preservada (labels, alt-text, aria) e navegabilidade via teclado funcional.

Testes (Manual & Automatizados)
- Manual: navegar por todas as rotas e validar textos em PT-BR, mensagens coerentes e componentes ajustados.
- Manual: verificar estados de erro, confirmações, tooltips e toasts.
- Automatizado: ajustar testes unitários/snapshots que dependam de textos (React Testing Library / Jest) para novas strings.

Entregáveis do PR
- Atualização dos arquivos de textos/components com nomenclatura PT-BR.
- Ajustes visuais nos componentes/páginas conforme descrito (commits detalhados).
- Documentação em `docs/frontend.md` ou nova seção `docs/ux-style-guide.md` com padrões linguísticos.
- Evidências de testes (prints/gifs opcionais) e execução de `npm run lint` + `npm test` sem falhas.

Notas
- Coordenar com time de produto/UX para aprovação dos textos e melhorias visuais.
- Manter consistência com termos já utilizados no backend/docs para evitar divergências.
- Considerar roadmap futuro para suporte multi-idioma; estruturar código pensando em escalabilidade.
