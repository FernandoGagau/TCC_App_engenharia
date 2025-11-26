"""
API Routes com Histórico e Controle de Tokens
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from domain.chat_history_mongo import ChatHistoryManagerMongo as ChatHistoryManager, ChatSession, ChatMessage
from infrastructure.token_tracker_mongo import TokenTrackerMongo
from infrastructure.llm_service import get_llm_service
from domain.agents.construction_agent import ConstructionAnalysisAgent
from application.services.timeline_service import TimelineService

# Inicializa serviços
chat_history = ChatHistoryManager()
token_tracker = TokenTrackerMongo()
timeline_service = TimelineService()
logger = logging.getLogger(__name__)

# Inicializa o agente LangGraph
try:
    construction_agent = ConstructionAnalysisAgent()
    logger.info("Agente LangGraph inicializado com sucesso")
except Exception as e:
    logger.warning(f"Erro ao inicializar agente LangGraph: {e}. Usando fallback.")
    construction_agent = None

router = APIRouter()


# ===== MODELS =====
class StartChatRequest(BaseModel):
    project_name: str
    user_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    attachments: Optional[List[Dict]] = None


class SessionResponse(BaseModel):
    session_id: str
    project_name: str
    status: str
    started_at: str
    last_activity: str
    message_count: int
    total_tokens: int
    total_cost: float


# ===== CHAT ENDPOINTS =====
@router.post("/chat/start")
async def start_chat(request: StartChatRequest):
    """Inicia nova conversa de documentação"""
    try:
        # Cria nova sessão sem mensagem de boas-vindas
        session = await chat_history.create_session(
            project_name=request.project_name,
            user_id=request.user_id,
            add_greeting=False
        )

        return {
            "session_id": session.id,
            "project_name": session.project_name,
            "status": session.status,
            "state": "initial",
            "message": "",  # Sem mensagem automática - aguarda primeira mensagem do usuário
            "token_info": await token_tracker.get_session_usage(session.id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/message")
async def send_message(request: SendMessageRequest):
    """Envia mensagem para o agente"""
    logger.info(f"📨 Received message request - session_id: {request.session_id}, message: {request.message[:50] if request.message else 'None'}...")

    try:
        # Se session_id é None, cria nova sessão automaticamente
        if not request.session_id:
            logger.info("Creating new session automatically as session_id is None")
            session = await chat_history.create_session()
            request.session_id = session.id
            logger.info(f"✨ New session created: {session.id}")
        else:
            # Verifica se a sessão existe
            session = await chat_history.get_session(request.session_id)
            if not session:
                logger.error(f"Session {request.session_id} not found")
                raise HTTPException(status_code=404, detail="Sessão não encontrada")

        # Estima tokens da mensagem
        estimated_tokens = token_tracker.count_tokens(request.message)
        usage = await token_tracker.get_session_usage(request.session_id)
        limit = 50000  # Limite padrão
        total_with_new = usage['total_tokens'] + estimated_tokens
        percentage = (total_with_new / limit) * 100

        token_check = {
            'allowed': total_with_new < limit,
            'tokens_remaining': max(0, limit - total_with_new),
            'warning': percentage > 80,
            'percentage': percentage
        }

        if not token_check['allowed']:
            raise HTTPException(
                status_code=429,
                detail=f"Limite de tokens excedido. Tokens restantes: {token_check['tokens_remaining']}"
            )

        # Adiciona mensagem do usuário
        logger.info(f"📝 API: About to save USER message to MongoDB: {request.message[:50]}...")
        await chat_history.add_message(
            session_id=request.session_id,
            role='user',
            content=request.message,
            attachments=request.attachments or []
        )
        logger.info(f"✅ API: USER message saved to MongoDB")

        # Gera resposta do assistente
        try:
            # Tenta usar o agente LangGraph primeiro
            logger.info(f"Construction agent status: {construction_agent is not None}")
            if construction_agent:
                logger.info("Usando agente LangGraph para processar mensagem")

                # Processa com o agente multi-agente
                agent_result = await construction_agent.process_message(
                    session_id=request.session_id,
                    message=request.message,
                    attachments=request.attachments
                )

                if agent_result.get("success"):
                    assistant_response = agent_result.get("response", "")

                    # Adiciona informações de análise se disponível
                    analysis_results = agent_result.get("analysis_results", {})
                    if analysis_results:
                        assistant_response += f"\n\n📊 **Análise Detalhada:**\n"

                        if "visual" in analysis_results:
                            visual = analysis_results["visual"]
                            assistant_response += f"- Fase detectada: {visual.get('phase_detected', 'N/A')}\n"
                            assistant_response += f"- Progresso: {visual.get('progress_percentage', 0)}%\n"

                        if "progress" in analysis_results:
                            progress = analysis_results["progress"]
                            assistant_response += f"- Status da timeline: {progress.get('timeline_status', 'N/A')}\n"

                        if "quality" in analysis_results:
                            quality = analysis_results["quality"]
                            assistant_response += f"- Score de qualidade: {quality.get('score', 0)}/10\n"
                else:
                    raise Exception("Agente LangGraph falhou, usando fallback")

            else:
                # Fallback para o LLM simples
                llm_service = get_llm_service()

                # Pega histórico da conversa para contexto
                messages = await chat_history.get_session_messages(request.session_id, limit=10)
                conversation_context = []

                for msg in messages[-5:]:  # Últimas 5 mensagens para contexto
                    conversation_context.append({
                        "role": msg.role,
                        "content": msg.content
                    })

                # Gera resposta
                assistant_response = llm_service.chat([
                    llm_service.create_messages(
                        system_prompt="Você é um especialista em análise de obras. Responda de forma técnica e útil.",
                        user_message=request.message
                    )[-1]
                ])
        except Exception as llm_error:
            # Em caso de erro com LLM (ex: API key inválida), retorna resposta simulada
            logger.warning(f"Erro ao chamar LLM: {llm_error}. Usando resposta simulada.")

            # Respostas simuladas baseadas em palavras-chave
            message_lower = request.message.lower()

            if any(word in message_lower for word in ['olá', 'oi', 'bom dia', 'boa tarde', 'boa noite']):
                assistant_response = "Olá! Sou o assistente de análise de obras. Como posso ajudá-lo com seu projeto de construção hoje?"
            elif any(word in message_lower for word in ['obra', 'construção', 'projeto']):
                assistant_response = "Para análise completa da obra, preciso de informações como: localização, tipo de construção, fase atual e fotos do progresso. Posso ajudá-lo a documentar todos esses aspectos."
            elif any(word in message_lower for word in ['foto', 'imagem', 'análise']):
                assistant_response = "Você pode enviar fotos da obra para análise. Avaliarei aspectos como progresso, qualidade da execução e conformidade com o projeto."
            elif any(word in message_lower for word in ['relatório', 'documento']):
                assistant_response = "Posso gerar relatórios detalhados com análise de progresso, qualidade e recomendações técnicas para sua obra."
            else:
                assistant_response = f"[Modo Desenvolvimento] Recebi sua mensagem: '{request.message}'. Em produção, esta mensagem seria processada pela IA para fornecer análise técnica especializada sobre construção civil."

        # Conta tokens da resposta
        response_tokens = token_tracker.count_tokens(assistant_response)

        # Rastreia uso de tokens
        token_usage = await token_tracker.track_request(
            session_id=request.session_id,
            model="google/gemini-2.5-flash-lite",
            input_text=request.message,
            output_text=assistant_response,
            metadata={"attachments": len(request.attachments or [])}
        )

        # Adiciona resposta ao histórico (se não foi adicionada pelo agent)
        message_already_saved = agent_result.get("message_saved", False) if construction_agent else False
        if not message_already_saved:
            # Determina qual modelo foi usado (chat ou vision)
            model_used = "x-ai/grok-4-fast"  # Default to chat model
            if request.attachments and len(request.attachments) > 0:
                # Se tem anexos, provavelmente usou o modelo de visão
                model_used = "google/gemini-2.5-flash-image-preview"

            await chat_history.add_message(
                session_id=request.session_id,
                role='assistant',
                content=assistant_response,
                tokens_used=token_usage.total_tokens,
                metadata={"model_used": model_used}
            )
        else:
            logger.info("Message already saved by agent, skipping duplicate save")

        return {
            "response": assistant_response,
            "session_id": request.session_id,
            "message_id": len(session.messages),
            "token_usage": {
                "request_tokens": token_usage.total_tokens,
                "session_total": await token_tracker.get_session_usage(request.session_id)
            },
            "warnings": [
                "Limite de tokens próximo" if token_check['warning'] else None
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/session/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset uma sessão para continuar conversa"""
    try:
        session = await chat_history.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")

        # Limpa mensagens antigas mas mantém a sessão
        session.messages = []
        session.total_tokens = 0
        session.total_cost = 0
        session.last_activity = datetime.now()

        # Adiciona mensagem de boas-vindas
        await chat_history.add_message(
            session_id,
            role='assistant',
            content='Sessão resetada. Como posso ajudar?'
        )

        return {"message": "Sessão resetada com sucesso", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== HISTÓRICO ENDPOINTS =====
@router.get("/chat/sessions")
async def get_sessions(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100)
):
    """Lista sessões de chat"""
    try:
        sessions = await chat_history.list_sessions(
            user_id=user_id,
            status=status,
            limit=limit
        )

        return {
            "sessions": [
                SessionResponse(
                    session_id=s.id,
                    project_name=s.project_name,
                    status=s.status,
                    started_at=s.started_at.isoformat(),
                    last_activity=s.last_activity.isoformat(),
                    message_count=len(s.messages),
                    total_tokens=s.total_tokens,
                    total_cost=s.total_cost
                )
                for s in sessions
            ],
            "total": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/sessions/{session_id}")
async def get_session(session_id: str):
    """Recupera sessão específica"""
    try:
        session = await chat_history.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")

        return {
            "session": {
                "id": session.id,
                "project_name": session.project_name,
                "status": session.status,
                "started_at": session.started_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "metadata": session.metadata,
                "total_tokens": session.total_tokens,
                "total_cost": session.total_cost
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "attachments": msg.attachments,
                    "tokens_used": msg.tokens_used
                }
                for msg in session.messages
            ],
            "token_info": await token_tracker.get_session_usage(session_id),
            "statistics": await chat_history.get_statistics()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: Optional[int] = Query(50, le=200)
):
    """Recupera mensagens de uma sessão"""
    try:
        messages = await chat_history.get_session_messages(session_id, limit=limit)

        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "attachments": msg.attachments,
                    "tokens_used": msg.tokens_used
                }
                for msg in messages
            ],
            "total": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/sessions/{session_id}/status")
