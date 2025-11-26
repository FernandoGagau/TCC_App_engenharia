# ✅ Railway Deployment Checklist

Use este checklist para garantir que todos os serviços estão configurados corretamente.

## 📦 Serviços a Criar

- [ ] MongoDB Database
- [ ] Backend Service
- [ ] Frontend Service
- [ ] MinIO/S3 Storage (opcional)

---

## 1️⃣ MongoDB Database

### Criar Serviço
- [ ] Railway Dashboard → "+ New" → "Database" → "Add MongoDB"
- [ ] Aguardar criação (~30 segundos)
- [ ] Verificar status: "Active"

### Variáveis Geradas Automaticamente
- [ ] `MONGO_URL` (gerado pelo Railway)
- [ ] `MONGO_HOST`
- [ ] `MONGO_PORT`

✅ **Pronto!** MongoDB não precisa de configuração adicional.

---

## 2️⃣ Backend Service

### Criar Serviço
- [ ] Railway Dashboard → "+ New" → "Service"
- [ ] Selecionar "GitHub Repo" → `agente-engenharia`

### ⚙️ Settings → Source
- [ ] **Root Directory**: `backend` (sem barra)
- [ ] **Branch**: `main` ou `refinamento`
- [ ] Clicar em **Save**

### 🏗️ Settings → Build
- [ ] **Builder**: DOCKERFILE
- [ ] **Dockerfile Path**: (deixar vazio ou `Dockerfile`)
- [ ] Clicar em **Save**

### 🚀 Settings → Deploy
- [ ] **Start Command**: (deixar VAZIO)
- [ ] **Restart Policy**: ON_FAILURE com 3 retries
- [ ] Clicar em **Save**

### 🔐 Settings → Variables
Adicionar estas variáveis:

- [ ] `ENVIRONMENT` = `production`
- [ ] `OPENROUTER_API_KEY` = `sk-or-v1-[sua-chave]` ⚠️ **Obrigatória!**
- [ ] `OPENROUTER_BASE_URL` = `https://openrouter.ai/api/v1`
- [ ] `CHAT_MODEL` = `x-ai/grok-4-fast`
- [ ] `VISION_MODEL` = `google/gemini-2.5-flash-image-preview`
- [ ] `MONGODB_URL` = `${{MongoDB.MONGO_URL}}` ⚠️ **Obrigatória!**
- [ ] `PYTHONPATH` = `/app`
- [ ] `PYTHONUNBUFFERED` = `1`

### 🌐 Settings → Networking
- [ ] Clicar em **Generate Domain**
- [ ] Copiar a URL gerada (usar no frontend)

### ✅ Verificar Deploy
- [ ] Aguardar build completar
- [ ] Ver logs: deve aparecer "Application startup complete"
- [ ] Testar: `curl https://[seu-backend].railway.app/health`

---

## 3️⃣ Frontend Service

### Criar Serviço
- [ ] Railway Dashboard → "+ New" → "Service"
- [ ] Selecionar "GitHub Repo" → `agente-engenharia`

### ⚙️ Settings → Source
- [ ] **Root Directory**: `frontend` (sem barra) ⚠️ **IMPORTANTE!**
- [ ] **Branch**: `main` ou `refinamento`
- [ ] Clicar em **Save**

### 🏗️ Settings → Build
- [ ] **Builder**: DOCKERFILE
- [ ] **Dockerfile Path**: (deixar vazio ou `Dockerfile`)
- [ ] Clicar em **Save**

### 🚀 Settings → Deploy
- [ ] **Start Command**: (deixar VAZIO)
- [ ] **Restart Policy**: ON_FAILURE com 3 retries
- [ ] Clicar em **Save**

### 🔐 Settings → Variables
Adicionar estas variáveis:

- [ ] `NODE_ENV` = `production`
- [ ] `REACT_APP_BACKEND_URL` = `https://${{backend.RAILWAY_PUBLIC_DOMAIN}}` ⚠️ **Com https://!**
- [ ] `GENERATE_SOURCEMAP` = `false`

### 🌐 Settings → Networking
- [ ] Clicar em **Generate Domain**
- [ ] Copiar a URL gerada (esse é o link público da aplicação)

