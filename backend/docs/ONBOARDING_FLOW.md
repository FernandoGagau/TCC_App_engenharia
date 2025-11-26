# Fluxo de Onboarding - Sistema de Monitoramento de Obras

## Visão Geral

O sistema agora possui um **fluxo inteligente de onboarding** que detecta quando um usuário não possui projetos cadastrados e guia-o através do processo de configuração inicial.

## 🎯 Objetivo

Garantir que novos usuários tenham uma experiência fluida ao começar a usar o sistema, coletando todas as informações necessárias de forma conversacional e não intimidadora.

---

## 📋 Fluxo Completo

### 1. **Verificação Inicial**

Quando o usuário envia a primeira mensagem, o supervisor:

```python
# Verifica no banco de dados
has_projects = await project_repository.count_projects(user_id) > 0

if not has_projects:
    # Inicia fluxo de onboarding
    return onboarding_flow()
else:
    # Prossegue com análise normal
    return normal_analysis_flow()
```

**Prompt usado**: `check_project_exists_prompt`

**Variáveis**:
- `has_projects`: True/False
- `project_count`: número de projetos
- `project_list`: lista de projetos (se houver)
- `user_input`: entrada do usuário
- `context_history`: histórico da conversa

---

### 2. **Boas-vindas e Primeira Coleta**

Se não houver projetos, o sistema dá as boas-vindas e faz as primeiras perguntas:

**Exemplo de resposta**:
```
Olá! Bem-vindo ao Sistema de Monitoramento de Obras com IA! 👋

Vejo que você ainda não possui nenhum projeto cadastrado. Vou te ajudar a configurar
seu primeiro projeto para que você possa começar a monitorar sua obra.

Para começar, me conte sobre o seu projeto:

1. **Qual o nome da obra?** (Ex: "Edifício Residencial Solar", "Reforma Escritório Centro")

2. **Que tipo de obra é?**
   - Residencial (casa, apartamento, condomínio)
   - Comercial (loja, escritório, shopping)
   - Industrial (fábrica, galpão)
   - Reforma

3. **Onde fica localizada?** (endereço ou localização aproximada)

Não se preocupe se não tiver todas as informações agora - podemos complementar depois! 😊
```

**Prompt usado**: `onboarding_welcome_prompt`

**Variáveis**:
- `user_input`: entrada inicial do usuário

---

### 3. **Coleta Progressiva de Informações**

O sistema coleta informações gradualmente, fazendo 2-3 perguntas por vez:

**Informações Essenciais**:

#### 1. Identificação do Projeto
- ✅ Nome do projeto
- ✅ Tipo de obra (residencial, comercial, industrial, reforma)
- ✅ Endereço/localização

#### 2. Informações Técnicas (opcionais)
- Engenheiro responsável
- Número CREA
- Data de início
- Data de conclusão prevista
- Orçamento estimado

#### 3. Escopo do Monitoramento
- ✅ O que deseja monitorar? (progresso, segurança, qualidade, cronograma)
- ✅ Áreas a acompanhar (externa, interna, técnicas)
- Possui documentos? (plantas, cronograma, especificações)
- Possui fotos atuais?

#### 4. Objetivos e Necessidades
- Principal objetivo (controle de prazo, qualidade, custos)
- Frequência de relatórios (diário, semanal, mensal)

**Prompt usado**: `onboarding_collect_info_prompt`

**Variáveis**:
- `collected_info`: informações já coletadas
- `user_input`: última resposta do usuário
- `context_history`: histórico
- `missing_info`: lista do que ainda falta

**Resposta JSON do LLM**:
```json
{
  "extracted_info": {
    "project_name": "Edifício Residencial Solar",
    "project_type": "residential",
    "address": "Rua das Flores, 123 - São Paulo",
    "responsible_engineer": "João Silva",
    "responsible_crea": "SP-123456",
    "start_date": "2025-01-15",
    "expected_completion": "2025-12-31",
    "monitoring_goals": ["progress", "quality", "schedule"],
    "locations_to_monitor": ["external", "internal"],
    "has_documents": true,
    "has_images": false
  },
  "is_complete": false,
  "next_question": "Você possui alguma foto atual da obra para começarmos a análise?",
  "response_to_user": "Ótimo! Já tenho as informações principais... [continua]"
}
```

