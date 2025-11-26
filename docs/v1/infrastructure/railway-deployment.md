# 🚀 Guia de Deploy no Railway

## 📋 Visão Geral

Configuração completa para deploy do **Agente de Análise de Engenharia** na plataforma Railway, incluindo backend Python, frontend React, banco PostgreSQL e storage de arquivos.

---

## 🏗️ Arquitetura de Deploy

```mermaid
graph TB
    subgraph "🌐 Railway Cloud"
        subgraph "🔗 Services"
            BE[Backend API<br/>Python FastAPI]
            FE[Frontend<br/>React SPA]
            DB[(PostgreSQL<br/>Database)]
            RD[(Redis<br/>Cache)]
            ST[Volume Storage<br/>Files & Models]
        end

        subgraph "🌍 External APIs"
            OPENAI[OpenAI API]
            LANG[LangChain Services]
        end
    end

    subgraph "👥 Users"
        WEB[Web Browser]
        MOB[Mobile Browser]
    end

    WEB --> FE
    MOB --> FE
    FE --> BE
    BE --> DB
    BE --> RD
    BE --> ST
    BE --> OPENAI
    BE --> LANG
```

---

## 📦 Estrutura de Serviços

### **1. Backend Service (Python API)**
```yaml
Service Name: agente-engenharia-backend
Runtime: Python 3.11
Port: 8000
Resources:
  CPU: 2 vCPU
  Memory: 4GB
  Storage: 20GB SSD
```

### **2. Frontend Service (React)**
```yaml
Service Name: agente-engenharia-frontend
Runtime: Node.js 18
Port: 3000
Resources:
  CPU: 1 vCPU
  Memory: 2GB
  Storage: 5GB SSD
```

### **3. PostgreSQL Database**
```yaml
Service Name: agente-engenharia-db
Engine: PostgreSQL 15
Resources:
  CPU: 1 vCPU
  Memory: 2GB
  Storage: 10GB SSD
  Backup: Daily
```

### **4. Redis Cache**
```yaml
Service Name: agente-engenharia-cache
Engine: Redis 7
Resources:
  Memory: 1GB
  Persistence: RDB + AOF
```

---

## ⚙️ Configuração do Backend

### **railway.json**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "python -m uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### **requirements.txt**
```txt
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# LangChain Ecosystem
langchain==0.1.0
langchain-openai==0.0.8
langchain-community==0.0.10
langchain-experimental==0.0.25
langgraph==0.0.20
langsmith==0.0.69

# Database & ORM
sqlalchemy==2.0.23
alembic==1.13.1
psycopg2-binary==2.9.9
redis==5.0.1

# AI & ML
openai==1.3.7
opencv-python-headless==4.8.1.78
pillow==10.1.0
numpy==1.24.4
torch==2.1.1
torchvision==0.16.1
ultralytics==8.0.206

# Document Processing
langextract==0.4.1
pytesseract==0.3.10
PyPDF2==3.0.1
pdfplumber==0.10.3
python-docx==0.8.11
openpyxl==3.1.2

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
httpx==0.25.2
aiofiles==23.2.1
celery==5.3.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### **Dockerfile (Opcional)**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for uploads and models
RUN mkdir -p uploads models logs

# Expose port
EXPOSE 8000

# Start command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Variáveis de Ambiente (Backend)**
```bash
# Database
DATABASE_URL=postgresql://user:password@hostname:port/dbname
REDIS_URL=redis://hostname:port

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# LangChain
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_PROJECT=agente-engenharia

# Application
SECRET_KEY=your-secret-key-here
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE=50MB

# Storage
UPLOAD_DIR=/app/uploads
MODELS_DIR=/app/models

# External Services
RAILWAY_STATIC_URL=https://your-app.railway.app
FRONTEND_URL=https://your-frontend.railway.app
```

---

## ⚙️ Configuração do Frontend

### **package.json**
```json
{
  "name": "agente-engenharia-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "start": "npm run preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "@mui/material": "^5.15.0",
    "@mui/icons-material": "^5.15.0",
    "@emotion/react": "^11.11.1",
    "@emotion/styled": "^11.11.0",
    "axios": "^1.6.0",
    "socket.io-client": "^4.7.4",
    "zustand": "^4.4.7",
    "react-query": "^3.39.3",
    "react-dropzone": "^14.2.3",
    "three": "^0.158.0",
    "@react-three/fiber": "^8.15.0",
    "@react-three/drei": "^9.88.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.2.2",
    "vite": "^5.0.0"
  }
}
```

### **vite.config.ts**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@mui/material', '@mui/icons-material'],
          three: ['three', '@react-three/fiber', '@react-three/drei']
        }
      }
    }
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV)
  }
})
```

### **Variáveis de Ambiente (Frontend)**
```bash
# API Configuration
VITE_API_BASE_URL=https://your-backend.railway.app
VITE_WS_URL=wss://your-backend.railway.app

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG=false

# External Services
VITE_SENTRY_DSN=https://...
```

---

## 🗄️ Configuração do Banco de Dados

