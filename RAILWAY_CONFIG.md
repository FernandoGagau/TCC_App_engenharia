# Configuração Railway - URLs Atualizadas

## URLs do Sistema

- **Frontend**: https://agente-engenheiro.up.railway.app
- **Backend**: https://backend-production-630c.up.railway.app
- **API**: https://backend-production-630c.up.railway.app/api

## Variáveis de Ambiente Necessárias

### 🎨 Frontend (agente-engenheiro)

```bash
REACT_APP_BACKEND_URL=https://backend-production-630c.up.railway.app
```

### 🔧 Backend (backend-production-630c)

```bash
# CORS - Permite frontend acessar backend
CORS_ORIGINS=["https://agente-engenheiro.up.railway.app","http://localhost:3000","http://localhost:3001"]

# MongoDB
MONGODB_URL=mongodb+srv://usuario:senha@cluster.mongodb.net/construction_agent?retryWrites=true&w=majority
MONGODB_DATABASE=construction_agent

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-seu-key-aqui

# Modelos
CHAT_MODEL=x-ai/grok-4-fast
VISION_MODEL=google/gemini-2.5-flash-image-preview

# MinIO/S3 (se usar)
AWS_ACCESS_KEY_ID=seu-access-key
AWS_SECRET_ACCESS_KEY=seu-secret-key
AWS_ENDPOINT_URL=https://seu-minio-url.com
AWS_REGION=us-east-1
STORAGE_BUCKET=construction-images

# Segurança
SECRET_KEY=seu-secret-key-production-aqui
```

## ⚠️ IMPORTANTE: Quando mudar URL do frontend

Sempre que mudar o domínio customizado do frontend no Railway:

1. ✅ **Atualize `CORS_ORIGINS` no backend** para incluir novo domínio
2. ✅ **Redeploy o backend** após atualizar variável
3. ✅ **Teste** acessando o novo domínio

### Erro Comum: CORS

Se aparecer erro no console do tipo:
```
Access to XMLHttpRequest blocked by CORS policy
```

É porque o backend não está permitindo o domínio do frontend. Confira `CORS_ORIGINS`.

## 🧪 Testes

### 1. Teste CORS (Console do Browser)

```javascript
fetch('https://backend-production-630c.up.railway.app/api/health')
  .then(r => r.json())
  .then(d => console.log('✅ Backend OK:', d))
  .catch(e => console.error('❌ Backend erro:', e))
```

### 2. Teste Projetos

Acesse: https://agente-engenheiro.up.railway.app/projects

Deve carregar sem erros.

### 3. Página de Diagnóstico

Acesse: https://agente-engenheiro.up.railway.app/config-check.html

Deve mostrar todas as configurações corretas.

## 📝 Checklist de Deploy

- [ ] CORS_ORIGINS atualizado no backend
- [ ] Backend redeployado
- [ ] REACT_APP_BACKEND_URL configurado no frontend
- [ ] Frontend buildado com URL correta
- [ ] Sem erros de Mixed Content no console
- [ ] Requisições de API funcionando
- [ ] Dashboard carregando dados

## 🔄 Mudanças de Domínio

Sempre que mudar domínio:

**Frontend**: Não precisa fazer nada (continua acessando mesma URL de backend)

**Backend**:
```bash
# Adicione novo domínio ao CORS_ORIGINS
CORS_ORIGINS=["https://novo-dominio.com","https://dominio-antigo.com","http://localhost:3000"]
```

Mantenha o antigo temporariamente durante a transição.
