"""
Gerenciador de tokens com MongoDB
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from beanie import PydanticObjectId

from infrastructure.database.token_models import (
    TokenUsageModel,
    TokenAggregationModel,
    UserTokenQuotaModel,
    ModelPricingModel,
    TokenAnalyticsEventModel
)

logger = logging.getLogger(__name__)


class TokenManagerMongo:
    """Gerenciador de tokens usando MongoDB"""

    def __init__(self):
        """Inicializa o gerenciador"""
        self.default_pricing = {
            "x-ai/grok-4-fast": {
                "prompt_price_per_million": 0.0,
                "completion_price_per_million": 0.0,
                "max_context": 131072,
                "max_output": 8192
            },
            "openai/gpt-4": {
                "prompt_price_per_million": 30.0,
                "completion_price_per_million": 60.0,
                "max_context": 128000,
                "max_output": 4096
            },
            "anthropic/claude-3.5-sonnet": {
                "prompt_price_per_million": 3.0,
                "completion_price_per_million": 15.0,
                "max_context": 200000,
                "max_output": 4096
            }
        }

    async def track_usage(
        self,
        session_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        agent_type: Optional[str] = None,
        operation_type: str = "chat",
        metadata: Dict[str, Any] = None
    ) -> TokenUsageModel:
        """Registra uso de tokens no MongoDB"""

        try:
            # Calcula custos
            pricing = await self._get_model_pricing(model)
            prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt_price_per_million"]
            completion_cost = (completion_tokens / 1_000_000) * pricing["completion_price_per_million"]

            # Cria documento
            usage = TokenUsageModel(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                model=model,
                provider="openrouter",
                prompt_cost=prompt_cost,
                completion_cost=completion_cost,
                total_cost=prompt_cost + completion_cost,
                agent_type=agent_type,
                operation_type=operation_type,
                metadata=metadata or {}
            )

            # Salva no MongoDB
            await usage.save()

            # Atualiza agregações
            await self._update_aggregations(usage)

            # Verifica quotas
            await self._check_quotas(session_id, usage.total_tokens)

            logger.info(f"✅ Tokens tracked: {usage.total_tokens} for session {session_id}")
            return usage

        except Exception as e:
            logger.error(f"❌ Error tracking tokens: {e}")
            # Cria evento de erro
            await self._log_event(
                event_type="tracking_error",
                severity="error",
                message=f"Failed to track tokens: {str(e)}",
                session_id=session_id
            )
            raise

    async def get_session_usage(self, session_id: str) -> Dict[str, Any]:
        """Obtém uso total de tokens de uma sessão"""

        try:
            # Busca todos os usos da sessão
            usages = await TokenUsageModel.find(
                TokenUsageModel.session_id == session_id
            ).to_list()

            if not usages:
                return {
                    "session_id": session_id,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "message_count": 0,
                    "by_model": {},
                    "by_agent": {}
                }

            # Agrega dados
            total_tokens = sum(u.total_tokens for u in usages)
            total_cost = sum(u.total_cost for u in usages)

            # Por modelo
            by_model = {}
            for usage in usages:
                if usage.model not in by_model:
                    by_model[usage.model] = {
                        "tokens": 0,
                        "cost": 0.0,
                        "count": 0
                    }
                by_model[usage.model]["tokens"] += usage.total_tokens
                by_model[usage.model]["cost"] += usage.total_cost
                by_model[usage.model]["count"] += 1

            # Por agente
            by_agent = {}
            for usage in usages:
                if usage.agent_type:
                    if usage.agent_type not in by_agent:
                        by_agent[usage.agent_type] = {
                            "tokens": 0,
                            "cost": 0.0,
                            "count": 0
                        }
                    by_agent[usage.agent_type]["tokens"] += usage.total_tokens
                    by_agent[usage.agent_type]["cost"] += usage.total_cost
                    by_agent[usage.agent_type]["count"] += 1

            return {
                "session_id": session_id,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "message_count": len(usages),
                "prompt_tokens": sum(u.prompt_tokens for u in usages),
                "completion_tokens": sum(u.completion_tokens for u in usages),
                "by_model": by_model,
                "by_agent": by_agent,
                "first_usage": usages[0].timestamp.isoformat() if usages else None,
                "last_usage": usages[-1].timestamp.isoformat() if usages else None
            }

        except Exception as e:
            logger.error(f"Error getting session usage: {e}")
            return {}

    async def get_global_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas globais de uso"""

        try:
            # Busca agregação diária atual
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            daily = await TokenAggregationModel.find_one(
                TokenAggregationModel.period == "daily",
                TokenAggregationModel.period_date == today
            )

            # Busca agregação mensal
            month_start = today.replace(day=1)
            monthly = await TokenAggregationModel.find_one(
                TokenAggregationModel.period == "monthly",
                TokenAggregationModel.period_date == month_start
            )

            # Estatísticas gerais
            all_usages = await TokenUsageModel.find().to_list()
            total_all_time = sum(u.total_tokens for u in all_usages)
            total_cost_all_time = sum(u.total_cost for u in all_usages)

            return {
                "all_time": {
                    "total_tokens": total_all_time,
                    "total_cost": total_cost_all_time,
                    "total_messages": len(all_usages),
                    "unique_sessions": len(set(u.session_id for u in all_usages))
                },
                "today": {
                    "total_tokens": daily.total_tokens if daily else 0,
                    "total_cost": daily.total_cost if daily else 0,
                    "sessions": daily.total_sessions if daily else 0,
                    "messages": daily.total_messages if daily else 0
                } if daily else None,
                "this_month": {
                    "total_tokens": monthly.total_tokens if monthly else 0,
                    "total_cost": monthly.total_cost if monthly else 0,
                    "sessions": monthly.total_sessions if monthly else 0,
                    "messages": monthly.total_messages if monthly else 0
                } if monthly else None,
                "top_models": await self._get_top_models(),
                "top_agents": await self._get_top_agents()
            }

        except Exception as e:
            logger.error(f"Error getting global statistics: {e}")
            return {}

    async def get_usage_by_period(self, days: int = 7) -> List[Dict[str, Any]]:
        """Obtém uso por período"""

        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Busca agregações diárias
            aggregations = await TokenAggregationModel.find(
                TokenAggregationModel.period == "daily",
                TokenAggregationModel.period_date >= start_date
            ).sort("period_date").to_list()

            result = []
            for agg in aggregations:
                result.append({
                    "date": agg.period_date.isoformat(),
                    "tokens": agg.total_tokens,
                    "cost": agg.total_cost,
                    "sessions": agg.total_sessions,
                    "messages": agg.total_messages,
                    "avg_tokens_per_message": agg.avg_tokens_per_message,
                    "by_model": agg.by_model
                })

            return result

        except Exception as e:
            logger.error(f"Error getting usage by period: {e}")
            return []

    async def _get_model_pricing(self, model: str) -> Dict[str, float]:
        """Obtém preços do modelo"""

        # Busca no banco
        pricing_doc = await ModelPricingModel.find_one(
            ModelPricingModel.model_name == model
        )

        if pricing_doc:
            return {
                "prompt_price_per_million": pricing_doc.prompt_price_per_million,
                "completion_price_per_million": pricing_doc.completion_price_per_million
            }

        # Usa default ou retorna zero
        return self.default_pricing.get(model, {
            "prompt_price_per_million": 0.0,
            "completion_price_per_million": 0.0
        })

    async def _update_aggregations(self, usage: TokenUsageModel):
        """Atualiza agregações de tokens"""

        try:
            # Agregação diária
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            daily = await TokenAggregationModel.find_one(
                TokenAggregationModel.period == "daily",
                TokenAggregationModel.period_date == today
            )

            if not daily:
                daily = TokenAggregationModel(
                    period="daily",
                    period_date=today
                )

            # Atualiza totais
            daily.total_tokens += usage.total_tokens
            daily.total_cost += usage.total_cost
            daily.total_messages += 1

            # Atualiza por modelo
            if usage.model not in daily.by_model:
                daily.by_model[usage.model] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "count": 0
                }
            daily.by_model[usage.model]["tokens"] += usage.total_tokens
            daily.by_model[usage.model]["cost"] += usage.total_cost
            daily.by_model[usage.model]["count"] += 1

            # Atualiza por agente
            if usage.agent_type:
                if usage.agent_type not in daily.by_agent:
                    daily.by_agent[usage.agent_type] = {
                        "tokens": 0,
                        "cost": 0.0,
                        "count": 0
                    }
                daily.by_agent[usage.agent_type]["tokens"] += usage.total_tokens
                daily.by_agent[usage.agent_type]["cost"] += usage.total_cost
                daily.by_agent[usage.agent_type]["count"] += 1

            # Calcula médias
            if daily.total_messages > 0:
                daily.avg_tokens_per_message = daily.total_tokens / daily.total_messages

            daily.updated_at = datetime.utcnow()
            await daily.save()

            # Agregação mensal
            month_start = today.replace(day=1)
            monthly = await TokenAggregationModel.find_one(
                TokenAggregationModel.period == "monthly",
                TokenAggregationModel.period_date == month_start
            )

            if not monthly:
                monthly = TokenAggregationModel(
                    period="monthly",
                    period_date=month_start
                )

            # Atualiza totais mensais (similar ao diário)
            monthly.total_tokens += usage.total_tokens
            monthly.total_cost += usage.total_cost
            monthly.total_messages += 1

            await monthly.save()

        except Exception as e:
            logger.error(f"Error updating aggregations: {e}")

    async def _check_quotas(self, session_id: str, tokens_used: int):
        """Verifica quotas de uso"""

        # Por enquanto, apenas registra eventos se uso alto
        if tokens_used > 10000:  # Mais de 10k tokens em uma requisição
            await self._log_event(
                event_type="high_usage",
                severity="warning",
                message=f"High token usage: {tokens_used} tokens",
                session_id=session_id,
                details={"tokens": tokens_used}
            )

    async def _log_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Dict[str, Any] = None
    ):
        """Registra evento de analytics"""

        try:
            event = TokenAnalyticsEventModel(
                event_type=event_type,
                severity=severity,
                message=message,
                session_id=session_id,
                user_id=user_id,
                details=details or {}
            )
            await event.save()
        except Exception as e:
            logger.error(f"Error logging event: {e}")

    async def _get_top_models(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtém modelos mais usados"""

        try:
            # Agregação para pegar top models
            pipeline = [
                {"$group": {
                    "_id": "$model",
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost": {"$sum": "$total_cost"},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"total_tokens": -1}},
                {"$limit": limit}
            ]

            results = await TokenUsageModel.aggregate(pipeline).to_list()

            return [
                {
                    "model": r["_id"],
                    "tokens": r["total_tokens"],
                    "cost": r["total_cost"],
                    "requests": r["count"]
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error getting top models: {e}")
            return []

    async def _get_top_agents(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtém agentes mais usados"""

        try:
            pipeline = [
                {"$match": {"agent_type": {"$ne": None}}},
                {"$group": {
                    "_id": "$agent_type",
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost": {"$sum": "$total_cost"},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"total_tokens": -1}},
                {"$limit": limit}
            ]

            results = await TokenUsageModel.aggregate(pipeline).to_list()

            return [
                {
                    "agent": r["_id"],
                    "tokens": r["total_tokens"],
                    "cost": r["total_cost"],
                    "requests": r["count"]
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error getting top agents: {e}")
            return []

    async def export_token_report(self, format: str = "json") -> Dict[str, Any]:
        """Exporta relatório de tokens"""

        try:
            # Coleta todas as informações
            stats = await self.get_global_statistics()
            recent_usage = await self.get_usage_by_period(30)

            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "statistics": stats,
                "recent_usage": recent_usage,
                "top_sessions": await self._get_top_sessions(),
                "events": await self._get_recent_events()
            }

            return report

        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return {}

    async def _get_top_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém sessões com maior uso"""

        try:
            pipeline = [
                {"$group": {
                    "_id": "$session_id",
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost": {"$sum": "$total_cost"},
                    "count": {"$sum": 1},
                    "first_use": {"$min": "$timestamp"},
                    "last_use": {"$max": "$timestamp"}
                }},
                {"$sort": {"total_tokens": -1}},
                {"$limit": limit}
            ]

            results = await TokenUsageModel.aggregate(pipeline).to_list()

            return [
                {
                    "session_id": r["_id"],
                    "tokens": r["total_tokens"],
                    "cost": r["total_cost"],
                    "messages": r["count"],
                    "first_use": r["first_use"].isoformat(),
                    "last_use": r["last_use"].isoformat()
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error getting top sessions: {e}")
            return []

    async def _get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtém eventos recentes"""

        try:
            events = await TokenAnalyticsEventModel.find().sort("-timestamp").limit(limit).to_list()

            return [
                {
                    "type": e.event_type,
                    "severity": e.severity,
                    "message": e.message,
                    "timestamp": e.timestamp.isoformat(),
                    "details": e.details
                }
                for e in events
            ]

        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []


# Instância global
token_manager_mongo = TokenManagerMongo()
