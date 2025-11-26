# 📊 Sistema de Progresso Duplo

## 🎯 Visão Geral

O sistema agora possui **dois níveis de progresso** que funcionam de forma independente:

1. **Progresso do Cronograma** (`schedule_progress`)
   - Calculado automaticamente baseado nas datas do cronograma
   - Atualiza sozinho conforme o tempo passa
   - Representa o progresso **esperado** da obra

2. **Progresso Real** (`actual_progress`)
   - Calculado baseado nas análises de imagens enviadas
   - Atualiza quando usuário envia fotos da obra
   - Representa o progresso **real/físico** da obra

3. **Progresso Geral** (`overall_progress`)
   - Igual ao `schedule_progress` (atualiza com as datas)
   - Usado como referência principal

---

## 📡 APIs Atualizadas

### API 1: GET `/api/projects/{project_id}`

**Resposta:**
```json
{
  "project_id": "uuid-123",
  "name": "Obra de Teste",
  "overall_progress": 7.58,
  "progress_info": {
    "schedule_progress": 7.58,      // Progresso esperado (baseado em datas)
    "actual_progress": 0,            // Progresso real (baseado em imagens)
    "overall_progress": 7.58,        // = schedule_progress
    "variance": -7.58,               // Diferença (negativo = atrasado)
    "has_schedule": true,            // Tem cronograma cadastrado?
    "has_images": false              // Tem análises de imagem?
  },
  "cronograma": { ... }
}
```

### API 2: GET `/api/projects/`

**Resposta:**
```json
{
  "projects": [
    {
      "project_id": "uuid-123",
      "name": "Obra de Teste",
      "overall_progress": 7.58,
      "progress_info": {
        "schedule_progress": 7.58,
        "actual_progress": 0,
        "overall_progress": 7.58,
        "variance": -7.58,
        "has_schedule": true,
        "has_images": false
      },
      ...
    }
  ],
  "total": 1
}
```

---

## 🎨 Implementação Frontend

### 1. Tela de Detalhes da Obra

#### Layout Sugerido

```
┌─────────────────────────────────────────────┐
│ Progresso Geral                             │
├─────────────────────────────────────────────┤
│                                             │
│ 📅 Progresso do Cronograma:  7.58%  ████░░│
│    (Baseado nas datas planejadas)           │
│                                             │
│ 📸 Progresso Real:            0.00%  ░░░░░░│
│    (Baseado em análises de imagens)         │
│                                             │
│ 📊 Variância:                -7.58% 🔴     │
│    (Obra está ATRASADA)                     │
│                                             │
└─────────────────────────────────────────────┘
```

#### Código React

