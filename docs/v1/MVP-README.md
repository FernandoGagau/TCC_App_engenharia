# 🤖 MVP - Agente Conversacional de Obras

## 📋 Visão Geral

**MVP funcional** do Agente Conversacional para documentação inteligente de obras, focado em:

✅ **Chat estruturado** com perguntas sobre a obra
✅ **Configuração centralizada** em arquivo JSON
✅ **Documentação automática** da obra em JSON
✅ **3 locais específicos** para monitoramento
✅ **Upload de imagens** com análise simulada
✅ **API REST** pronta para frontend React

---

## 🚀 Como Executar

### **1. Backend (Python/FastAPI)**

```bash
# Navegar para o backend
cd backend

# Instalar dependências
pip install -r requirements.txt

# Executar servidor
python main.py
```

**Servidor rodará em**: `http://localhost:8000`

### **2. Testar a API**

#### **Iniciar Conversa**
```bash
curl -X POST "http://localhost:8000/chat/start" \
  -H "Content-Type: application/json"
```

#### **Enviar Mensagem**
```bash
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Casa da Maria Silva - Ampliação Cozinha",
    "project_id": "session-123"
  }'
```

#### **Upload de Imagem**
```bash
curl -X POST "http://localhost:8000/chat/image" \
  -F "file=@foto_obra.jpg" \
  -F "location=location_1" \
  -F "session_id=session-123"
```

---

## 🗂️ Estrutura do MVP

### **Arquivos Criados**

```
✅ backend/
   ├── main.py                    # API FastAPI principal
   ├── requirements.txt           # Dependências Python
   └── config/
       └── agent_config.json      # Configuração completa do agente

✅ docs/
   ├── PRD/
   │   ├── product-requirements.md      # PRD original
   │   └── mvp-conversational-agent.md  # PRD focado no MVP
   ├── examples/
   │   └── exemplo-obra-json.md    # Exemplo de JSON gerado
   └── architecture/
       └── system-architecture.md # Arquitetura completa

✅ README.md                      # Documentação geral
✅ MVP-README.md                  # Este arquivo
```

---

## 🎯 Funcionamento do MVP

### **1. Conversa Estruturada**

O agente segue uma **sequência de perguntas** definida no `agent_config.json`:

```json
"questions_sequence": [
  {
    "id": "project_name",
    "question": "📋 Qual é o nome desta obra?",
    "type": "text",
    "required": true
  },
  {
    "id": "project_type",
    "question": "🏗️ Que tipo de construção?",
    "type": "select",
    "options": ["construção_nova", "reforma", "ampliação"]
  }
  // ... mais perguntas
]
```

### **2. Análise de 3 Locais**

Configuração dos locais no JSON:

```json
"locations": {
  "location_1": {
    "name": "Área Externa - Fachada",
    "key_elements": ["estrutura", "fundação", "revestimento"],
    "tracking_phases": ["fundacao", "estrutura", "alvenaria"]
  },
  "location_2": {
    "name": "Área Interna - Ambiente Principal",
    "key_elements": ["piso", "paredes", "teto"],
    "tracking_phases": ["estrutura", "alvenaria", "acabamento"]
  },
  "location_3": {
    "name": "Área Técnica - Cozinha/Banheiro",
    "key_elements": ["hidraulica", "eletrica", "revestimentos"],
    "tracking_phases": ["instalacoes", "revestimento", "louças"]
  }
}
```

### **3. JSON Automático Gerado**

Após a conversa, o agente gera automaticamente:

```json
{
  "project_info": {
    "project_name": "Casa da Maria Silva",
    "project_type": "reforma",
    "start_date": "10/01/2025",
    "project_id": "uuid-gerado"
  },
  "locations_status": {
    "location_1": {
      "current_phase": "fundacao",
      "progress_percentage": 30,
      "observations": "Estrutura bem executada"
    }
    // ... outros locais
  },
  "timeline": [
    {
      "timestamp": "2025-01-15T14:30:00Z",
      "event": "Documentação inicial criada",
      "progress_before": 0,
      "progress_after": 15
    }
  ]
}
```

