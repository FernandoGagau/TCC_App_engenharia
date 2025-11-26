# Sistema de Rastreamento de Tokens e Custos

Este documento explica como o sistema rastreia o uso de tokens e calcula custos do OpenRouter.

## Modelos e Preços

O sistema utiliza dois modelos principais do OpenRouter:

### x-ai/grok-4-fast (Chat)
- **Uso**: Conversas de texto, onboarding, perguntas gerais
- **Input**: $0.20 / 1M tokens
- **Output**: $0.50 / 1M tokens

### google/gemini-2.5-flash-image-preview (Visão)
- **Uso**: Análise de imagens, detecção de progresso visual
- **Input**: $0.30 / 1M tokens
- **Output**: $2.50 / 1M tokens

## Como Funciona

### 1. Rastreamento de Tokens

Cada mensagem salva rastreia:
- `input_tokens`: Tokens do prompt (pergunta do usuário + contexto)
- `output_tokens`: Tokens da resposta (resposta do assistente)
- `tokens_used`: Total (input + output)

### 2. Cálculo de Custo

O custo é calculado separadamente para input e output:

```python
custo_total = (input_tokens × preço_input / 1M) + (output_tokens × preço_output / 1M)
```

**Exemplo (Grok):**
- Input: 1000 tokens → $0.0002 (1000 × $0.20 / 1M)
- Output: 500 tokens → $0.00025 (500 × $0.50 / 1M)
- **Total**: $0.00045

**Exemplo (Gemini com imagem):**
- Input: 2000 tokens → $0.0006 (2000 × $0.30 / 1M)
- Output: 800 tokens → $0.002 (800 × $2.50 / 1M)
- **Total**: $0.0026

### 3. Detecção de Modelo

O sistema detecta qual modelo usar baseado em:
- Se a mensagem tem anexos (imagens) → Gemini Vision
- Se é apenas texto → Grok Chat

### 4. Acumulação por Sessão

Cada sessão mantém:
- `total_tokens`: Soma de todos os tokens da sessão
- `total_cost`: Soma de todos os custos em USD

## Configuração

### Atualizar Preços

Para atualizar os preços dos modelos, edite:
```
backend/src/infrastructure/config/model_pricing.py
```

```python
MODEL_PRICING = {
    "x-ai/grok-4-fast": {
        "input": 0.20,   # Atualizar aqui
        "output": 0.50,  # Atualizar aqui
    },
    # ...
}
```

### Adicionar Novos Modelos

Para adicionar um novo modelo:

1. Adicione ao `model_pricing.py`:
```python
MODEL_PRICING = {
    # ...modelos existentes...

    "novo-modelo/nome": {
        "input": 0.15,
        "output": 0.45,
        "description": "Descrição do modelo"
    }
}
```

2. Atualize a lógica de detecção em `get_model_pricing()` se necessário

## Migração de Dados Existentes

Para sessões antigas que não têm tokens rastreados, use o script de migração:

```bash
python3 backend/migrate_session_costs.py
```

Este script:
1. Estima tokens baseado no comprimento do texto
2. Calcula custos usando os preços corretos
3. Atualiza todas as sessões existentes

## Dashboard

O dashboard mostra:
- **Total de Tokens**: Soma de todos os tokens usados
- **Custo Total**: Soma de todos os custos em USD
- **Custo por Sessão**: Custo individual de cada sessão
- **Projeção Mensal**: Estimativa de custo baseado no uso dos últimos 7 dias

## Referências

- OpenRouter Pricing: https://openrouter.ai/models
- Grok 4 Fast: https://openrouter.ai/x-ai/grok-4-fast
- Gemini 2.5 Flash: https://openrouter.ai/google/gemini-2.5-flash-image-preview

## Notas Importantes

1. **Precisão**: Os tokens são estimados para mensagens antigas, mas rastreados com precisão para novas mensagens
2. **Fallback**: Se input/output não estiverem disponíveis, o sistema assume 40% input, 60% output
3. **Cache**: O sistema não usa cache do OpenRouter por padrão, então todos os tokens são cobrados
4. **Arredondamento**: Custos são armazenados com 6 casas decimais para precisão máxima