```jsx
import React, { useEffect, useState } from 'react';
import { Box, LinearProgress, Typography, Card, CardContent } from '@mui/material';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import RemoveIcon from '@mui/icons-material/Remove';

function ProjectProgress({ projectId }) {
  const [progressInfo, setProgressInfo] = useState(null);

  useEffect(() => {
    fetch(`/api/projects/${projectId}`)
      .then(res => res.json())
      .then(data => setProgressInfo(data.progress_info));
  }, [projectId]);

  if (!progressInfo) return <div>Carregando...</div>;

  const { schedule_progress, actual_progress, variance, has_schedule, has_images } = progressInfo;

  // Determina cor da variância
  const getVarianceColor = (variance) => {
    if (variance > 5) return 'success';   // Verde - adiantado
    if (variance < -5) return 'error';     // Vermelho - atrasado
    return 'warning';                      // Amarelo - no prazo
  };

  const getVarianceIcon = (variance) => {
    if (variance > 5) return <TrendingUpIcon />;
    if (variance < -5) return <TrendingDownIcon />;
    return <RemoveIcon />;
  };

  const getVarianceText = (variance) => {
    if (variance > 5) return 'ADIANTADO';
    if (variance < -5) return 'ATRASADO';
    return 'NO PRAZO';
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Progresso Geral
        </Typography>

        {/* Progresso do Cronograma */}
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              📅 Progresso do Cronograma
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {schedule_progress.toFixed(2)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={schedule_progress}
            sx={{ height: 10, borderRadius: 5, backgroundColor: '#e0e0e0' }}
          />
          <Typography variant="caption" color="text.secondary">
            (Baseado nas datas planejadas)
          </Typography>
        </Box>

        {/* Progresso Real */}
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              📸 Progresso Real
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {actual_progress.toFixed(2)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={actual_progress}
            color="secondary"
            sx={{ height: 10, borderRadius: 5, backgroundColor: '#e0e0e0' }}
          />
          <Typography variant="caption" color="text.secondary">
            (Baseado em {has_images ? 'análises de imagens' : 'nenhuma imagem ainda'})
          </Typography>
        </Box>

        {/* Variância */}
        {has_schedule && (
          <Box
            sx={{
              mt: 3,
              p: 2,
              backgroundColor: getVarianceColor(variance) === 'error' ? '#ffebee' :
                               getVarianceColor(variance) === 'success' ? '#e8f5e9' : '#fff3e0',
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}
          >
            {getVarianceIcon(variance)}
            <Box sx={{ flex: 1 }}>
              <Typography variant="body2" fontWeight="bold">
                Variância: {variance > 0 ? '+' : ''}{variance.toFixed(2)}%
              </Typography>
              <Typography variant="caption">
                Obra está {getVarianceText(variance)}
              </Typography>
            </Box>
          </Box>
        )}

        {/* Mensagem se não tem cronograma */}
        {!has_schedule && (
          <Box sx={{ mt: 3, p: 2, backgroundColor: '#f5f5f5', borderRadius: 2 }}>
            <Typography variant="body2" color="text.secondary">
              ℹ️ Cadastre um cronograma para visualizar o progresso esperado
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export default ProjectProgress;
```

---

### 2. Lista de Projetos (Dashboard)

```jsx
function ProjectCard({ project }) {
  const { schedule_progress, actual_progress, variance } = project.progress_info;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6">{project.name}</Typography>

        {/* Dois mini progress bars lado a lado */}
        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          {/* Cronograma */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              📅 Cronograma
            </Typography>
            <LinearProgress
              variant="determinate"
              value={schedule_progress}
              sx={{ height: 6, borderRadius: 3 }}
            />
            <Typography variant="caption" fontWeight="bold">
              {schedule_progress.toFixed(1)}%
            </Typography>
          </Box>

          {/* Real */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              📸 Real
            </Typography>
            <LinearProgress
              variant="determinate"
              value={actual_progress}
              color="secondary"
              sx={{ height: 6, borderRadius: 3 }}
            />
            <Typography variant="caption" fontWeight="bold">
              {actual_progress.toFixed(1)}%
            </Typography>
          </Box>
        </Box>

        {/* Badge de status */}
        {variance < -5 && (
          <Chip
            label="Atrasado"
            color="error"
            size="small"
            sx={{ mt: 1 }}
          />
        )}
        {variance > 5 && (
          <Chip
            label="Adiantado"
            color="success"
            size="small"
            sx={{ mt: 1 }}
          />
        )}
      </CardContent>
    </Card>
  );
}
```

---

## 🔄 Como Funcionam as Atualizações

### Atualização Automática do Cronograma

O `schedule_progress` é **recalculado automaticamente** quando:
- A API GET `/api/projects/{id}` é chamada
- O backend compara a data atual com as datas do cronograma
- Não precisa de nenhuma ação do usuário

**Exemplo:**
```
Hoje: 2025-10-03
Atividade "Alvenaria":
  - Início: 2025-03-24
  - Duração: 27 dias
  - Fim calculado: 2025-04-28

Se hoje > fim:
  expected_progress = 100%

Se hoje entre início e fim:
  dias_decorridos = 15
  expected_progress = (15/27) * 100 = 55.5%

Se hoje < início:
  expected_progress = 0%
```

### Atualização Manual do Progresso Real

O `actual_progress` é **atualizado quando**:
1. Usuário envia imagem pelo chat
2. Visual Agent analisa a imagem
3. Sistema calcula progresso baseado nas atividades detectadas
4. Salva em `metadata.cronograma.summary.actual_progress`

**Código que faz isso:** `supervisor.py:1578-1719`

---

