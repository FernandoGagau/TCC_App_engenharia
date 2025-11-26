# 🏗️ Construction Analysis Agent System v2.0

Este repositório faz parte de um **Trabalho de Conclusão de Curso (TCC)** em Engenharia Civil e reúne um sistema completo de **IA conversacional** para documentação e monitoramento de obras, combinando:

- Chat inteligente com múltiplos agentes
- Análise de imagens com **GPT-4 Vision**
- Orquestração multi-agente com **LangChain** e **LangGraph**
- Geração automática de documentação estruturada em **JSON**

---

## 📋 Visão Geral

O sistema foi desenvolvido para apoiar engenheiros e gestores na **análise, documentação e acompanhamento de projetos de construção civil**, integrando:

- Conversas em linguagem natural
- Processamento de imagens e documentos técnicos
- Monitoramento de progresso físico
- Geração de relatórios inteligentes

A plataforma utiliza:

- **LangChain 0.3.x** e **LangGraph 0.6.x** para orquestração de agentes
- **GPT-4 / GPT-4 Vision** como modelos principais de linguagem e visão
- Backend em **FastAPI (Python 3.12+)**
- Frontend em **React 18 + TypeScript**

---

## 🎯 Funcionalidades Principais

### 🤖 Agentes Inteligentes

- **Agente de Análise Visual**  
  Responsável por processar **imagens e vídeos de obras**, identificando elementos relevantes para o acompanhamento do canteiro.

- **Agente de Documentação**  
  Faz a **análise e extração de informações** de documentos técnicos (plantas, memoriais, especificações etc.) e gera estruturas consolidadas.

- **Agente de Progresso**  
  Monitora o **progresso da obra** e realiza comparação com o **cronograma executivo**, identificando atrasos, adiantamentos e desvios.

- **Agente de Relatórios**  
  Gera **relatórios automáticos** estruturados (JSON) com insights, alertas e recomendações para a gestão da obra.

---

### 💬 Interface de Chat Interativa

- Chat em tempo real com os agentes de IA  
- **Upload de imagens e documentos técnicos**  
- **Captura de fotos via câmera** (quando disponível)  
- **Gravação e envio de áudio**  
- Mapeamento de **locais/áreas do projeto** para contextualização das análises

---

## 🔧 Tecnologias Utilizadas

### Backend (Python 3.12+)

- **Runtime:**  
  - Python 3.12+ com `async/await` nativo

- **Framework Web:**  
  - **FastAPI 0.115+** (alta performance, OpenAPI/Swagger embutido)

- **IA / Agentes:**
  - **LangChain 0.3.27+** (orquestração de LLMs e ferramentas)
  - **LangGraph 0.6.7+** (fluxos de agentes e state machines)
  - **LangSmith** (observabilidade, tracing e monitoramento)
  - **Modelos:** OpenAI GPT-4, GPT-4 Vision, OpenRouter

- **Banco de Dados e Cache:**
  - **MongoDB 7.0+** com **Motor** (driver assíncrono)
  - **Redis 7.0+** (cache e filas de processamento)

- **Storage:**
  - **MinIO / S3 / GCS** para armazenamento de objetos (imagens, documentos, modelos etc.)

- **Deploy:**
  - **Railway** com **Nixpacks**

---

### Frontend

- **Framework:** React 18 com TypeScript  
- **Build:** Vite 5.0+  
- **Estilos:** Tailwind CSS  
- **Gerenciamento de Estado / Dados:**  
  - Zustand  
  - TanStack Query  

---

## 📁 Estrutura do Projeto

