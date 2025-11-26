# Prompt: Otimizar Lifecycle de Sessões de Chat

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, ai-agents).
- Guarde como referência: agents/backend-development.md, agents/frontend-development.md, agents/qa-agent.md, docs/development-guidelines.md.

Objetivo
- Evitar criação desnecessária de sessões de chat quando o usuário apenas acessa a interface.
- Criar sessão somente após a primeira mensagem enviada pelo usuário e garantindo vínculo correto no banco.
- Remover a mensagem automática "Sessão iniciada! Como posso ajudá-lo com a análise da obra?" do fluxo inicial.

Escopo
- Backend: ajustar `chat_service` e rotas (REST/WebSocket) para adiar a criação da sessão até receber a primeira mensagem.
- Frontend: revisar fluxo de inicialização do chat para não disparar criação de sessão antecipada.
- Persistência: garantir que logs, histórico e metadados da sessão sejam gravados apenas após a primeira mensagem.
- UX: retirar mensagem de boas-vindas automática, mantendo apenas histórico real do usuário e do agente.

Requisitos de Configuração
- Nenhum novo segredo esperado; confirmar se variáveis existentes para chat permanecem válidas após a alteração.
- Caso exista feature flag para mensagens iniciais, reaproveitar ou documentar atualização.

Arquitetura de Alto Nível
- Application Layer (`backend/src/application/services/chat_service.py`): introduzir lógica que aguarde `user_message` antes de chamar o repositório de sessões.
- Domain Layer: revisar entidades/vo do chat para permitir estado "pending" ou similar antes de persistir.
- Infrastructure (`backend/src/infrastructure/repositories/chat_session_repository.py` ou equivalente): garantir que criação no banco só acontece mediante chamada explícita.
- Presentation (`backend/src/presentation/api/v1/chat.py` e websockets): adaptar endpoints/eventos para lidar com sessão inexistente até primeira mensagem.
- Frontend (`frontend/src/services/chat.service.js`, hooks/contextos): remover chamadas `createSession` na montagem e garantir envio correto de `sessionId` após criação.

Fluxo Atual x Proposto
1. **Atual**: usuário abre `/chat` → frontend chama `createSession` → mensagem "Sessão iniciada" aparece → usuário envia primeira mensagem.
2. **Proposto**: usuário abre `/chat` → interface exibe tela vazia aguardando ação → ao enviar primeira mensagem, backend cria sessão, vincula metadados e retorna `sessionId` → frontend utiliza `sessionId` em mensagens subsequentes.

Validações e Estados de Erro
- Caso backend receba mensagem sem sessão prévia, deve criar automaticamente e retornar payload completo.
- Proteger contra duplicação se usuário enviar múltiplas mensagens em paralelo (locks/transactions idempotentes).
- Garantir tratamento adequado para erros durante criação tardia (feedback ao usuário com retry).

Testes (Manual & Automatizados)
- Manual: abrir chat e fechar sem enviar mensagem → conferir que nenhuma nova sessão aparece no banco.
- Manual: enviar primeira mensagem → confirmar que sessão é criada e histórico grava apenas mensagens reais.
- Manual: atualizar página com sessão ativa e continuar conversa → verificar reuso do `sessionId` existente.
- Automatizado: testes unitários/integrados para `chat_service` garantindo que criação acontece somente com payload de mensagem.
- Automatizado: testes frontend (React Testing Library) simulando envio da primeira mensagem e fluxo de `sessionId`.

Entregáveis do PR
- Ajustes em serviços/backend e frontend garantindo novo lifecycle.
- Remoção da mensagem "Sessão iniciada! Como posso ajudá-lo com a análise da obra?" do código.
- Atualização de documentação relevante (`docs/ai-agents.md` ou `docs/frontend.md`) explicando novo comportamento.
- Evidências de testes: `pytest` (backend) e `npm test` ou similar (frontend).

Notas
- Registrar migração/cleanup se existirem sessões "em branco" criadas anteriormente (pode ser roteiro manual).
- Coordenar com time de analytics para preservar métricas (sessões só contam após interação real).
- Documentar mudança na release notes para o time de produto.