async def update_session_status(session_id: str, status: str):
    """Atualiza status da sessão"""
    try:
        await chat_history.update_session_status(session_id, status)
        return {"message": f"Status da sessão {session_id} atualizado para {status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== BUSCA ENDPOINTS =====
@router.get("/chat/search")
async def search_messages(
    query: str = Query(..., min_length=3),
    session_id: Optional[str] = Query(None)
):
    """Busca mensagens por conteúdo"""
    try:
        results = await chat_history.search_sessions(query, session_id)

        return {
            "query": query,
            "results": [
                {
                    "message_id": msg.id,
                    "session_id": msg.session_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "context_match": query.lower() in msg.content.lower()
                }
                for msg in results
            ],
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== TOKENS & ANALYTICS ENDPOINTS =====
@router.get("/analytics/tokens/session/{session_id}")
async def get_session_token_usage(session_id: str):
    """Obtém uso de tokens de uma sessão"""
    try:
        return await token_tracker.get_session_usage(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/tokens/global")
async def get_global_token_statistics():
    """Obtém estatísticas globais de tokens"""
    try:
        # Temporário até implementar agregação no MongoDB
        daily_summary = await token_tracker.get_daily_summary()
        return {
            "total_tokens": daily_summary.get("total_tokens", 0),
            "total_cost": daily_summary.get("total_cost", 0.0),
            "total_requests": daily_summary.get("total_requests", 0),
            "models_usage": daily_summary.get("by_model", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/usage/period")
async def get_usage_by_period(
    days: int = Query(7, ge=1, le=365)
):
    """Obtém uso por período"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Temporário até implementar agregação no MongoDB
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "usage": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== DASHBOARD ENDPOINTS =====
@router.get("/dashboard/overview")
async def get_dashboard_overview():
    """Dashboard principal com dados reais"""
    try:
        # Estatísticas de chat
        try:
            chat_stats = await chat_history.get_statistics()
        except Exception as e:
            logger.error(f"Error getting chat stats: {str(e)}", exc_info=True)
            chat_stats = {
                "total_sessions": 0,
                "active_sessions": 0,
                "total_messages": 0,
                "messages_today": 0
            }

        # Estatísticas de tokens
        try:
            daily_summary = await token_tracker.get_daily_summary()
            token_stats = {
                "total_tokens": daily_summary.get("total_tokens", 0),
                "total_cost": daily_summary.get("total_cost", 0.0),
                "total_requests": daily_summary.get("total_requests", 0),
                "models_usage": daily_summary.get("by_model", {})
            }
        except Exception as e:
            logger.error(f"Error getting token stats: {str(e)}", exc_info=True)
            token_stats = {
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_requests": 0,
                "models_usage": {}
            }

        # Uso por período (última semana) - temporário
        weekly_usage = {
            "period": {
                "start": (datetime.now() - timedelta(days=7)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "usage": []
        }

        # Sessões ativas
        try:
            active_sessions = await chat_history.list_sessions(status='active', limit=10)
        except Exception as e:
            logger.error(f"Error listing active sessions: {str(e)}", exc_info=True)
            active_sessions = []

        # Sessões recentes
        try:
            recent_sessions = await chat_history.list_sessions(limit=5)
        except Exception as e:
            logger.error(f"Error listing recent sessions: {str(e)}", exc_info=True)
            recent_sessions = []

        # Processar sessões recentes com tratamento de erros
        recent_sessions_data = []
        for s in recent_sessions:
            try:
                # ChatSession é um objeto, não um dict
                session_data = {
                    "id": getattr(s, 'id', 'unknown'),
                    "project_name": getattr(s, 'project_name', 'Unknown Project'),
                    "status": getattr(s, 'status', 'unknown'),
                    "last_activity": getattr(s, 'last_activity', datetime.now()).isoformat(),
                    "message_count": len(getattr(s, 'messages', [])),
                    "tokens": getattr(s, 'total_tokens', 0),
                    "cost": round(getattr(s, 'total_cost', 0.0), 4)
                }
                recent_sessions_data.append(session_data)
            except Exception as e:
                logger.warning(f"Erro ao processar sessão: {e}")
                continue

        return {
            "timestamp": datetime.now().isoformat(),
            "chat_statistics": chat_stats,
            "token_statistics": token_stats,
            "weekly_usage": weekly_usage,
            "active_sessions": len(active_sessions) if active_sessions else 0,
            "recent_sessions": recent_sessions_data,
            "alerts": [
                {
                    "type": "info" if token_stats['total_cost'] < 10 else "warning",
                    "message": f"Custo total: ${token_stats['total_cost']:.2f}"
                },
                {
                    "type": "success",
                    "message": f"{token_stats['total_requests']} requisições processadas"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {str(e)}", exc_info=True)
        # Return empty/default data instead of 500
        return {
            "timestamp": datetime.now().isoformat(),
            "chat_statistics": {
                "total_sessions": 0,
                "active_sessions": 0,
                "total_messages": 0,
                "messages_today": 0
            },
            "token_statistics": {
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_requests": 0,
                "models_usage": {}
            },
            "weekly_usage": {
                "period": {
                    "start": (datetime.now() - timedelta(days=7)).isoformat(),
                    "end": datetime.now().isoformat()
                },
                "usage": []
            },
            "active_sessions": 0,
            "recent_sessions": [],
            "alerts": []
        }


@router.get("/dashboard/costs")
async def get_cost_analysis():
    """Análise detalhada de custos"""
    try:
        # Estatísticas de tokens
        daily_summary = await token_tracker.get_daily_summary()
        token_stats = {
            "total_tokens": daily_summary.get("total_tokens", 0),
            "total_cost": daily_summary.get("total_cost", 0.0),
            "total_requests": daily_summary.get("total_requests", 0),
            "models_usage": daily_summary.get("by_model", {})
        }

        # Custos por modelo
        models_cost = {}
        for model, stats in token_stats.get('models_usage', {}).items():
            cost = stats.get('cost', 0.0)
            tokens = stats.get('tokens', 0)
            requests = stats.get('requests', 0)

            models_cost[model] = {
                'total_cost': round(cost, 4),
                'requests': requests,
                'tokens': tokens,
                'avg_cost_per_request': round(cost / max(requests, 1), 4)
            }

        # Projeções
        daily_avg_cost = token_stats['total_cost']
        monthly_projection = daily_avg_cost * 30

        # Métricas de eficiência
        total_tokens = token_stats['total_tokens']
        total_cost = token_stats['total_cost']
        cost_per_token = round(total_cost / total_tokens, 6) if total_tokens else 0.0
        tokens_per_dollar = round(total_tokens / total_cost, 2) if total_cost else 0.0

        return {
            "total_cost": token_stats['total_cost'],
            "models_breakdown": models_cost,
            "projections": {
                "daily_average": round(daily_avg_cost, 4),
                "monthly_projection": round(monthly_projection, 2),
                "yearly_projection": round(monthly_projection * 12, 2)
            },
            "efficiency": {
                "cost_per_token": cost_per_token,
                "tokens_per_dollar": tokens_per_dollar
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== TIMELINE ENDPOINTS =====
@router.get("/timeline/summary")
async def get_timeline_summary(project_id: Optional[str] = None):
    """Retorna resumo da timeline do projeto ou todos os projetos"""
    try:
        summary = await timeline_service.get_timeline_summary(project_id)
        return summary
    except Exception as e:
        logger.error(f"Error getting timeline summary: {str(e)}", exc_info=True)
        # Return empty/default data instead of 500
        return {
            "project": project_id or "all",
            "total_images": 0,
            "total_months": 0,
            "periods": [],
            "progress_timeline": []
        }


@router.get("/timeline/images/{month}")
async def get_images_by_month(month: str, project_id: Optional[str] = None):
    """Retorna imagens de um mês específico"""
    try:
        images = await timeline_service.get_images_by_period(month, project_id)
        return {"month": month, "images": images, "count": len(images)}
    except Exception as e:
        logger.error(f"Error getting images for month {month}: {str(e)}", exc_info=True)
        return {"month": month, "images": [], "count": 0}


@router.get("/timeline/latest")
async def get_latest_timeline_images(limit: int = 10, project_id: Optional[str] = None):
    """Retorna as imagens mais recentes"""
    try:
        images = await timeline_service.get_latest_images(limit, project_id)
        return {"images": images, "count": len(images)}
    except Exception as e:
        logger.error(f"Error getting latest images: {str(e)}", exc_info=True)
        return {"images": [], "count": 0}


@router.get("/timeline/progress")
async def get_construction_progress(project_id: Optional[str] = None):
    """Analisa o progresso da obra ou de todas as obras"""
    try:
        progress = await timeline_service.get_progress_analysis(project_id)
        return progress
    except Exception as e:
        logger.error(f"Error getting construction progress: {str(e)}", exc_info=True)
        # Return empty/default data instead of 500
        return {
            "total_duration_days": 0,
            "total_images": 0,
            "periods_analyzed": 0,
            "monthly_progress": [],
            "activity_frequency": {}
        }


# ===== ADMIN ENDPOINTS =====
@router.post("/admin/archive-old-sessions")
async def archive_old_sessions(days: int = 30):
    """Arquiva sessões antigas"""
    try:
        await chat_history.archive_old_sessions(days)
        return {"message": f"Sessões com mais de {days} dias foram arquivadas"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/export/token-report")
async def export_token_report():
    """Exporta relatório de uso de tokens"""
    try:
        # Temporário até implementar no MongoDB
        daily_summary = await token_tracker.get_daily_summary()
        report = {
            "generated_at": datetime.now().isoformat(),
            "tokens": {
                "total": daily_summary.get("total_tokens", 0),
                "by_model": daily_summary.get("by_model", {})
            },
            "costs": {
                "total": daily_summary.get("total_cost", 0.0),
                "by_model": daily_summary.get("by_model", {})
            }
        }
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== MISSING ENDPOINTS =====
@router.get("/timeout-config")
async def get_timeout_config():
    """Retorna configuração de timeout do sistema"""
    return JSONResponse(content={
        "chat_timeout": 30000,
        "upload_timeout": 60000,
        "analysis_timeout": 120000
    })

@router.get("/api/timeout-config")
async def get_timeout_config_api():
    """Retorna configuração de timeout do sistema (rota API)"""
    return JSONResponse(content={
        "chat_timeout": 30000,
        "upload_timeout": 60000,
        "analysis_timeout": 120000
    })

@router.post("/api/start-upload-session")
async def start_upload_session():
    """Inicia sessão de upload de arquivos"""
    try:
        upload_session_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return JSONResponse(content={
            "upload_session_id": upload_session_id,
            "max_file_size": "50MB",
            "allowed_types": ["image/jpeg", "image/png", "image/webp", "application/pdf"],
            "expires_in": 3600
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== AGENTE LANGGRAPH ENDPOINTS =====
@router.get("/agent/info")
async def get_agent_info():
    """Retorna informações sobre o agente LangGraph"""
    if construction_agent:
        return construction_agent.get_agent_info()
    else:
        return {
            "name": "Construction Analysis Agent",
            "version": "2.0.0",
            "status": "fallback_mode",
            "description": "Agente LangGraph não disponível, usando modo simplificado"
        }

@router.get("/agent/visualize")
async def visualize_agent_graph():
    """Visualiza o grafo de agentes LangGraph"""
    if construction_agent:
        try:
            # Gera visualização Mermaid
            mermaid_graph = construction_agent.visualize_graph()

            # Gera ASCII art
            ascii_graph = construction_agent.get_graph_ascii()

            return {
                "success": True,
                "mermaid": mermaid_graph,
                "ascii": ascii_graph,
                "message": "Visualização gerada. Verifique os arquivos graph_visualization.png e graph_mermaid.md"
            }
        except Exception as e:
            logger.error(f"Erro ao visualizar grafo: {e}")
            return {"error": str(e)}
    else:
        return {"error": "Agente não disponível"}


@router.post("/agent/analyze")
async def analyze_with_agent(
    session_id: str = Query(...),
    message: str = Query(...),
    agent_type: str = Query(default="supervisor")
):
    """Endpoint direto para análise com agente específico"""
    if not construction_agent:
        raise HTTPException(
            status_code=503,
            detail="Agente LangGraph não disponível"
        )

    try:
        result = await construction_agent.process_message(
            session_id=session_id,
            message=message,
            attachments=[]
        )

        return result

    except Exception as e:
        logger.error(f"Erro na análise do agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))
