# 🚂 Railway Deployment Guide

Este guia explica como configurar o projeto no Railway para criar múltiplos serviços automaticamente.

## 📋 Pré-requisitos

1. Conta no Railway: https://railway.app
2. Repositório GitHub vinculado
3. API Keys configuradas (OpenRouter)

## 🏗️ Arquitetura no Railway

O projeto será dividido em **4 serviços separados**:

1. **Backend** - API Python FastAPI
2. **Frontend** - React + Nginx
3. **MongoDB** - Banco de dados
4. **MinIO** - Object Storage

## 📦 Passo 1: Criar Projeto no Railway

1. Acesse [Railway Dashboard](https://railway.app/dashboard)
2. Clique em **"New Project"**
3. Selecione **"Deploy from GitHub repo"**
4. Escolha o repositório: `agente-engenharia`
5. Railway vai detectar automaticamente o projeto

## 🔧 Passo 2: Adicionar Serviços Manualmente

### 2.1 Backend Service

1. No projeto Railway, clique em **"+ New"** → **"Service"**
2. Selecione **"GitHub Repo"** → Seu repositório
3. **IMPORTANTE - Configure o Root Directory**:
   - Vá em **Settings** (tab superior)
   - Na seção **Source** → **Root Directory**
   - Digite: `backend` (sem barra no final)
   - Clique em **Save**

4. **Configure o Build**:
   - Vá em **Settings** → **Build**
   - **Builder**: DOCKERFILE
   - **Dockerfile Path**: Deixe vazio ou `Dockerfile` (Railway procura na root configurada)
   - Clique em **Save**

5. **Configure o Deploy**:
   - Vá em **Settings** → **Deploy**
   - **Start Command**: Deixe vazio (o Dockerfile tem ENTRYPOINT configurado)
   - **Restart Policy**: ON_FAILURE com 3 tentativas
   - Clique em **Save**

6. **Variáveis de Ambiente** (Settings → Variables):

   ⚠️ **IMPORTANTE**: Substitua `sk-or-v1-your-key-here` pela sua chave real da OpenRouter!

   ```env
   ENVIRONMENT=production
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   CHAT_MODEL=x-ai/grok-4-fast
   VISION_MODEL=google/gemini-2.5-flash-image-preview
   MONGODB_URL=${{MongoDB.MONGO_URL}}
   MINIO_ENDPOINT=${{MinIO.RAILWAY_PRIVATE_DOMAIN}}:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin123
   PYTHONPATH=/app
   PYTHONUNBUFFERED=1
   ```

   **Como obter a OPENROUTER_API_KEY:**
   1. Acesse https://openrouter.ai/keys
   2. Faça login com sua conta
   3. Clique em "Create Key"
   4. Copie a chave (começa com `sk-or-v1-...`)
   5. Cole no Railway

7. **Configure Networking**:
   - Settings → Networking → Generate Domain (Railway cria URL pública)

8. **Trigger Deploy**:
   - Volte na tab **Deployments**
   - Clique em **Deploy** ou faça um push no GitHub

### 2.2 Frontend Service

1. Clique em **"+ New"** → **"Service"**
2. Selecione **"GitHub Repo"** → Seu repositório

3. **IMPORTANTE - Configure o Root Directory**:
   - Vá em **Settings** (tab superior)
   - Na seção **Source** → **Root Directory**
   - Digite: `frontend` (sem barra no final)
   - Clique em **Save**

4. **Configure o Build**:
   - Vá em **Settings** → **Build**
   - **Builder**: DOCKERFILE
   - **Dockerfile Path**: Deixe vazio ou `Dockerfile`
   - Clique em **Save**

5. **Configure o Deploy**:
   - Vá em **Settings** → **Deploy**
   - **Start Command**: Deixe vazio (o Dockerfile tem CMD configurado)
   - Clique em **Save**

6. **Variáveis de Ambiente** (Settings → Variables):

   ⚠️ **IMPORTANTE**: Adicione `https://` na URL do backend!

   ```env
   NODE_ENV=production
   REACT_APP_BACKEND_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}
   GENERATE_SOURCEMAP=false
   ```

5. **Configure Networking**:
   - Settings → Networking → Generate Domain

### 2.3 MongoDB Service

1. Clique em **"+ New"** → **"Database"** → **"Add MongoDB"**
2. Railway cria automaticamente:
   - **Name**: `MongoDB`
   - **Versão**: MongoDB 7.0
   - **Variáveis geradas automaticamente**:
     - `MONGO_URL`
     - `MONGO_HOST`
     - `MONGO_PORT`
     - `MONGO_USER`
     - `MONGO_PASSWORD`

3. Não precisa configurar nada adicional!

### 2.4 MinIO Service

⚠️ **Railway não tem MinIO nativo, use uma das alternativas:**

#### Opção A: Docker Image (Recomendado)

1. Clique em **"+ New"** → **"Empty Service"**
2. Configure:
   - **Name**: `minio`
   - **Image**: `minio/minio:latest`
   - **Start Command**: `minio server /data --console-address ":9001"`

3. **Variáveis de Ambiente**:
   ```env
   MINIO_ROOT_USER=minioadmin
   MINIO_ROOT_PASSWORD=minioadmin123
   MINIO_DEFAULT_BUCKETS=construction-images,construction-documents
   ```

4. **Configure Volumes** (Settings → Volumes):
   - Mount Path: `/data`
   - Size: 10GB

5. **Configure Networking**:
   - Port 9000 (API)
   - Port 9001 (Console)
   - Generate Domain para o Console

#### Opção B: Usar AWS S3 / Cloudflare R2

Se preferir um serviço gerenciado externo:

1. Crie bucket no [AWS S3](https://aws.amazon.com/s3/) ou [Cloudflare R2](https://www.cloudflare.com/products/r2/)
2. Configure as variáveis no Backend:
   ```env
   MINIO_ENDPOINT=s3.amazonaws.com
   MINIO_ACCESS_KEY=your-aws-access-key
   MINIO_SECRET_KEY=your-aws-secret-key
   MINIO_BUCKET_NAME=construction-files
   ```

## 🔗 Passo 3: Conectar Serviços

O Railway usa **variáveis de referência** para conectar serviços:

### No Backend, use:
```env
MONGODB_URL=${{MongoDB.MONGO_URL}}
MINIO_ENDPOINT=${{MinIO.RAILWAY_PRIVATE_DOMAIN}}:9000
```

### No Frontend, use:
```env
REACT_APP_BACKEND_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}
```

## 🚀 Passo 4: Deploy

1. Após configurar todos os serviços, clique em **"Deploy"** em cada um
2. Railway vai:
   - Detectar Dockerfiles
   - Fazer build das imagens
   - Criar containers
   - Gerar URLs públicas

3. Ordem recomendada de deploy:
   1. MongoDB (primeiro)
   2. MinIO (segundo)
   3. Backend (terceiro - depende de MongoDB e MinIO)
   4. Frontend (último - depende do Backend)

## 📊 Monitoramento

### Backend Health Check
```bash
curl https://your-backend.railway.app/health
```

### Frontend Health Check
```bash
curl https://your-frontend.railway.app/
```

### Logs
- Railway Dashboard → Seu Serviço → Deployments → View Logs

## 🔐 Variáveis de Ambiente Críticas

### Backend (Obrigatórias)
- `OPENROUTER_API_KEY` - Sua chave da OpenRouter
- `MONGODB_URL` - Conexão MongoDB (gerada automaticamente)
- `MINIO_ENDPOINT` - Endpoint do MinIO
- `MINIO_ACCESS_KEY` - Chave de acesso MinIO
- `MINIO_SECRET_KEY` - Senha MinIO

### Frontend (Obrigatórias)
- `REACT_APP_BACKEND_URL` - URL pública do backend

## 💰 Custos Estimados

| Serviço | Recursos | Custo/mês (aprox.) |
|---------|----------|-------------------|
| Backend | 2GB RAM, 1 vCPU | $10-15 |
| Frontend | 512MB RAM, 0.25 vCPU | $3-5 |
| MongoDB | 1GB Storage | $5 (pode usar Free Tier) |
| MinIO | 10GB Storage | $5-10 |
| **Total** | | **$23-35/mês** |

💡 **Dica**: Railway oferece $5 de crédito grátis/mês no plano gratuito!

## 🐛 Troubleshooting

### ❌ Erro: "Dockerfile does not exist"

**Sintoma:**
```
Dockerfile `Dockerfile` does not exist
[Region: us-east4]
```

**Causa:** Railway não está encontrando o Dockerfile porque o **Root Directory** não foi configurado corretamente.

**✅ Solução:**

1. **Vá em Settings → Source → Root Directory**
2. **Digite exatamente**: `backend` (sem `/` no início ou fim)
3. **Clique em Save**
4. **Vá em Settings → Build**
5. **Dockerfile Path**: Deixe vazio ou apenas `Dockerfile`
6. **Clique em Save**
7. **Trigger novo deploy**: Deployments → Redeploy

**Explicação:** O Railway procura o Dockerfile relativo ao Root Directory. Se você configurou `backend/` como root, ele vai procurar em `backend/Dockerfile` (correto), mas se não configurou, ele procura na raiz do repo (incorreto).

---

### ❌ Erro: "Invalid value for '--port': '$PORT' is not a valid integer"

**Sintoma:**
```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
Usage: python -m uvicorn [OPTIONS] APP
```

**Causa:** A variável `$PORT` do Railway não está sendo expandida corretamente no comando.

**✅ Solução:**

O projeto já foi corrigido! Agora usa um `entrypoint.sh` que lida com a variável PORT corretamente.

**Se ainda ocorrer:**

1. **Vá em Settings → Deploy**
2. **Start Command**: **Deixe completamente VAZIO**
3. **Clique em Save**
4. **Redeploy**

**Explicação:** O Railway injeta automaticamente a variável `PORT` no ambiente. O Dockerfile agora usa um script `entrypoint.sh` que lê `$PORT` corretamente e inicia o uvicorn com a porta dinâmica.

---

### ❌ Erro: "Field required: mongodb_url"

**Sintoma:**
```
ValidationError: 1 validation error for DatabaseSettings
mongodb_url
  Field required [type=missing]
RuntimeError: MongoDB connection is required to start the application
```

**Causa:** O serviço MongoDB não foi criado OU a variável `MONGODB_URL` não está configurada.

**✅ Solução:**

**1. Criar serviço MongoDB:**
- No Railway, clique em **"+ New" → "Database" → "Add MongoDB"**
- Railway cria automaticamente o serviço

**2. Configurar variável no Backend:**
- Backend → Settings → Variables
- Adicione: `MONGODB_URL=${{MongoDB.MONGO_URL}}`
- Clique em "Add"

**3. Aguarde redeploy automático**

**Nota:** O código agora aceita tanto `MONGODB_URL` quanto `DB_MONGODB_URL`.

---

### ❌ Erro: "Field required: openrouter_api_key"

**Sintoma:**
```
ValidationError: 1 validation error for Settings
openrouter_api_key
  Field required [type=missing]
ERROR: Application startup failed. Exiting.
```

**Causa:** A variável de ambiente `OPENROUTER_API_KEY` não foi configurada no Railway.

**✅ Solução:**

1. **Vá em Settings → Variables**
2. **Clique em "New Variable"**
3. **Nome**: `OPENROUTER_API_KEY`
4. **Valor**: Sua chave da OpenRouter (começa com `sk-or-v1-...`)
5. **Clique em "Add"**
6. **Aguarde o redeploy automático**

**Como obter a chave:**
- Acesse https://openrouter.ai/keys
- Faça login e clique em "Create Key"
- Copie a chave gerada

---

### ⚠️ Warning: "matplotlib permissions" / "fontconfig errors"

**Sintoma:**
```
mkdir -p failed for path /home/appuser/.config/matplotlib
Fontconfig error: No writable cache directories
```

**Causa:** Usuário não-root não tem permissão para criar diretórios de cache.

**Status:** ✅ Já corrigido no Dockerfile mais recente!

Se ainda ocorrer, adicione estas variáveis de ambiente:
```env
MPLCONFIGDIR=/tmp/matplotlib
FONTCONFIG_PATH=/etc/fonts
```

---

### Backend não conecta no MongoDB
```
❌ Error: Connection refused
✅ Solução: Verifique se MONGODB_URL usa ${{MongoDB.MONGO_URL}}
```

### Frontend não carrega Backend
```
❌ Error: CORS / Network Error
✅ Solução: Configure CORS_ORIGINS no backend com a URL do frontend
```

### MinIO não inicia
```
❌ Error: Cannot start minio
✅ Solução: Adicione volume persistente em Settings → Volumes
```

### Build falha no Railway
```
❌ Error: Docker build failed
✅ Solução: Verifique se Dockerfile está na raiz do serviço
          Railway Root Directory deve apontar para backend/ ou frontend/
```

## 📚 Documentação Oficial

- [Railway Docs](https://docs.railway.app/)
- [Railway Multi-Service](https://docs.railway.app/guides/projects#multiple-services)
- [Railway Docker Deployment](https://docs.railway.app/guides/dockerfiles)
- [Railway Environment Variables](https://docs.railway.app/guides/variables)

## 🎉 Verificação de Sucesso

### Backend está funcionando quando você vê nos logs:

```
✅ Connected to MongoDB: construction_agent
✅ MongoDB connected successfully
✅ Using OpenRouter with model: x-ai/grok-4-fast
✅ Visual Agent initialized with model: google/gemini-2.5-flash-image-preview
✅ Agent Factory initialized successfully
✅ System initialized successfully
✅ Application startup complete
```

### Teste o Backend:

1. **Health Check:**
   ```bash
   curl https://your-backend-url.railway.app/health
   ```

   Deve retornar:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "version": "2.0.0"
   }
   ```

2. **API Docs:**
   - Acesse: `https://your-backend-url.railway.app/docs`
   - Deve abrir a interface Swagger UI

### ⚠️ Warnings Conhecidos (não críticos):

```
ERROR: Prompts file not found at /app/config/prompts.yaml
```
- **Status:** ✅ Corrigido no Dockerfile
- **Impacto:** Nenhum - sistema usa prompts default
- **Próximo deploy:** Arquivo será copiado corretamente

```
WARNING: Auth router not available
```
- **Status:** ✅ Corrigido adicionando email-validator
- **Impacto:** Endpoints de autenticação habilitados

## 🎯 Próximos Passos

1. ✅ Backend funcionando
2. ✅ MongoDB conectado
3. ⏳ Configure Frontend service
4. ⏳ Configure MinIO/S3 para uploads
5. ⏳ Configure domínio customizado (opcional)
6. ⏳ Configure CI/CD com GitHub Actions

---

**Precisa de ajuda?** Consulte os logs no Railway Dashboard ou abra uma issue no GitHub.