### **Schema Migration (Alembic)**
```python
# alembic/env.py
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base

target_metadata = Base.metadata

def run_migrations_online():
    configuration = context.config
    configuration.set_main_option(
        "sqlalchemy.url",
        os.getenv("DATABASE_URL")
    )

    connectable = engine_from_config(
        configuration.get_section(configuration.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

### **Inicialização do Banco**
```bash
# Comandos para executar no Railway
alembic upgrade head
python scripts/seed_database.py
```

---

## 📦 Deploy Steps

### **1. Preparação do Repositório**
```bash
# 1. Criar repositório no GitHub
git init
git add .
git commit -m "Initial commit: Agente de Engenharia"
git remote add origin https://github.com/username/agente-engenharia.git
git push -u origin main
```

### **2. Configuração no Railway**

#### **Passo 1: Criar Projeto**
1. Acesse [Railway.app](https://railway.app)
2. Clique em "New Project"
3. Selecione "Deploy from GitHub repo"
4. Conecte o repositório `agente-engenharia`

#### **Passo 2: Criar Serviços**
```bash
# Backend Service
- Service Type: Web Service
- Source: GitHub Repository
- Build Path: ./backend
- Start Command: python -m uvicorn main:app --host 0.0.0.0 --port $PORT

# Frontend Service
- Service Type: Web Service
- Source: GitHub Repository
- Build Path: ./frontend
- Build Command: npm run build
- Start Command: npm start

# Database Service
- Service Type: PostgreSQL
- Version: 15
- Storage: 10GB

# Redis Service
- Service Type: Redis
- Version: 7
- Memory: 1GB
```

#### **Passo 3: Configurar Variáveis**
```bash
# Backend Environment Variables
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
OPENAI_API_KEY=sk-your-key-here
LANGCHAIN_API_KEY=ls-your-key-here
SECRET_KEY=your-secret-key
ENVIRONMENT=production

# Frontend Environment Variables
VITE_API_BASE_URL=${{backend.RAILWAY_STATIC_URL}}
VITE_WS_URL=wss://${{backend.RAILWAY_STATIC_URL}}
```

### **3. Configuração de Domínio**
```bash
# Custom Domain (Opcional)
Backend: api.agente-engenharia.com
Frontend: app.agente-engenharia.com

# SSL/TLS
Automático via Railway (Let's Encrypt)
```

---

## 📊 Monitoramento e Logs

### **Railway Observability**
```yaml
Metrics:
  - CPU Usage
  - Memory Usage
  - Request Count
  - Response Time
  - Error Rate

Logs:
  - Application Logs
  - Access Logs
  - Error Logs
  - Database Query Logs

Alerts:
  - High CPU (>80%)
  - High Memory (>90%)
  - High Error Rate (>5%)
  - Database Connection Issues
```

### **Health Check Endpoints**
```python
# backend/main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "services": {
            "database": await check_database(),
            "redis": await check_redis(),
            "openai": await check_openai()
        }
    }
```

---

## 🔧 CI/CD Pipeline

### **GitHub Actions Workflow**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci

      - name: Build frontend
        run: |
          cd frontend
          npm run build

      - name: Run frontend tests
        run: |
          cd frontend
          npm test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Railway
        uses: railwayapp/railway-deploy@v1
        with:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

## 🚀 Comandos de Deploy

### **Deploy Manual via CLI**
```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Link ao projeto
railway link

# 4. Deploy backend
cd backend
railway up

# 5. Deploy frontend
cd ../frontend
railway up

# 6. Verificar status
railway status
```

### **Deploy via Git**
```bash
# Deploy automático no push para main
git add .
git commit -m "feat: implementar análise visual"
git push origin main

# Railway detecta automaticamente e faz deploy
```

---

## 📋 Checklist de Deploy

### **Pré-Deploy**
- [ ] Testes unitários passando
- [ ] Testes de integração passando
- [ ] Variables de ambiente configuradas
- [ ] Banco de dados migrado
- [ ] Assets de build otimizados
- [ ] Health checks implementados

### **Pós-Deploy**
- [ ] Verificar saúde dos serviços
- [ ] Testar endpoints principais
- [ ] Verificar logs de erro
- [ ] Testar upload de arquivos
- [ ] Validar integração com APIs externas
- [ ] Confirmar funcionamento do WebSocket
- [ ] Testar responsividade do frontend

### **Monitoramento Contínuo**
- [ ] Configurar alertas de performance
- [ ] Monitorar uso de recursos
- [ ] Acompanhar métricas de usuário
- [ ] Revisar logs regularmente
- [ ] Backup automático funcionando
- [ ] SSL/TLS válido

---

## 💰 Estimativa de Custos

### **Railway Pricing (Monthly)**
```
Backend Service (2 vCPU, 4GB RAM): ~$20
Frontend Service (1 vCPU, 2GB RAM): ~$10
PostgreSQL (1 vCPU, 2GB RAM, 10GB): ~$15
Redis (1GB Memory): ~$8
Bandwidth (100GB): ~$2

Total Estimado: ~$55/mês
```

### **Otimizações de Custo**
- Auto-scaling para reduzir custos em baixa demanda
- Compressão de assets para reduzir bandwidth
- Cache agressivo para reduzir compute
- Cleanup automático de arquivos temporários

---

**🚀 O deploy no Railway fornece uma infraestrutura robusta, escalável e de fácil manutenção para o Agente de Análise de Engenharia, com monitoramento integrado e deploy contínuo.**