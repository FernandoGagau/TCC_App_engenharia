"""
Modelos MongoDB para Token Tracking
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4
from beanie import Document, Indexed
from pydantic import Field, BaseModel


class TokenUsageModel(Document):
    """Modelo MongoDB para uso de tokens"""

    # Identificadores
    session_id: Indexed(str)  # ID da sessão de chat
    request_id: str = Field(default_factory=lambda: str(uuid4()))  # ID único da requisição

    # Dados de uso
    model: str  # Modelo usado (ex: gpt-4, claude-3)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Custo
    cost: float = 0.0

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Contexto
    input_text: Optional[str] = None
    output_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "token_usage"
        indexes = [
            "session_id",
            "timestamp",
            "model"
        ]


class TokenSessionSummaryModel(Document):
    """Modelo MongoDB para resumo de sessão de tokens"""

    session_id: Indexed(str, unique=True)

    # Totais
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_requests: int = 0

    # Por modelo
    models_used: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Timestamps
    first_request: Optional[datetime] = None
    last_request: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Limites e alertas
    limit_tokens: int = 50000  # Limite padrão
    warning_threshold: float = 0.8  # 80% do limite
    limit_reached: bool = False
    warning_sent: bool = False

    class Settings:
        name = "token_sessions"
        indexes = [
            "session_id",
            "created_at", 
            "total_cost"
        ]