## ⚙️ Backend - Como Funciona

### Estrutura no MongoDB

```json
{
  "project_id": "uuid-123",
  "name": "Obra de Teste",
  "overall_progress": 7.58,  // ← Igual a schedule_progress
  "metadata": {
    "cronograma": {
      "summary": {
        "expected_progress_until_today": 7.58,  // ← schedule_progress
        "actual_progress": 0,                    // ← actual_progress
        "variance": -7.58,                       // ← Diferença
        "total_weight_completed": 15.0,
        "total_weight_in_progress": 30.0,
        "total_weight_remaining": 55.0
      },
      "activities": { ... },
      "calculated_at": "2025-10-03"
    }
  }
}
```

### Cálculo da Variância

```python
variance = actual_progress - schedule_progress

# Exemplo:
# actual_progress = 5%  (baseado em imagens)
# schedule_progress = 10% (baseado em datas)
# variance = -5% (atrasado)

if variance < -5:
    status = "ATRASADO"  # 🔴
elif variance > 5:
    status = "ADIANTADO"  # 🟢
else:
    status = "NO PRAZO"  # 🟡
```

---

## 📊 Exemplo Completo de Uso

### Cenário 1: Obra sem Imagens

```json
{
  "progress_info": {
    "schedule_progress": 15.0,   // 15% esperado baseado em datas
    "actual_progress": 0,         // 0% pois não tem imagens
    "overall_progress": 15.0,     // = schedule_progress
    "variance": -15.0,            // Atrasado (não enviou imagens)
    "has_schedule": true,
    "has_images": false
  }
}
```

**Frontend mostra:**
```
📅 Progresso do Cronograma: 15.00% ███░░░░░░░
📸 Progresso Real:           0.00% ░░░░░░░░░░
📊 Variância: -15.00% 🔴 ATRASADO
   (Envie fotos da obra para atualizar o progresso real)
```

### Cenário 2: Obra Adiantada

```json
{
  "progress_info": {
    "schedule_progress": 15.0,
    "actual_progress": 25.0,   // 25% detectado nas imagens
    "overall_progress": 15.0,
    "variance": 10.0,          // Adiantado!
    "has_schedule": true,
    "has_images": true
  }
}
```

**Frontend mostra:**
```
📅 Progresso do Cronograma: 15.00% ███░░░░░░░
📸 Progresso Real:          25.00% █████░░░░░
📊 Variância: +10.00% 🟢 ADIANTADO
```

### Cenário 3: Obra sem Cronograma

```json
{
  "progress_info": {
    "schedule_progress": 0,
    "actual_progress": 20.0,   // Só tem progresso de imagens
    "overall_progress": 0,
    "variance": 0,
    "has_schedule": false,     // Sem cronograma!
    "has_images": true
  }
}
```

**Frontend mostra:**
```
📸 Progresso Real: 20.00% ████░░░░░░

ℹ️ Cadastre um cronograma para acompanhar o progresso esperado
```

---

## ✅ Checklist de Implementação Frontend

- [ ] Substituir exibição única de progresso por dois componentes separados
- [ ] Mostrar barra de "Progresso do Cronograma" (azul)
- [ ] Mostrar barra de "Progresso Real" (verde/roxo)
- [ ] Calcular e exibir variância com cores:
  - 🔴 Vermelho: variance < -5
  - 🟡 Amarelo: -5 <= variance <= 5
  - 🟢 Verde: variance > 5
- [ ] Adicionar ícones e textos explicativos
- [ ] Mostrar mensagem quando `has_schedule = false`
- [ ] Mostrar mensagem quando `has_images = false`
- [ ] Adicionar tooltip explicando cada tipo de progresso

---

## 🔄 Fluxo Completo

1. **Usuário cadastra projeto** → `overall_progress = 0`
2. **Usuário envia cronograma** → `schedule_progress` começa a ser calculado
3. **Tempo passa** → `schedule_progress` atualiza automaticamente
4. **Usuário envia foto** → Visual Agent analisa
5. **Backend calcula** → Atualiza `actual_progress`
6. **Frontend exibe** → Dois progressos lado a lado + variância

**Tudo automático!** 🎉
