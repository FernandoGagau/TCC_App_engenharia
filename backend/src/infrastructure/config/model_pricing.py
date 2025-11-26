"""
Configuração de preços dos modelos OpenRouter
Preços em USD por milhão de tokens
Atualizado em: 2025-10-04
"""

# Preços oficiais do OpenRouter (USD por 1M tokens)
MODEL_PRICING = {
    # Grok 4 Fast - Chat principal
    "x-ai/grok-4-fast": {
        "input": 0.20,
        "output": 0.50,
        "description": "Modelo de chat rápido da xAI"
    },

    # Gemini 2.5 Flash - Visão
    "google/gemini-2.5-flash-image-preview": {
        "input": 0.30,
        "output": 2.50,
        "description": "Modelo de visão do Google"
    },

    # Fallback padrão
    "default": {
        "input": 0.20,
        "output": 0.50,
        "description": "Preço padrão caso modelo não seja encontrado"
    }
}


def get_model_pricing(model_name: str) -> dict:
    """
    Retorna o pricing para um modelo específico

    Args:
        model_name: Nome do modelo (ex: "x-ai/grok-4-fast")

    Returns:
        dict com chaves 'input' e 'output' contendo preços por milhão de tokens
    """
    # Verifica se é um modelo conhecido
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]

    # Verifica por substring (ex: se contém 'gemini' ou 'grok')
    model_lower = model_name.lower()

    if 'gemini' in model_lower or 'vision' in model_lower:
        return MODEL_PRICING["google/gemini-2.5-flash-image-preview"]

    if 'grok' in model_lower:
        return MODEL_PRICING["x-ai/grok-4-fast"]

    # Retorna pricing padrão
    return MODEL_PRICING["default"]


def calculate_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """
    Calcula o custo total baseado nos tokens e modelo

    Args:
        input_tokens: Número de tokens de entrada
        output_tokens: Número de tokens de saída
        model_name: Nome do modelo usado

    Returns:
        Custo total em USD
    """
    pricing = get_model_pricing(model_name)

    input_cost = (input_tokens * pricing["input"]) / 1_000_000
    output_cost = (output_tokens * pricing["output"]) / 1_000_000

    return input_cost + output_cost
