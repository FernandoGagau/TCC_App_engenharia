# Prompt: Unificar Dockerfiles e Configurações Railway

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, infrastructure, devops).
- Referências úteis: agents/architecture-planning.md, agents/backend-development.md, agents/frontend-development.md, agents/security-check.md, docs/deployment.md (se existir) e docs/development-guidelines.md.

Objetivo
- Eliminar duplicações e inconsistências nos Dockerfiles do backend e frontend, criando imagens enxutas e alinhadas ao fluxo de CI/CD.
- Padronizar as configurações `railway.toml` (backend e frontend) garantindo provisionamento automático de serviços dependentes (MongoDB, MinIO, Redis, etc.).
- Assegurar que a subida do backend no Railway acione a infraestrutura completa necessária e que o frontend tenha configuração equivalente.

Escopo
- Backend: revisar `backend/Dockerfile` (ou múltiplos Dockerfiles) consolidando build multi-stage (base, deps, runtime) e suporte a testes.
- Frontend: revisar `frontend/Dockerfile`, removendo redundâncias e otimizar para build estático/SSR conforme necessidade do projeto.
- Infraestrutura: garantir que docker-compose ou scripts relacionados estejam consistentes com novos Dockerfiles.
- Railway: atualizar `backend/railway.toml` e `frontend/railway.toml` para declarar serviços, environment groups e build/deploy hooks corretos.
- Documentação: registrar instruções claras para desenvolvedores e para o time de DevOps sobre a sequência de deploy.

Requisitos de Configuração
- Confirmar variáveis obrigatórias para backend (`MONGO_URI`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, etc.) e frontend (URLs de API, chaves públicas) nas seções `env` dos `railway.toml`.
- Definir `deploy`/`build` dentro dos `.toml` apontando para Dockerfile correto (`dockerfilePath`) e comando de start coerente.
- Verificar se Railway Projects possuem `serviceName`, `healthcheckPath`, limites de CPU/RAM adequados.
- Caso necessário, ajustar `.dockerignore` para reduzir tamanho das imagens.

Arquitetura de Alto Nível
- Docker Backend: multi-stage com base Python 3.12 slim → etapa de dependências (pip wheel cache) → etapa final com app + gunicorn/uvicorn.
- Docker Frontend: multi-stage Node 20 builder → etapa final Nginx/serve com assets estáticos.
- Railway Backend: serviço principal (container) + declarações de dependências (MongoDB, MinIO, Redis) usando plugins Railway ou serviços externos; definir ordem de inicialização.
- Railway Frontend: serviço container apontando para Dockerfile otimizado ou build via `npm run build` + static hosting.
- Pipeline: documentar sequência (ex.: backend sobe → aguarda serviços → aplica migrations/seed; frontend sobe após backend saudável).

Verificações Técnicas
- Conferir se variáveis definidas nos `.toml` correspondem às usadas em `backend/main.py`, `backend/src/infrastructure/*`, `frontend/src/config/*`.
- Garantir que comando `CMD`/`ENTRYPOINT` nos Dockerfiles utilize scripts de start da aplicação (ex.: `uvicorn main:app --host 0.0.0.0 --port 8000`).
- Validar compatibilidade com `docker-compose.yml` local (se existir) para manter paridade entre dev e prod.
- Revisar permissões de arquivos, diretórios de logs e volumes persistentes (MinIO data, MongoDB data) no Railway.

Testes (Manual & Automatizados)
- Manual: construir imagens localmente (`docker build backend`, `docker build frontend`) e verificar tempo/tamanho.
- Manual: simular deploy usando Railway CLI (`railway run`) para backend e frontend, confirmando provisionamento de dependências.
- Automatizado: opcionalmente adicionar job em CI para `docker build` de ambos os serviços.
- Validar healthchecks: acessar endpoints/URL após deploy para garantir que serviços sobem sem race conditions.

Entregáveis do PR
- Dockerfiles consolidados e otimizados (`backend/Dockerfile`, `frontend/Dockerfile`) + atualização de `.dockerignore` conforme necessário.
- `backend/railway.toml` e `frontend/railway.toml` revisados com configurações corretas de serviços, envs e deploy.
- Documentação atualizada (ex.: `docs/deployment.md` ou nova página em `docs/infra/railway.md`) explicando fluxo de deploy unificado.
- Se aplicável, ajustes em `docker-compose.yml` e scripts de start para refletir nova padronização.
- Logs de testes/local build anexados na descrição do PR (ex.: `docker build` + Railway CLI).

Notas
- Avaliar criação de imagem base compartilhada se backend e jobs auxiliares utilizarem mesmas dependências (ex.: worker).
- Considerar cache/registry privado para acelerar deploy no Railway.
- Registrar follow-up para monitoramento (ex.: configurar Railway Alerts) após reorganização.
