# Prompt: Ativar API de Storage MinIO e Refatorar Integração

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, infrastructure, storage, security).
- Referências úteis: docs/backend.md, docs/infrastructure.md (se existir), docs/storage.md, agents/backend-development.md, agents/security-check.md.

Objetivo
- Garantir que os endpoints de upload/download MinIO estejam disponíveis e funcionando na API.
- Refatorar a integração de storage seguindo SOLID, evitando instâncias ad-hoc e aplicando TRY controlado.
- Assegurar que a inicialização da aplicação configure o MinIOStorageService e verifique dependências críticas.

Escopo
- Montar `backend/src/presentation/api/storage_routes.py` no FastAPI (`backend/main.py`) com prefixo adequado e autenticação.
- Criar camada de DI/Factory para `MinIOStorageService`, reutilizando configurações de ambiente e evitando múltiplas instâncias.
- Revisar `storage_routes.py` para extrair utilitários (ex.: logging, validação, conversão de resposta) em helpers ou classes menores.
- Adicionar health check/startup que valide conexão MinIO e crie buckets obrigatórios (isolando em módulo `infrastructure/storage/setup.py`).
- Garantir que outros componentes (QuotaService, ImageProcessor) recebam dependências via constructor/Depends.
- Documentar processos de configuração (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_DEFAULT_BUCKET`).

Requisitos de Configuração
- Confirmar variáveis MinIO em `.env`/Railway.
- Validar existência de buckets necessários (`construction-files`, `construction-images`, etc.).
- Garantir permissões corretas para uploads (policy pública para thumbnails conforme docs).

Arquitetura de Alto Nível
- `MinioClientFactory` (novo) cria serviço configurado com retries/logs.
- `StorageService`/`QuotaService` recebem instâncias via DI (FastAPI Depends).
- Routes chamam serviços desacoplados e retornam DTOs padronizados.
- Startup event registra health check e logs (sucedido/falhou).

Princípios e Boas Práticas
- Aplicar SOLID: separar lógica de upload, logs, quotas em classes específicas.
- Usar `try/except` apenas em I/O com mensagens claras e `logger.bind(bucket=..., user=...)`.
- Validar dados de entrada via Pydantic (ex.: `FileUploadRequest`).
- Garantir testes cobrindo erros de conexão, quotas, validação de arquivo.

Testes (Manual & Automatizados)
- Unitários: mocks do MinIO client validando upload/download, quotas e exceções.
- Integração: rodar `tests/integration/test_storage_routes.py` usando MinIO local (docker) ou moto/s3 compatível.
- QA Manual: upload via `/api/storage/upload`, download via `/api/storage/files/{id}` e verificar thumbnails.

Entregáveis do PR
- Atualização do `main.py` com router e DI, novos módulos factory/setup.
- Refatoração de rotas/serviços conforme descrito.
- Testes automatizados e documentação atualizada (`docs/storage.md`, `.env.example`).
- Notas de migração (se endpoints ou auth mudarem).

Notas
- Verificar impacto em componentes que já chamam `StorageService` local (chat, project, reports).
- Considerar métricas (uploads por bucket) e logging centralizado.
- Planejar fallback/local storage para ambientes sem MinIO (flag de configuração).