```bash
/projeto-agente-engenharia/
├── backend/              # API Python com agentes e lógica de negócio
│   ├── agents/           # Definição e orquestração dos agentes de IA
│   ├── models/           # Modelos de dados (Pydantic / ORM / schemas)
│   ├── services/         # Serviços de processamento e integrações
│   └── api/              # Endpoints REST/WebSocket (FastAPI)
├── frontend/             # Aplicação React (interface do usuário)
│   ├── components/       # Componentes reutilizáveis de UI
│   ├── pages/            # Páginas principais da aplicação
│   └── hooks/            # Hooks customizados (estado, API, etc.)
├── docs/                 # Documentação completa do TCC e do sistema
│   ├── architecture/     # Documentos de arquitetura de software
│   ├── OCR/              # Guias de processamento de documentos/imagens
│   ├── PRD/              # Product Requirements Document
│   ├── agents/           # Detalhamento de cada agente de IA
│   └── infrastructure/   # Configuração de deploy e infraestrutura
└── assets/
    ├── images/           # Imagens do projeto e da obra
    └── models/           # Modelos treinados e artefatos de IA
🚀 Início Rápido
✅ Pré-requisitos
Backend

Python 3.12+

MongoDB 7.0+ ou PostgreSQL 15+ (conforme configuração)

Redis 7.0+ (cache e filas)

Tesseract OCR 5.0+ (processamento de imagens/documentos)

Chaves de API (OpenAI, OpenRouter etc.)

Frontend

Node.js 18+

npm ou pnpm/yarn

🐍 Backend (Python 3.12+)
bash
Copiar código
# Clone o repositório
git clone <repository-url>
cd agente-engenharia/backend

# Criar ambiente virtual com Python 3.12+
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou, no Windows:
.venv\Scripts\activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# OU, usando pyproject.toml (recomendado)
pip install -e .

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações (Mongo/Redis, chaves de API, etc.)

# Executar o servidor
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
💻 Frontend
bash
Copiar código
cd ../frontend

# Instalar dependências
npm install

# Rodar ambiente de desenvolvimento
npm run dev
🐳 Docker (Produção)
bash
Copiar código
# Build da imagem do backend (Python 3.12)
docker build -t construction-agent:latest ./backend

# Ou usar docker-compose para subir todos os serviços
docker-compose up --build
🚂 Deploy no Railway
O deploy em produção é feito via Railway.

Guia completo: veja docs/infrastructure/RAILWAY_SETUP.md (ou arquivo equivalente).

Resumo rápido:

Criar um projeto no Railway vinculado ao repositório GitHub

Adicionar 4 serviços:

Backend

Frontend

MongoDB

MinIO (ou outro storage compatível)

Configurar as variáveis de ambiente de cada serviço

Habilitar deploy automático a cada push na branch configurada (ex: main)

🔐 GitHub Secrets Necessários
Para que os workflows de CI/CD funcionem corretamente, configure os seguintes secrets em:

Settings → Secrets and variables → Actions → New repository secret

Secret Name	Descrição	Usado em
OPENROUTER_API_KEY	Chave de API do OpenRouter (provedor de LLMs)	Testes Backend / IA
SONAR_TOKEN	Token do SonarCloud para análise de qualidade	Code Quality

Como obter:

OPENROUTER_API_KEY: acessar OpenRouter → criar API Key

SONAR_TOKEN: acessar SonarCloud → My Account → Security → Generate Token

📖 Documentação
A documentação detalhada está na pasta /docs:

Architecture
Desenho da arquitetura, fluxos principais e decisões de design.

PRD (Product Requirements Document)
Requisitos funcionais e não funcionais do produto.

Agents
Descrição do comportamento, entradas, saídas e fluxos de cada agente.

OCR
Processo de extração de dados de documentos e imagens (Tesseract, pipelines etc.).

Infrastructure
Configurações de deploy (Railway, Docker, variáveis de ambiente, storage).

Essa documentação complementa o TCC, detalhando como a solução foi implementada em nível de sistema.

🎯 Principais Casos de Uso
Monitoramento de Progresso de Obra
Análise automática de fotos do canteiro, vinculando o conteúdo visual ao cronograma e ao modelo de referência.

Análise de Documentos Técnicos
Extração de informações de plantas, memoriais descritivos e especificações para apoiar a documentação e o planejamento.

Relatórios Inteligentes
Geração de relatórios com estrutura JSON e possibilidade de exportação para outros formatos (PDF, dashboards etc.).

Assistente Virtual para Engenheiros
Interface conversacional que ajuda na consulta de informações, entendimento de documentos e tomada de decisão.

📋 Status do Projeto
✅ Análise de requisitos e definição de MCPs

✅ Estrutura base do projeto (backend + frontend)

✅ Desenvolvimento dos agentes principais

✅ Interface em React integrada ao backend

✅ Integração entre serviços e testes iniciais

✅ Deploy funcional no Railway



