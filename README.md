# 🏗️ Construction Analysis Agent System v2.0

## 📋 Visão Geral

Sistema inteligente de análise e documentação de obras usando **LangChain 0.3.12**, **LangGraph 0.2.63** e **GPT-4 Vision**.

Sistema completo de IA conversacional para documentação e monitoramento de projetos de construção civil, implementando chat inteligente, análise de imagens com GPT-4 Vision, multi-agent system com orquestração via LangGraph e geração automática de documentação JSON estruturada.

## 🎯 Funcionalidades Principais

### 🤖 Agentes Inteligentes
- **Agente de Análise Visual**: Processamento de imagens e vídeos de obras
- **Agente de Documentação**: Análise e extração de informações de documentos técnicos
- **Agente de Progresso**: Monitoramento e comparação com cronogramas
- **Agente de Relatórios**: Geração automática de relatórios e insights

### 📱 Interface de Chat Interativa
- Chat em tempo real com os agentes
- Captura de fotos via câmera
- Upload de imagens e documentos
- Gravação e envio de áudio
- Mapeamento de locais/áreas do projeto

### 🔧 Tecnologias Utilizadas

#### Backend (Python 3.12+)
- **Runtime**: Python 3.12+ com async/await nativo
- **Framework**: FastAPI 0.115+ (alta performance)
- **AI/Agents**:
  - LangChain 0.3.27+ (orquestração)
  - LangGraph 0.6.7+ (fluxos de agentes)
  - LangSmith (observabilidade)
- **Models**: OpenAI GPT-4, GPT-4 Vision, OpenRouter
- **Database**:
  - MongoDB 7.0+ com Motor (async driver)
  - Redis 7.0+ (cache e filas)
- **Storage**: MinIO/S3/GCS para objetos
- **Deploy**: Railway com Nixpacks

#### Frontend
- **Framework**: React 18 com TypeScript
- **Build**: Vite 5.0+
- **Styling**: Tailwind CSS
- **State**: Zustand/TanStack Query

## 📁 Estrutura do Projeto

```
/projeto-agente-engenharia/
├── backend/              # API Python com agentes
│   ├── agents/          # Agentes especializados
│   ├── models/          # Modelos de dados
│   ├── services/        # Serviços de processamento
│   └── api/             # Endpoints REST/WebSocket
├── frontend/            # React App
│   ├── components/      # Componentes reutilizáveis
│   ├── pages/          # Páginas da aplicação
│   └── hooks/          # Hooks customizados
├── docs/               # Documentação completa
│   ├── architecture/   # Documentos de arquitetura
│   ├── OCR/           # Guias de processamento
│   ├── PRD/           # Product Requirements
│   ├── agents/        # Documentação dos agentes
│   └── infrastructure/ # Configuração de deploy
└── assets/
    ├── images/        # Imagens do projeto
    └── models/        # Modelos treinados
```

## 🚀 Início Rápido

### Pré-requisitos
- **Python 3.12+** (obrigatório para o backend)
- Node.js 18+ (frontend)
- PostgreSQL 15+ ou MongoDB 7.0+
- Redis 7.0+ (cache e filas)
- Tesseract OCR 5.0+ (processamento de imagens)
- Chaves API (OpenAI, OpenRouter, etc.)

### Instalação

#### Backend (Python 3.12+)
```bash
# Clone o repositório
git clone <repository-url>
cd agente-engenharia/backend

# Criar ambiente virtual com Python 3.12+
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# Ou usar pyproject.toml (recomendado)
pip install -e .

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações

# Executar o servidor
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd ../frontend
npm install
npm run dev
```

#### Docker (Produção)
```bash
# Build com Python 3.12
docker build -t construction-agent:latest ./backend

# Ou usar docker-compose
docker-compose up --build
```

### 🚂 Deploy no Railway

Para fazer deploy no Railway, siga o guia completo: **[RAILWAY_SETUP.md](./RAILWAY_SETUP.md)**

**Resumo rápido:**
1. Crie projeto no Railway vinculando o GitHub
2. Adicione 4 serviços: Backend, Frontend, MongoDB, MinIO
3. Configure variáveis de ambiente em cada serviço
4. Deploy automático via GitHub push

### 🔐 GitHub Secrets Necessários

Para os workflows de CI/CD funcionarem corretamente, configure os seguintes secrets no GitHub:

**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | Required For |
|------------|-------------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key (provedor único de LLMs) | Testes Backend |
| `SONAR_TOKEN` | SonarCloud token para análise de qualidade | Code Quality |

**Como obter os tokens:**
- **OPENROUTER_API_KEY**: Acesse [OpenRouter](https://openrouter.ai/keys) → Create API Key
- **SONAR_TOKEN**: Acesse [SonarCloud](https://sonarcloud.io/) → My Account → Security → Generate Token

## 📖 Documentação

A documentação completa está disponível na pasta `/docs`:

- **[Arquitetura](./docs/architecture/)** - Design e estrutura do sistema
- **[PRD](./docs/PRD/)** - Requisitos do produto
- **[Agentes](./docs/agents/)** - Comportamento e fluxos dos agentes
- **[OCR](./docs/OCR/)** - Processamento de documentos
- **[Infraestrutura](./docs/infrastructure/)** - Configuração e deploy

## 🎯 Casos de Uso

1. **Monitoramento de Progresso**: Análise automática de fotos da obra
2. **Análise de Documentos**: Extração de informações de plantas e especificações
3. **Relatórios Inteligentes**: Geração de relatórios com insights visuais
4. **Assistente Virtual**: Suporte inteligente para engenheiros e gestores

## 📋 Status do Projeto

- ✅ Análise de requisitos e MCPs
- ✅ Estrutura base do projeto
- ✅ Desenvolvimento dos agentes 
- ✅ Interface React
- ✅ Integração e testes
- ✅ Deploy Railway