---

### 4. **Confirmação dos Dados**

Quando todas as informações essenciais forem coletadas:

**Exemplo de confirmação**:
```
Perfeito! Aqui está o resumo do seu projeto:

📋 **Informações do Projeto:**

**Identificação:**
• Nome: Edifício Residencial Solar
• Tipo: Obra Residencial
• Localização: Rua das Flores, 123 - São Paulo

**Responsável Técnico:**
• Engenheiro: João Silva
• CREA: SP-123456

**Cronograma:**
• Início: 15/01/2025
• Conclusão prevista: 31/12/2025
• Duração: 12 meses

**Monitoramento:**
• Foco: Progresso, Qualidade e Cronograma
• Áreas: Externa e Interna
• Documentos: Sim
• Fotos iniciais: Não (pode adicionar depois)

---

Está tudo correto? Digite:
• **"Sim"** ou **"Confirmar"** para cadastrar o projeto
• **"Editar [campo]"** para alterar alguma informação
• **"Cancelar"** para recomeçar
```

**Prompt usado**: `project_confirmation_prompt`

**Variáveis**:
- `project_info`: todas as informações coletadas

---

### 5. **Próximos Passos Após Cadastro**

Após confirmação, o sistema:

1. **Cria o projeto no banco de dados**
2. **Cria localizações padrão** (externa, interna, técnica)
3. **Inicia timeline do projeto**
4. **Orienta próximos passos**:

**Exemplo**:
```
✅ Projeto "Edifício Residencial Solar" cadastrado com sucesso!

**Próximos passos para começar o monitoramento:**

1. 📸 **Adicionar fotos da obra**
   Envie fotos atuais da obra para que eu possa analisar o progresso inicial.
   Você pode enviar quantas fotos quiser!

2. 📄 **Fazer upload de documentos** (opcional)
   - Plantas do projeto
   - Cronograma de execução
   - Especificações técnicas
   - Orçamento

3. 🎯 **Começar o monitoramento**
   Posso começar a analisar as imagens assim que você enviá-las!

**O que você gostaria de fazer agora?**
• Enviar fotos
• Fazer upload de documentos
• Apenas explorar o sistema
```

---

## 🔄 Fluxo com Múltiplos Projetos

### Seleção de Projeto

Quando o usuário já possui projetos e faz uma solicitação:

```python
# Verifica se há projeto selecionado no contexto da sessão
if not current_project and project_count > 1:
    # Precisa selecionar um projeto
    return project_selection_flow()
```

**Exemplo de seleção**:
```
Você possui 3 projetos cadastrados:

1. 🏗️ **Edifício Residencial Solar**
   Tipo: Residencial | Local: São Paulo - SP
   Progresso: 45% | Status: Em andamento

2. 🏢 **Reforma Escritório Centro**
   Tipo: Comercial | Local: Rio de Janeiro - RJ
   Progresso: 78% | Status: Em andamento

3. 🏭 **Galpão Industrial Norte**
   Tipo: Industrial | Local: Curitiba - PR
   Progresso: 100% | Status: Concluído

Qual projeto você gostaria de analisar?
Digite o número ou o nome do projeto.
```

**Prompt usado**: `project_selection_prompt`

**Variáveis**:
- `project_list`: lista formatada de projetos
- `user_input`: solicitação do usuário
- `current_project`: projeto atualmente selecionado
- `context_history`: histórico

---

## 🚨 Tratamento de Erros

### Erro: Ação sem Projeto Selecionado

```
Para realizar essa análise, preciso saber qual projeto você deseja analisar.

**Você possui os seguintes projetos:**

1. Edifício Residencial Solar
2. Reforma Escritório Centro
3. Galpão Industrial Norte

**Por favor, selecione um projeto:**
• Digite o número (1, 2 ou 3)
• Ou digite o nome do projeto
• Ou diga "criar novo projeto" para cadastrar uma nova obra
```

**Prompt usado**: `missing_project_error_prompt`

**Variáveis**:
- `requested_action`: ação que o usuário tentou fazer
- `available_projects`: lista de projetos disponíveis

---

## 💡 Exemplos de Uso

### Exemplo 1: Novo Usuário

