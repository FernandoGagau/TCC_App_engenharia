"""
Sistema de Rastreamento de Tokens com MongoDB
Substitui completamente o armazenamento em arquivos JSON
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import yaml
from pathlib import Path
import tiktoken
import logging
from uuid import uuid4

from infrastructure.database.token_models import (
    TokenUsageModel,
    TokenSessionSummaryModel
)
from infrastructure.database.mongodb import MongoDB

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Classe de dados para uso de tokens"""
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    timestamp: datetime
    metadata: Dict[str, Any]


class TokenTrackerMongo:
    """Gerenciador de rastreamento de tokens com MongoDB"""

    def __init__(self, config_path: str = "config/token_config.yaml"):
        """Inicializa o rastreador"""
        # Carrega configuração
        self.config = self._load_config(config_path)
        self.models_cost = self.config.get('models', {})
        self.limits = self.config.get('limits', {'default': 50000})
        
        # Inicializa tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def _load_config(self, config_path: str) -> Dict:
        """Carrega configuração do YAML"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
        return {}

    def count_tokens(self, text: str) -> int:
        """Conta tokens em um texto"""
        try:
            return len(self.tokenizer.encode(text))
        except:
            # Fallback: estimativa simples
            return len(text) // 4

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estima custo baseado no modelo e tokens"""
        if model not in self.models_cost:
            logger.warning(f"Modelo {model} não encontrado na configuração de custos")
            # Usa valores padrão
            model_costs = {'input': 0.0001, 'output': 0.0004}
        else:
            model_costs = self.models_cost[model]

        input_cost = (input_tokens / 1000) * model_costs['input']
        output_cost = (output_tokens / 1000) * model_costs['output']

        return round(input_cost + output_cost, 6)

    async def track_request(
        self,
        session_id: str,
        model: str,
        input_text: str,
        output_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TokenUsage:
        """Rastreia uma requisição no MongoDB"""
        
        input_tokens = self.count_tokens(input_text)
        output_tokens = self.count_tokens(output_text)
        total_tokens = input_tokens + output_tokens
        
        # Calcula custo
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        
        # Cria registro no MongoDB
        token_usage = TokenUsageModel(
            session_id=session_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            input_text=input_text[:1000],  # Salva apenas primeiros 1000 chars
            output_text=output_text[:1000],
            metadata=metadata or {}
        )
        
        # Salva no MongoDB
        await token_usage.save()
        
        # Atualiza resumo da sessão
        await self._update_session_summary(session_id, token_usage)
        
        # Verifica limites
        await self._check_limits(session_id, total_tokens)
        
        return TokenUsage(
            session_id=session_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            timestamp=token_usage.timestamp,
            metadata=metadata or {}
        )

    async def _update_session_summary(self, session_id: str, usage: TokenUsageModel):
        """Atualiza resumo da sessão no MongoDB"""
        
        # Busca ou cria resumo da sessão
        summary = await TokenSessionSummaryModel.find_one(
            TokenSessionSummaryModel.session_id == session_id
        )
        
        if not summary:
            summary = TokenSessionSummaryModel(
                session_id=session_id,
                first_request=usage.timestamp
            )
        
        # Atualiza totais
        summary.total_tokens += usage.total_tokens
        summary.total_input_tokens += usage.input_tokens
        summary.total_output_tokens += usage.output_tokens
        summary.total_cost += usage.cost
        summary.total_requests += 1
        
        # Atualiza por modelo
        if usage.model not in summary.models_used:
            summary.models_used[usage.model] = {
                "tokens": 0,
                "cost": 0.0,
                "requests": 0
            }
        
        summary.models_used[usage.model]["tokens"] += usage.total_tokens
        summary.models_used[usage.model]["cost"] += usage.cost
        summary.models_used[usage.model]["requests"] += 1
        
        # Atualiza timestamps
        summary.last_request = usage.timestamp
        summary.updated_at = datetime.utcnow()
        
        # Salva no MongoDB
        await summary.save()

    async def _check_limits(self, session_id: str, new_tokens: int):
        """Verifica limites de tokens"""
        
        summary = await TokenSessionSummaryModel.find_one(
            TokenSessionSummaryModel.session_id == session_id
        )
        
        if summary:
            # Verifica se excedeu o limite
            if summary.total_tokens + new_tokens > summary.limit_tokens:
                summary.limit_reached = True
                await summary.save()
                logger.warning(f"Sessão {session_id} excedeu limite de tokens")
            
            # Verifica se está próximo do limite
            elif summary.total_tokens + new_tokens > (summary.limit_tokens * summary.warning_threshold):
                if not summary.warning_sent:
                    summary.warning_sent = True
                    await summary.save()
                    logger.warning(f"Sessão {session_id} próxima do limite de tokens")

    async def get_session_usage(self, session_id: str) -> Dict[str, Any]:
        """Retorna uso de tokens de uma sessão"""
        
        summary = await TokenSessionSummaryModel.find_one(
            TokenSessionSummaryModel.session_id == session_id
        )
        
        if not summary:
            return {
                "session_id": session_id,
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost": 0.0,
                "requests": 0,
                "models_used": [],
                "percentage_of_limit": 0.0,
                "warning": False,
                "limit_reached": False
            }
        
        return {
            "session_id": session_id,
            "total_tokens": summary.total_tokens,
            "input_tokens": summary.total_input_tokens,
            "output_tokens": summary.total_output_tokens,
            "total_cost": summary.total_cost,
            "requests": summary.total_requests,
            "models_used": list(summary.models_used.keys()),
            "percentage_of_limit": (summary.total_tokens / summary.limit_tokens) * 100,
            "warning": summary.warning_sent,
            "limit_reached": summary.limit_reached
        }

    async def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Retorna resumo diário de uso"""
        
        if not date:
            date = datetime.utcnow()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Busca todos os usos do dia
        daily_usage = await TokenUsageModel.find(
            TokenUsageModel.timestamp >= start_of_day,
            TokenUsageModel.timestamp < end_of_day
        ).to_list()
        
        # Calcula totais
        total_tokens = sum(u.total_tokens for u in daily_usage)
        total_cost = sum(u.cost for u in daily_usage)
        total_requests = len(daily_usage)
        
        # Agrupa por modelo
        by_model = {}
        for usage in daily_usage:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0
                }
            by_model[usage.model]["tokens"] += usage.total_tokens
            by_model[usage.model]["cost"] += usage.cost
            by_model[usage.model]["requests"] += 1
        
        # Top sessões
        sessions = {}
        for usage in daily_usage:
            if usage.session_id not in sessions:
                sessions[usage.session_id] = {
                    "tokens": 0,
                    "cost": 0.0
                }
            sessions[usage.session_id]["tokens"] += usage.total_tokens
            sessions[usage.session_id]["cost"] += usage.cost
        
        top_sessions = sorted(
            [{"session_id": k, **v} for k, v in sessions.items()],
            key=lambda x: x["tokens"],
            reverse=True
        )[:10]
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_requests": total_requests,
            "total_sessions": len(sessions),
            "by_model": by_model,
            "top_sessions": top_sessions
        }

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove dados antigos do MongoDB"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Remove usos antigos
        result = await TokenUsageModel.find(
            TokenUsageModel.timestamp < cutoff_date
        ).delete()
        
        if result.deleted_count > 0:
            logger.info(f"Removidos {result.deleted_count} registros de token antigos")
        
        # Remove resumos de sessões antigas sem atividade
        old_summaries = await TokenSessionSummaryModel.find(
            TokenSessionSummaryModel.last_request < cutoff_date
        ).delete()
        
        if old_summaries.deleted_count > 0:
            logger.info(f"Removidos {old_summaries.deleted_count} resumos de sessão antigos")


# Versão síncrona para compatibilidade
class TokenTracker:
    """Wrapper síncrono para compatibilidade com código existente"""
    
    def __init__(self, config_path: str = "config/token_config.yaml"):
        self.async_tracker = TokenTrackerMongo(config_path)
    
    def count_tokens(self, text: str) -> int:
        return self.async_tracker.count_tokens(text)
    
    def track_request(self, *args, **kwargs) -> TokenUsage:
        """Versão síncrona do track_request"""
        return asyncio.create_task(self.async_tracker.track_request(*args, **kwargs))
    
    def get_session_usage(self, session_id: str) -> Dict[str, Any]:
        """Versão síncrona do get_session_usage"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.async_tracker.get_session_usage(session_id)
            )
        finally:
            loop.close()
    
    def check_token_limit(self, session_id: str, estimated_tokens: int) -> Dict[str, Any]:
        """Verifica limite de tokens"""
        usage = self.get_session_usage(session_id)
        limit = 50000  # Limite padrão
        
        total_with_new = usage['total_tokens'] + estimated_tokens
        percentage = (total_with_new / limit) * 100
        
        return {
            'allowed': total_with_new < limit,
            'tokens_remaining': max(0, limit - total_with_new),
            'warning': percentage > 80,
            'percentage': percentage
        }
