# Railway Architecture Options

## Opção 1: Serviços Separados (Atual - Recomendado) ✅

### Estrutura
```
Railway Project
├── MongoDB (Database)
├── Backend (FastAPI Container)
└── Frontend (React + Nginx Container)
```

### Como funciona
- Frontend serve apenas arquivos estáticos (HTML, JS, CSS)
- React faz chamadas diretas para `https://backend.railway.app/api/...`
- Backend responde com JSON
- CORS configurado no backend

### Variáveis
```env
# Frontend
REACT_APP_BACKEND_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}

# Backend
MONGODB_URL=${{MongoDB.MONGO_URL}}
```

### Vantagens
- ✅ Escalabilidade independente
- ✅ Deploy independente
- ✅ Monitoramento separado
- ✅ Custo otimizado
- ✅ Simples de configurar
- ✅ Padrão moderno (JAMstack)

### Desvantagens
- ❌ Duas URLs diferentes (pode resolver com domínio customizado)
- ❌ CORS precisa estar configurado

---

## Opção 2: Nginx como Proxy (Alternativa)

### Estrutura
```
Railway Project
├── MongoDB (Database)
├── Backend (FastAPI Container)
└── Frontend (React + Nginx com Proxy)
```

### Como funciona
- Frontend Nginx faz proxy das chamadas `/api/*` para o backend
- `https://frontend.railway.app/api/users` → `https://backend.railway.app/api/users`
- React chama apenas `/api/...` (mesma origem)

### nginx.conf
```nginx
location /api/ {
    # Usar variável de ambiente injetada no build
    set $backend_url "BACKEND_URL_PLACEHOLDER";
    proxy_pass $backend_url;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Dockerfile
```dockerfile
# Build stage
FROM node:18-alpine AS builder
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
COPY . .
RUN npm ci && npm run build

# Runtime stage
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/nginx.conf.template

# Entrypoint que substitui variável de ambiente
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
```

### docker-entrypoint.sh
```bash
#!/bin/sh
set -e

# Substituir BACKEND_URL no nginx.conf
envsubst '$BACKEND_URL' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Iniciar nginx
exec "$@"
```

### Vantagens
- ✅ Uma única URL pública (frontend)
- ✅ Sem problemas de CORS
- ✅ Backend pode ser privado

### Desvantagens
- ❌ Mais complexo de configurar
- ❌ Frontend precisa reiniciar se backend mudar
- ❌ Latência extra (proxy)
- ❌ Nginx precisa resolver DNS do backend

---

## Opção 3: Monolito (Não Recomendado) ❌

### Estrutura
```
Railway Project
├── MongoDB (Database)
└── App (Backend + Frontend no mesmo container)
```

### Como funciona
- FastAPI serve a API em `/api/*`
- FastAPI serve arquivos estáticos do React em `/*`
- Tudo em um único processo

### main.py
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# API routes
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# Serve React build
app.mount("/", StaticFiles(directory="frontend/build", html=True), name="static")
```

### Vantagens
- ✅ Deploy simples (um único serviço)
- ✅ Uma única URL

### Desvantagens
- ❌ Escalabilidade ruim (frontend + backend juntos)
- ❌ Build lento (sempre rebuild tudo)
- ❌ Desperdício de recursos
- ❌ Não é padrão moderno

---

## 🎯 Recomendação

**Use Opção 1: Serviços Separados**

É a arquitetura moderna, padrão da indústria:
- Netflix, Airbnb, Uber usam microserviços
- Frontend CDN (Vercel, Netlify) + Backend API
- JAMstack architecture

### Como está atualmente

✅ **Correto:**
```javascript
// frontend/src/services/api.js
const API_URL = process.env.REACT_APP_BACKEND_URL;

fetch(`${API_URL}/api/users`)
  .then(res => res.json())
```

✅ **CORS no backend:**
```python
# backend/src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontend.railway.app",
        "http://localhost:3000"
    ]
)
```

---

## 🚀 Se Você Quiser Migrar para Proxy

Se ainda assim preferir usar Nginx proxy (Opção 2):

1. Adicionar `docker-entrypoint.sh`
2. Modificar `nginx.conf` para usar variável
3. Modificar `Dockerfile` para copiar entrypoint
4. Adicionar `BACKEND_URL` nas variáveis Railway

**Mas isso é mais trabalho e não traz vantagens reais.**

---

## 💡 Dica: Domínio Customizado

Se o problema é ter URLs diferentes, use domínio customizado:

```
https://app.seudominio.com     → Frontend
https://api.seudominio.com     → Backend
```

Railway permite configurar isso gratuitamente.