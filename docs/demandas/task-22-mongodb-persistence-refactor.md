# Prompt: Refatorar Persistência MongoDB e Rotas de Projetos

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, database, QA).
- Referências úteis: docs/backend.md, docs/database.md, docs/development-guidelines.md, agents/backend-development.md, agents/database-development.md, agents/qa-agent.md.

Objetivo
- Corrigir a integração com MongoDB garantindo persistência funcional para projetos e mensagens.
- Eliminar retornos de corrotinas não resolvidas nas rotas REST (uso consistente de `await`).
- Reestruturar serviços e repositórios aplicando SOLID, separando responsabilidades em módulos menores e fáceis de testar.

Escopo
- Revisar `backend/src/presentation/api/project_routes.py` para aplicar `await` em todas as chamadas assíncronas e organizar handlers.
- Extrair um repositório MongoDB dedicado (ex.: `backend/src/infrastructure/repositories/project_repository.py`) com CRUD completo.
- Atualizar `ProjectService` para usar o repositório em vez de chamar utilitários diretos do `MongoDB` singleton.
- Ajustar o gerenciador `backend/src/infrastructure/database/mongodb.py` para expor métodos de obtenção de coleção/cliente, sem conter lógica de negócio.
- Garantir que as rotas REST recebam responses serializadas (`dict`) e não modelos Pydantic/Beanie crus.
- Cobrir o fluxo com testes automatizados (unitários para repositório/serviço e integração para rotas).

Requisitos de Configuração
- Validar variáveis `DB_MONGODB_URL` e `DB_DATABASE_NAME` em `.env` e `docker-compose`.
- Assegurar que coleções necessárias estejam indexadas (seguir docs/database.md para criação de índices via Beanie ou comandos iniciais).
- Manter compatibilidade com a infraestrutura existente (Beanie/Motor) e pipelines de CI.

Arquitetura de Alto Nível
- `MongoDB` manager: responsável apenas por conexão/configuração.
- `ProjectRepository`: interface + implementação MongoDB (CRUD, consultas especializadas, conversão para entidades domain).
- `ProjectService`: orquestra regras de negócio, chama repositório e emite eventos (futuro).
- `ProjectRoutes`: apenas valida entrada, chama service e devolve DTOs.

Princípios e Boas Práticas
- Aplicar SOLID: SRP (cada classe com responsabilidade única), DIP (serviço depende de interface do repositório), LSP ao criar mocks/stubs.
- Usar `try/except` pontuais e com logging estruturado; evitar blocos enormes em rotas.
- Normalizar conversão entre entidades Domain ↔ DTO sem acoplamento à camada de infra.
- Documentar caminhos de erro (404, 500) e retornar códigos padronizados.

Testes (Manual & Automatizados)
- Unitários: `tests/unit/test_project_repository.py`, `tests/unit/test_project_service.py` cobrindo cenários de sucesso/erro.
- Integração: `tests/integration/test_project_routes.py` com client FastAPI simulando chamadas (usando MongoDB de teste ou mock do Motor).
- QA Manual: criar projeto via `/api/projects/create`, listar, atualizar e buscar por ID garantindo respostas corretas.

Entregáveis do PR
- Novos arquivos de repositório + refatoração do `ProjectService` e rotas.
- Ajustes no `MongoDB` manager conforme arquitetura descrita.
- Testes automatizados rodando em CI (`pytest`).
- Atualização de documentação (`docs/backend.md` / `docs/database.md`) descrevendo fluxo de persistência refatorado.
- Registro no CHANGELOG ou release notes indicando breaking changes (se aplicável).

Notas
- Preparar migração de dados se estrutura/coleção mudar; documentar script em `scripts/migrations` (se necessário).
- Verificar se outros serviços (ChatService, ProjectManager) precisam apontar para o novo repositório.
- Manter compatibilidade com instâncias locais e Railway.