---

## 🔧 Configuração Personalizada

### **Modificar Perguntas**

Edite `backend/config/agent_config.json`:

```json
"questions_sequence": [
  {
    "id": "nova_pergunta",
    "question": "❓ Sua pergunta customizada aqui?",
    "type": "text",
    "required": true
  }
]
```

### **Personalizar Locais**

```json
"locations": {
  "location_1": {
    "name": "Seu Local Personalizado",
    "description": "Descrição do que será monitorado",
    "key_elements": ["elemento1", "elemento2"],
    "tracking_phases": ["fase1", "fase2"]
  }
}
```

### **Ajustar Prompts**

```json
"prompts": {
  "system_prompt": "Seu prompt personalizado aqui...",
  "initial_interview": {
    "intro_message": "Sua mensagem de boas-vindas..."
  }
}
```

---

## 🌐 Endpoints da API

### **📋 Informações Gerais**
- `GET /` - Informações da API
- `GET /health` - Health check
- `GET /config` - Configuração pública

### **💬 Chat**
- `POST /chat/start` - Iniciar conversa
- `POST /chat/message` - Enviar mensagem
- `POST /chat/image` - Upload de imagem

### **📊 Projetos**
- `GET /projects` - Listar projetos
- `GET /projects/{id}` - Dados de projeto específico

---

## 🧪 Testando o MVP

### **Cenário Completo de Teste**

1. **Iniciar conversa**
2. **Responder perguntas sequenciais**:
   - Nome da obra
   - Tipo de construção
   - Endereço
   - Responsável técnico
   - Datas de início/fim
3. **Enviar 3 fotos** (uma para cada local)
4. **Verificar JSON gerado** em `/storage/projects/`

### **Fluxo Esperado**

```
🤖 Agente: Olá! Qual o nome da obra?
👤 Usuário: Casa da Maria Silva

🤖 Agente: Que tipo de construção?
👤 Usuário: reforma

🤖 Agente: Endereço da obra?
👤 Usuário: Rua das Flores, 123

// ... continua até as 3 fotos

🤖 Agente: ✅ Documentação criada!
           📊 Progresso: 25% | Status: No prazo
           💾 Salvo em: obra_12345.json
```

---

## 🔮 Próximas Evoluções

### **Sprint 2 - Integração IA Real**
- [ ] **LangChain + OpenRouter (Grok-4 Fast)** para conversas inteligentes
- [ ] **OpenRouter (Gemini 2.5 Flash Image Preview)** para análise real de imagens
- [ ] **LangSmith** para observabilidade

### **Sprint 3 - Frontend React**
- [ ] **Interface de chat** responsiva
- [ ] **Upload drag-and-drop** de imagens
- [ ] **Visualização do JSON** em tempo real
- [ ] **Dashboard** de progresso

### **Sprint 4 - Deploy Produção**
- [ ] **Railway deployment** automatizado
- [ ] **Banco PostgreSQL** para persistência
- [ ] **Redis** para cache
- [ ] **CI/CD** com GitHub Actions

---

## 💡 Como Usar na Prática

### **Para Engenheiros**
1. Acesse a API via Postman/Insomnia
2. Inicie conversa para cada nova obra
3. Documente com fotos regulares
4. Acompanhe progresso via JSON

### **Para Desenvolvedores**
1. Estude `agent_config.json` para entender estrutura
2. Modifique prompts conforme necessário
3. Integre frontend consumindo a API
4. Customize locais e fases por tipo de obra

### **Para Gestores**
1. Use JSON gerado para relatórios
2. Monitore progresso via API `/projects`
3. Exporte dados para sistemas existentes
4. Analise qualidade e cronograma

---

**🎯 Este MVP demonstra a viabilidade do conceito e está pronto para evolução com IA completa e interface web!**