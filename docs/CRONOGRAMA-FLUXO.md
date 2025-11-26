# 📅 Fluxo Completo do Cronograma

## 🎯 Visão Geral

Após o usuário cadastrar um projeto, o sistema pergunta sobre cronograma e **automaticamente calcula o progresso esperado** baseado nas datas e na data atual.

---

## 📝 1. Quando o Sistema Pergunta

### Trigger: Após Cadastro do Projeto

Quando o projeto é cadastrado (após `[CADASTRAR_PROJETO]` ser processado), o sistema pergunta:

```
✅ Obra cadastrada com sucesso!

Você possui um cronograma de atividades com percentuais de andamento?
Se sim, pode compartilhar os percentuais das atividades já executadas?
```

---

## 📊 2. Formato de Resposta Aceito

O usuário pode enviar o cronograma em **qualquer formato**. Exemplo:

```
## Cronograma de Atividades da Obra

**1. Prumada**
- Duração: 2 dias úteis
- Data de início: 24/03/2025
- Porcentagem: 2,00%

**2. Alvenaria**
- Duração: 27 dias úteis
- Data de início: 24/03/2025
- Porcentagem: 12,00%

... (28 atividades total)
```

---

## 🤖 3. O Que o Sistema Faz Automaticamente

### Passo 1: Detecção via Marker `[SALVAR_CRONOGRAMA]`

O LLM analisa a conversa e quando detecta dados de cronograma, adiciona o marker `[SALVAR_CRONOGRAMA]` na resposta.

**Código:** `supervisor.py:1982`
```python
if '[SALVAR_CRONOGRAMA]' in response_text:
    cronograma_data = await self._extract_cronograma_from_conversation(messages)
```

### Passo 2: Extração dos Dados via LLM

**Função:** `_extract_cronograma_from_conversation()`
**Código:** `supervisor.py:1461-1577`

O sistema usa LLM para extrair:
- ✅ Nome da atividade (normalizado para 28 atividades padrão)
- ✅ Percentual (peso da atividade no projeto)
- ✅ Duração em dias úteis
- ✅ Data de início

**Saída do LLM:**
```json
{
  "has_cronograma_data": true,
  "activities": {
    "alvenaria": {
      "percentage": 12.0,
      "duration_days": 27,
      "start_date": "2025-03-24"
    },
    "contrapiso": {
      "percentage": 6.0,
      "duration_days": 12,
      "start_date": "2025-05-26"
    }
  }
}
```

### Passo 3: Cálculo Automático do Progresso Esperado

**Função:** `_save_cronograma_to_project()`
**Código:** `supervisor.py:1578-1719`

Para **cada atividade**, o sistema:

1. **Calcula data de término:**
   ```python
   end_date = start_date + timedelta(days=duration_days * 1.4)  # Ajuste para fins de semana
   ```

2. **Compara com data atual:**
   ```python
   current_date = now_brazil().date()

   if current_date >= end_date:
       status = "deveria_estar_concluída"
       expected_progress = 100%

   elif current_date >= start_date:
       status = "em_andamento"
       expected_progress = (dias_decorridos / duração_total) * 100

   else:
       status = "não_iniciada"
       expected_progress = 0%
   ```

3. **Calcula peso ponderado:**
   ```python
   total_expected_progress += (weight / 100) * expected_progress
   ```

### Passo 4: Salvar no MongoDB

**Estrutura salva em `metadata.cronograma`:**

```json
{
  "metadata": {
    "cronograma": {
      "activities": {
        "alvenaria": {
          "percentage": 12.0,
          "duration_days": 27,
          "start_date": "2025-03-24",
          "end_date": "2025-04-28",
          "expected_progress": 85.5,     // ← Calculado automaticamente!
          "actual_progress": 0,           // ← Atualizado por análise de imagens
          "status": "em_andamento"        // ← Calculado baseado na data
        }
      },
      "summary": {
        "total_weight_completed": 15.0,          // Soma dos pesos das atividades concluídas
        "total_weight_in_progress": 30.0,        // Soma dos pesos em andamento
        "total_weight_remaining": 55.0,          // Soma dos pesos não iniciadas
        "expected_progress_until_today": 45.2,   // Progresso esperado até hoje
        "actual_progress": 0                     // Progresso real (baseado em imagens)
      },
      "updated_at": "2025-10-03T20:00:00",
      "calculated_at": "2025-10-03"
    }
  },
  "overall_progress": 0  // ← Representa progresso REAL (não esperado)
}
```

---

## 📡 4. APIs para Acessar os Dados

