# Storage Configuration - MinIO

Este projeto utiliza MinIO como storage padrão para armazenamento de imagens e documentos.

## 🚀 Quick Start

### 1. Iniciar MinIO
```bash
# Inicializar MinIO com buckets
./backend/scripts/init-minio.sh

# Ou manualmente
docker-compose up -d minio
```

### 2. Acessar MinIO Console
- **URL**: http://localhost:9001
- **Usuário**: minioadmin
- **Senha**: minioadmin123

### 3. Verificar Buckets
Os seguintes buckets são criados automaticamente:
- `construction-images` - Imagens de obras (fotos, análises visuais)
- `construction-documents` - Documentos (PDFs, planilhas)

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```env
# Storage Configuration (MinIO/S3)
STORAGE_TYPE=s3
STORAGE_BUCKET=construction-images
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin123
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:9000
```

### Alterando para AWS S3

Para usar AWS S3 ao invés de MinIO:

```env
STORAGE_TYPE=s3
STORAGE_BUCKET=seu-bucket-aws
AWS_ACCESS_KEY_ID=sua-access-key
AWS_SECRET_ACCESS_KEY=sua-secret-key
AWS_REGION=us-east-1
# Remover ou deixar vazio para usar AWS S3
AWS_ENDPOINT_URL=
```

### Usando Storage Local

Para desenvolvimento sem MinIO:

```env
STORAGE_TYPE=local
STORAGE_BASE_PATH=backend/storage
```

## 📂 Estrutura de Armazenamento

Arquivos são organizados por:
```
{project_id}/
  ├── attachments/          # Anexos enviados via chat
  ├── construction/         # Fotos de obra
  ├── bim/                  # Modelos BIM
  └── documents/            # Documentos gerais
```

## 🔧 Troubleshooting

### MinIO não inicia
```bash
# Verificar logs
docker-compose logs minio

# Reiniciar
docker-compose restart minio
```

### Erro de conexão
- Verifique se MinIO está rodando: `docker ps | grep minio`
- Teste conexão: `curl http://localhost:9000/minio/health/live`

### Buckets não existem
```bash
# Executar script de inicialização
./backend/scripts/init-minio.sh
```

## 🔐 Segurança em Produção

**IMPORTANTE**: Em produção, altere as credenciais padrão!

```yaml
# docker-compose.yml
environment:
  MINIO_ROOT_USER: ${MINIO_ROOT_USER}
  MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
```

```env
# .env
MINIO_ROOT_USER=seu-usuario-seguro
MINIO_ROOT_PASSWORD=sua-senha-forte-aqui
```

## 📊 Monitoramento

- **Console Web**: http://localhost:9001
- **API Endpoint**: http://localhost:9000
- **Health Check**: http://localhost:9000/minio/health/live

## 🔄 Backup

Para fazer backup dos dados do MinIO:

```bash
# Backup do volume
docker run --rm -v agente-engenharia_minio_data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/minio-backup-$(date +%Y%m%d).tar.gz /data

# Restore
docker run --rm -v agente-engenharia_minio_data:/data -v $(pwd)/backup:/backup alpine tar xzf /backup/minio-backup-YYYYMMDD.tar.gz -C /
```

## 📚 Referências

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html)
- [AWS S3 boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html)
