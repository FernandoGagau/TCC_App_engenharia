# Prompt: Tela de Login e Cadastro de Autenticação Simples

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (frontend, backend, auth, database).
- Siga os guias: agents/frontend-development.md, agents/backend-development.md, agents/security-check.md, docs/authentication.md, docs/frontend.md.

Objetivo
- Entregar fluxo completo de autenticação com cadastro, login e gerenciamento mínimo de sessão.
- Disponibilizar tela de login alinhada à identidade visual existente e liberar o acesso ao chat após autenticação.
- Garantir armazenamento seguro de credenciais, tokens e estados de usuário conforme diretrizes da plataforma.

Escopo
- UI/UX: Tela de login responsiva com campos de e-mail e senha, CTA para cadastro e link de recuperação futura.
- Cadastro: Formulário modal/página para criar usuário com validação de senha e consentimento de termos.
- Backend: Endpoints REST para registro, login, logout, refresh e perfil atual, seguindo DDD no backend/src/.
- Sessão: Emissão de JWT (access + refresh) com cookies HTTP-only e sincronização com estado do frontend.
- Autorização: Proteção das rotas do chat e demais áreas autenticadas via guard/contexto.
- Observabilidade: Logs auditáveis de login/logout e métricas básicas de falhas.

Requisitos de Configuração
- Variáveis de ambiente novas (adicionar a .env.example, backend/.env, frontend/.env.local):
  - AUTH_JWT_SECRET=<string-32>
  - AUTH_JWT_REFRESH_SECRET=<string-32>
  - AUTH_ACCESS_TOKEN_TTL_MIN=15
  - AUTH_REFRESH_TOKEN_TTL_DAYS=7
  - AUTH_COOKIE_DOMAIN=<domínio>
  - AUTH_SECURE_COOKIES=true  # false somente em dev local com http
- Dependências backend: python-jose[cryptography], passlib[bcrypt], email-validator.
- Dependências frontend: npm install yup @hookform/resolvers react-hook-form (se ainda não presente).

Arquitetura de Alto Nível
- Application Layer: `backend/src/application/services/auth_service.py` para orquestrar registro e login.
- Domain Layer: `backend/src/domain/entities/user.py` e value objects para validação de senha/e-mail.
- Infrastructure: `backend/src/infrastructure/repositories/user_repository.py` com persistência MongoDB e hashing.
- Presentation: `backend/src/presentation/api/v1/auth_router.py` expondo rotas REST com FastAPI e responses padronizadas.
- Frontend: Contexto `frontend/src/context/AuthContext.jsx` para estado global + `frontend/src/services/auth.service.js` para chamadas HTTP.

Fluxo de Usuário
1. Usuário acessa `/login` e vê layout seguindo o tema (hero à esquerda, form à direita em desktops, pilha vertical no mobile).
2. Ao clicar em “Criar conta”, abre modal/página `/register` com campos nome, e-mail, senha, confirmar senha.
3. Submissão bem-sucedida cria conta, realiza login automático e redireciona para `/chat`.
4. Login falho exibe mensagens inline e incrementa contagem de tentativas (bloqueio temporário após N falhas configuráveis).
5. Logout limpa contexto, redireciona para `/login` e invalida refresh token no backend.

Modelagem de Dados (MongoDB)
```python
# backend/src/domain/models/user.py
{
    "user_id": str,  # UUID
    "email": str,
    "password_hash": str,
    "full_name": str,
    "roles": ["user"],
    "created_at": datetime,
    "updated_at": datetime,
    "last_login": datetime | None,
    "status": "active" | "pending" | "blocked"
}

# backend/src/domain/models/refresh_token.py
{
    "token_id": str,
    "user_id": str,
    "token_hash": str,
    "expires_at": datetime,
    "created_at": datetime,
    "revoked": bool,
    "ip_address": str | None,
    "user_agent": str | None
}
```

APIs (Propostas)
- `POST /api/v1/auth/register`
  - Request: `{ "full_name": str, "email": EmailStr, "password": str, "accept_terms": bool }`
  - Response 201: `{ "user": { "id": str, "email": str, "full_name": str }, "message": "registered" }`
  - Efeitos: Cria usuário, gera tokens, seta cookies `access_token`, `refresh_token` (HttpOnly, Secure, SameSite=Lax).
- `POST /api/v1/auth/login`
  - Request: `{ "email": EmailStr, "password": str }`
  - Response 200: mesmo payload de register; cookies atualizados.
  - Falha: 401 com `detail` genérico.
- `POST /api/v1/auth/logout`
  - Request body vazio; revoga refresh, limpa cookies.