### API 1: Detalhes do Projeto (com cronograma)

**Endpoint:** `GET /api/projects/{project_id}`

**Resposta:**
```json
{
  "project_id": "uuid-123",
  "name": "Obra Teste",
  "overall_progress": 0,
  "cronograma": {
    "activities": { ... },
    "summary": { ... },
    "updated_at": "2025-10-03T20:00:00",
    "calculated_at": "2025-10-03"
  }
}
```

### API 2: Cronograma Detalhado (com status atual)

**Endpoint:** `GET /api/projects/{project_id}/cronograma`

**Resposta:**
```json
{
  "has_cronograma": true,
  "project_id": "uuid-123",
  "project_name": "Obra Teste",
  "current_date": "2025-10-03",
  "summary": {
    "total_weight_completed": 15.0,
    "total_weight_in_progress": 30.0,
    "total_weight_remaining": 55.0,
    "expected_progress_until_today": 45.2,
    "actual_progress": 0,
    "variance": -45.2  // Diferença (negativo = atrasado)
  },
  "activities": [
    {
      "name": "alvenaria",
      "percentage": 12.0,
      "duration_days": 27,
      "start_date": "2025-03-24",
      "end_date": "2025-04-28",
      "expected_progress": 85.5,
      "actual_progress": 0,
      "status": "em_andamento",
      "days_elapsed": 15,
      "days_remaining": 10
    }
  ],
  "total_activities": 28
}
```

---

## 🖥️ 5. Como Visualizar no Frontend

### Opção 1: Na Tela de Detalhes do Projeto

```javascript
const response = await fetch(`/api/projects/${projectId}`);
const project = await response.json();

if (project.cronograma) {
  const summary = project.cronograma.summary;

  console.log(`Progresso esperado: ${summary.expected_progress_until_today}%`);
  console.log(`Progresso real: ${summary.actual_progress}%`);
  console.log(`Variância: ${summary.actual_progress - summary.expected_progress_until_today}%`);
}
```

### Opção 2: Tela Dedicada de Cronograma

```javascript
const response = await fetch(`/api/projects/${projectId}/cronograma`);
const cronograma = await response.json();

// Renderizar gráfico de Gantt
cronograma.activities.forEach(activity => {
  renderGanttBar({
    name: activity.name,
    startDate: activity.start_date,
    endDate: activity.end_date,
    expectedProgress: activity.expected_progress,
    actualProgress: activity.actual_progress,
    status: activity.status  // "em_andamento", "deveria_estar_concluída", "não_iniciada"
  });
});

// Mostrar indicador de atraso/adiantamento
const variance = cronograma.summary.variance;
if (variance < -5) {
  showAlert(`Obra atrasada em ${Math.abs(variance).toFixed(1)}%`);
}
```

---

## 🎨 6. Sugestões de Visualização

### Dashboard de Progresso

```
┌─────────────────────────────────────┐
│ CRONOGRAMA DA OBRA                  │
├─────────────────────────────────────┤
│                                     │
│ Progresso Esperado:  45.2% ████▓░░│
│ Progresso Real:       0.0% ░░░░░░░│
│                                     │
│ Status: ATRASADO (-45.2%)          │
│                                     │
│ Atividades:                         │
│ ✅ Concluídas:      15.0% (3)     │
│ 🔄 Em Andamento:    30.0% (8)     │
│ ⏸️  Não Iniciadas:   55.0% (17)    │
│                                     │
└─────────────────────────────────────┘
```

### Tabela de Atividades

| Atividade | % | Status | Início | Término | Esperado | Real | Dias Restantes |
|-----------|---|--------|--------|---------|----------|------|----------------|
| Alvenaria | 12% | 🔄 Em andamento | 24/03 | 28/04 | 85.5% | 0% | 10 dias |
| Contrapiso | 6% | ⏸️ Não iniciada | 26/05 | 10/06 | 0% | 0% | 54 dias |

---

## ✅ Resumo do Fluxo

1. **Usuário cadastra projeto** → Sistema pergunta sobre cronograma
2. **Usuário envia cronograma** → LLM extrai dados estruturados
3. **Sistema calcula automaticamente:**
   - Data de término de cada atividade
   - Progresso esperado baseado na data atual
   - Status de cada atividade
   - Peso ponderado de progresso total
4. **Salva no MongoDB** → `metadata.cronograma`
5. **Frontend acessa via API:**
   - `GET /api/projects/{id}` → Dados gerais + cronograma
   - `GET /api/projects/{id}/cronograma` → Detalhes completos

**Tudo é calculado automaticamente baseado nas datas!** 🎉