### ✅ Verificar Deploy
- [ ] Aguardar build completar
- [ ] Acessar URL do frontend no navegador
- [ ] Deve carregar a interface React

---

## 4️⃣ MinIO/S3 Storage (Opcional)

### Opção A: MinIO no Railway

#### Criar Serviço
- [ ] Railway Dashboard → "+ New" → "Empty Service"
- [ ] **Image**: `minio/minio:latest`
- [ ] **Start Command**: `minio server /data --console-address ":9001"`

#### Variables
- [ ] `MINIO_ROOT_USER` = `minioadmin`
- [ ] `MINIO_ROOT_PASSWORD` = `minioadmin123`

#### Volumes
- [ ] Settings → Volumes → Add Volume
- [ ] **Mount Path**: `/data`
- [ ] **Size**: 10GB

#### Networking
- [ ] Port 9000 (API)
- [ ] Port 9001 (Console)
- [ ] Generate Domain

#### Adicionar no Backend
- [ ] Backend → Variables → `MINIO_ENDPOINT` = `${{MinIO.RAILWAY_PRIVATE_DOMAIN}}:9000`
- [ ] `MINIO_ACCESS_KEY` = `minioadmin`
- [ ] `MINIO_SECRET_KEY` = `minioadmin123`

### Opção B: AWS S3 ou Cloudflare R2 (Recomendado)

- [ ] Criar bucket no [AWS S3](https://aws.amazon.com/s3/) ou [Cloudflare R2](https://www.cloudflare.com/products/r2/)
- [ ] Adicionar no Backend:
  - [ ] `MINIO_ENDPOINT` = `s3.amazonaws.com` ou R2 endpoint
  - [ ] `MINIO_ACCESS_KEY` = sua access key
  - [ ] `MINIO_SECRET_KEY` = sua secret key

---

## 🧪 Testes Finais

### Backend Health Check
```bash
curl https://[seu-backend].railway.app/health
```

**Esperado:**
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "2.0.0"
}
```

### Backend API Docs
- [ ] Abrir: `https://[seu-backend].railway.app/docs`
- [ ] Deve mostrar Swagger UI

### Frontend
- [ ] Abrir: `https://[seu-frontend].railway.app`
- [ ] Deve carregar a interface
- [ ] Testar login/criar conta
- [ ] Testar criar novo projeto

### Logs
- [ ] Backend logs: "Application startup complete"
- [ ] Frontend logs: "Build completed"
- [ ] MongoDB logs: "Connection accepted"

---

## 🚨 Troubleshooting

### Backend não inicia
- [ ] Verificar `OPENROUTER_API_KEY` está configurada
- [ ] Verificar `MONGODB_URL=${{MongoDB.MONGO_URL}}`
- [ ] Ver logs: Deployments → View Logs

### Frontend não carrega backend
- [ ] Verificar `REACT_APP_BACKEND_URL` tem `https://`
- [ ] Verificar backend está no ar
- [ ] Ver console do navegador (F12) para erros CORS

### "Dockerfile does not exist"
- [ ] Verificar Root Directory está configurado (`backend` ou `frontend`)
- [ ] Verificar spelling correto (sem barra no final)

---

## ✅ Checklist de Sucesso

- [ ] ✅ MongoDB: Status "Active"
- [ ] ✅ Backend: Logs mostram "Application startup complete"
- [ ] ✅ Backend: Health check retorna 200 OK
- [ ] ✅ Backend: `/docs` abre Swagger UI
- [ ] ✅ Frontend: Site carrega no navegador
- [ ] ✅ Frontend: Consegue fazer login
- [ ] ✅ Frontend: Consegue criar projeto

---

## 🎉 Pronto!

Se todos os checkboxes acima estão marcados, sua aplicação está 100% funcional no Railway!

**URLs Importantes:**
- Backend API: `https://[seu-backend].railway.app`
- Frontend App: `https://[seu-frontend].railway.app`
- API Docs: `https://[seu-backend].railway.app/docs`

**Próximos Passos:**
- Configure domínio customizado (opcional)
- Configure CI/CD automático
- Configure monitoramento com Railway Metrics