```
Usuário: "Olá, quero monitorar minha obra"

Sistema: Bem-vindo! Vejo que você ainda não possui nenhum projeto cadastrado...
         [inicia onboarding]

Usuário: "É um prédio residencial em São Paulo"

Sistema: Ótimo! Me conta mais:
         - Qual o nome do projeto?
         - Qual o endereço completo?
         ...
```

### Exemplo 2: Usuário com Projetos

```
Usuário: "Analise essas fotos da obra" [anexa 3 fotos]

Sistema: [verifica que há 2 projetos]
         Você possui 2 projetos. Qual deseja analisar?
         1. Edifício Solar
         2. Reforma Centro

Usuário: "Edifício Solar"

Sistema: [seleciona projeto e prossegue com análise das fotos]
```

### Exemplo 3: Onboarding Parcial

```
Usuário: "Preciso monitorar minha reforma mas não tenho todas as informações agora"

Sistema: Sem problemas! Vamos começar com o básico e você complementa depois.
         Qual o nome da obra e onde fica?

Usuário: "Reforma do Escritório, Av. Paulista"

Sistema: Perfeito! Vou criar o projeto com essas informações.
         Você pode adicionar mais detalhes depois no perfil do projeto.
         [cria projeto com dados mínimos]
```

---

## 🔧 Implementação no Supervisor

### Métodos Necessários

```python
class SupervisorAgent:

    async def check_user_has_projects(self, user_id: str) -> dict:
        """Verifica se usuário tem projetos"""
        projects = await self.project_repository.get_user_projects(user_id)
        return {
            'has_projects': len(projects) > 0,
            'project_count': len(projects),
            'project_list': [self._format_project(p) for p in projects]
        }

    async def start_onboarding(self, user_input: str, context: AgentContext) -> str:
        """Inicia fluxo de onboarding"""
        prompt = self.prompt_manager.get_prompt(
            'supervisor',
            'onboarding_welcome_prompt',
            user_input=user_input
        )
        # ... lógica de onboarding

    async def collect_project_info(self, user_input: str, collected_info: dict) -> dict:
        """Coleta informações do projeto progressivamente"""
        prompt = self.prompt_manager.get_prompt(
            'supervisor',
            'onboarding_collect_info_prompt',
            collected_info=json.dumps(collected_info),
            user_input=user_input,
            missing_info=self._get_missing_info(collected_info)
        )
        # ... lógica de coleta

    async def handle_project_selection(self, user_input: str, projects: list) -> dict:
        """Gerencia seleção de projeto"""
        prompt = self.prompt_manager.get_prompt(
            'supervisor',
            'project_selection_prompt',
            project_list=self._format_project_list(projects),
            user_input=user_input
        )
        # ... lógica de seleção
```

---

## 📊 Estados do Onboarding

O sistema mantém estado da sessão para gerenciar o fluxo:

```python
session_state = {
    'onboarding_active': True,
    'onboarding_step': 'collecting_info',  # ou 'confirming', 'completed'
    'collected_info': {
        'project_name': 'Edifício Solar',
        'project_type': 'residential',
        # ... outras informações
    },
    'selected_project_id': None,
    'last_interaction': datetime.now()
}
```

---

## ✅ Checklist de Implementação

- [ ] Implementar `check_user_has_projects()` no supervisor
- [ ] Implementar `start_onboarding()` no supervisor
- [ ] Implementar `collect_project_info()` no supervisor
- [ ] Implementar `handle_project_selection()` no supervisor
- [ ] Adicionar gerenciamento de estado de sessão
- [ ] Criar testes para fluxo de onboarding
- [ ] Adicionar validação de dados coletados
- [ ] Implementar persistência de projetos no banco
- [ ] Testar fluxo completo end-to-end

---

## 🎯 Benefícios

1. ✅ **Experiência amigável** - Usuário é guiado passo a passo
2. ✅ **Flexibilidade** - Não força a fornecer todas as informações de uma vez
3. ✅ **Conversacional** - Parece uma conversa natural, não um formulário
4. ✅ **Inteligente** - Detecta automaticamente quando precisa de onboarding
5. ✅ **Contextual** - Adapta perguntas baseado no que já foi informado
6. ✅ **Validação** - Confirma informações antes de salvar
7. ✅ **Recuperável** - Usuário pode editar informações antes de confirmar