- `POST /api/v1/auth/refresh`
  - Verifica cookie de refresh, retorna novo access token.
- `GET /api/v1/auth/me`
  - Retorna perfil básico e roles para hidratar o frontend.

Implementação Backend (Diretrizes)
- Validar entradas com Pydantic + value objects (senha mínima 10 chars, letras maiúsculas, minúsculas, número, caractere especial).
- Hash de senha com bcrypt (round >= 12) usando `passlib`.
- Utilizar `datetime.utcnow()` + timezone awareness (docs/development-guidelines.md).
- Reaproveitar serviços conforme task-12; evitar duplicar lógica de tokens.
- Capturar e logar tentativas de login inválidas sem revelar se o e-mail existe.
- Criar testes unitários para serviço de autenticação (register/login) em `backend/tests/application/test_auth_service.py`.

Frontend (Implementação)
- Criar página `frontend/src/pages/LoginPage.jsx` com componentes MUI (`Paper`, `TextField`, `Button`, `Alert`).
- Criar `RegisterPage.jsx` ou modal reutilizando schema de validação via React Hook Form + Yup.
- Atualizar `frontend/src/App.js` para incluir rotas `/login`, `/register` e rota protegida para `/chat` usando wrapper `PrivateRoute`.
- Atualizar `frontend/src/context/AuthContext.jsx` (novo) para gerenciar `user`, `loading`, `login`, `logout`, `register`, usando `auth.service.js`.
- Garantir que `frontend/src/services/auth.service.js` utilize `fetch` ou `axios` com `credentials: 'include'` para enviar cookies.
- Implementar feedback de carregamento e estados de erro com `<LinearProgress />` ou `<Backdrop />` conforme docs/frontend.md.

Validações e Estados de Erro
- Exibir mensagens específicas para campos inválidos (formato de e-mail, senha fraca, termos não aceitos).
- Bloquear botão de submissão enquanto request está em andamento (evitar múltiplos posts).
- Exibir banner genérico para `401`/`500` retornados pelo backend.
- Considerar throttle client-side (desabilitar login por 5s após 3 falhas consecutivas).

Segurança & Compliance
- Cookies HttpOnly + Secure (usar flag `AUTH_SECURE_COOKIES` para ambiente).
- SameSite=Lax para evitar CSRF básico; para endpoints state-changing, exigir CSRF token? (planejar mas fora do MVP).
- Sanitizar campos de entrada (nome) e normalizar e-mail para lowercase antes de salvar.
- Registrar auditoria mínima em `backend/src/infrastructure/logging/audit_logger.py` (novo) com evento login_success/login_failed/logout.

Identidade Visual e UX
- Utilizar paleta primária definida no tema MUI (`theme.palette.primary.main`, `secondary.main`).
- Inclusão do logo disponível em `frontend/src/assets/logo.svg` (ou placeholder) alinhado à esquerda.
- Tipografia: `Typography` variantes `h4` para headline, `body2` para links.
- Responsividade: Grid de 12 colunas; breakpoint sm empilha form e hero.
- Acessibilidade: labels explícitos, `aria-live` para mensagens de erro, foco visível.

Testes (Manual & Automatizados)
- Manual: registrar novo usuário, validar redirecionamento ao chat, tentar login com senha errada, validar mensagem.
- Manual: realizar logout e garantir que rota `/chat` bloqueia acesso e redireciona para `/login`.
- Automatizado: testes unitários backend (register, login com senha errada, refresh expirado).
- Automatizado: testes de componentes com React Testing Library simulando submissão e estados de erro.

Entregáveis do PR
- Novos endpoints de autenticação com testes (backend `src/presentation/api/v1/auth_router.py` + casos de uso).
- Contexto de autenticação + páginas `Login` e `Register` com testes básicos.
- Atualização de `frontend/src/services/auth.service.js` para novos métodos.
- Documentação em `docs/authentication.md` (seções de fluxo atualizado) e nova entrada em `docs/README.md` se necessário.
- Atualização de `.env.example` (root ou backend/frontend) com novas variáveis.
- Scripts npm/pytest executados: `npm run lint`, `npm run test`, `pytest` (backend).

Checklists Úteis
- agents/security-check.md: revisar checklist CSRF, armazenamento seguro, rate limiting.
- agents/frontend-development.md: acessibilidade, estados de carregamento, organização de componentes.
- agents/backend-development.md: padrões de resposta, validação, logging.
- docs/testing.md: matriz de testes unitários e e2e futura.

Notas
- Utilizar UUID4 para IDs de usuário e tokens.
- Planejar integração futura com provedores sociais, manter design extensível.
- Garantir que logout também invalide sessões WebSocket ativas (registrar TODO se não implementado).
