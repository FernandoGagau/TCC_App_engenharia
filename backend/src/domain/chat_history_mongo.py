"""
Sistema de Histórico de Chat com MongoDB
Substitui armazenamento JSON por persistência em MongoDB
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
import logging
from dataclasses import dataclass
import yaml
from pathlib import Path

# MongoDB imports
from beanie import Document
from motor.motor_asyncio import AsyncIOMotorClient
from infrastructure.database.models import (
    SessionModel,
    MessageModel,
    SessionStatus,
    MessageRole,
    AttachmentModel
)
from infrastructure.database.mongodb import MongoDB
from infrastructure.config.model_pricing import calculate_cost

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Representa uma mensagem no chat"""
    id: str
    session_id: str
    role: str  # 'user' ou 'assistant'
    content: str
    timestamp: datetime
    attachments: List[Dict] = None
    metadata: Dict[str, Any] = None
    tokens_used: int = 0

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'attachments': self.attachments or [],
            'metadata': self.metadata or {},
            'tokens_used': self.tokens_used
        }

    @classmethod
    def from_mongo_model(cls, msg_model: MessageModel) -> 'ChatMessage':
        """Converte modelo MongoDB para ChatMessage"""
        return cls(
            id=str(msg_model.id),
            session_id=msg_model.session_id,
            role=msg_model.role,
            content=msg_model.content,
            timestamp=msg_model.timestamp,
            attachments=[att.dict() for att in msg_model.attachments] if msg_model.attachments else [],
            metadata=msg_model.metadata or {},
            tokens_used=msg_model.tokens_used or 0
        )


@dataclass
class ChatSession:
    """Representa uma sessão de chat"""
    id: str
    user_id: Optional[str]
    project_name: str
    started_at: datetime
    last_activity: datetime
    status: str  # 'active', 'completed', 'archived'
    messages: List[ChatMessage]
    metadata: Dict[str, Any]
    total_tokens: int = 0
    total_cost: float = 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'project_name': self.project_name,
            'started_at': self.started_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'status': self.status,
            'messages': [msg.to_dict() for msg in self.messages],
            'metadata': self.metadata,
            'total_tokens': self.total_tokens,
            'total_cost': self.total_cost
        }

    @classmethod
    async def from_mongo_model(cls, session_model: SessionModel, message_limit: int = 60) -> 'ChatSession':
        """Converte modelo MongoDB para ChatSession

        Args:
            session_model: Modelo da sessão do MongoDB
            message_limit: Número máximo de mensagens recentes a carregar (padrão: 60)
        """
        # Busca as últimas N mensagens da sessão (mais recentes primeiro, depois invertemos)
        messages = await MessageModel.find(
            MessageModel.session_id == session_model.session_id
        ).sort("-timestamp").limit(message_limit).to_list()

        # Inverte para ordem cronológica (mais antiga primeiro)
        messages.reverse()

        chat_messages = [ChatMessage.from_mongo_model(msg) for msg in messages]

        return cls(
            id=session_model.session_id,
            user_id=session_model.user_id,
            project_name=session_model.title or session_model.project_id or "Sem título",
            started_at=session_model.created_at,
            last_activity=session_model.updated_at or session_model.created_at,
            status=session_model.status.value,
            messages=chat_messages,
            metadata=session_model.metadata or {},
            total_tokens=session_model.total_tokens,
            total_cost=session_model.total_cost
        )


class ChatHistoryManagerMongo:
    """Gerenciador de histórico de chat com MongoDB"""

    def __init__(self):
        """Inicializa o gerenciador"""
        self.prompts_config = self._load_prompts_config()
        self._ensure_db_connected = False

    def _load_prompts_config(self) -> Dict:
        """Carrega configuração de prompts do YAML"""
        try:
            prompts_file = Path("backend/config/prompts.yaml")
            if prompts_file.exists():
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            return {}
        except Exception as e:
            logger.error(f"Erro ao carregar prompts: {e}")
            return {}

    async def ensure_connected(self):
        """Garante que está conectado ao MongoDB"""
        if not self._ensure_db_connected:
            if MongoDB.client is None:
                await MongoDB.connect_db()
            self._ensure_db_connected = True

    async def create_session(self, project_name: str, user_id: Optional[str] = None, add_greeting: bool = True) -> ChatSession:
        """Cria uma nova sessão de chat no MongoDB"""
        logger.info(f"🆕 Creating new session - project: {project_name}, user: {user_id}")
        await self.ensure_connected()

        session_id = str(uuid4())
        logger.info(f"📝 Generated session_id: {session_id}")

        # Cria sessão no MongoDB
        session_model = SessionModel(
            session_id=session_id,
            user_id=user_id or "anonymous",
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            title=project_name,
            metadata={
                'prompts_version': self.prompts_config.get('system', {}).get('version', '2.0.0')
            },
            total_tokens=0,
            total_cost=0.0
        )

        logger.info(f"💾 Attempting to save session to MongoDB...")
        try:
            await session_model.save()
            logger.info(f"✅ Session saved successfully: {session_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save session to MongoDB: {e}")
            raise

        # Adiciona mensagem de boas-vindas apenas se solicitado
        if add_greeting:
            welcome_msg = self.prompts_config.get('templates', {}).get('welcome',
                'Sessão iniciada! Como posso ajudá-lo com a análise da obra?')

            await self.add_message(
                session_id,
                role='assistant',
                content=welcome_msg
            )
            logger.info(f"Sessão criada com mensagem de boas-vindas: {session_id}")
        else:
            logger.info(f"Sessão criada sem mensagem de boas-vindas: {session_id}")

        # Retorna sessão como objeto ChatSession
        return await ChatSession.from_mongo_model(session_model)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        attachments: List[Dict] = None,
        metadata: Dict[str, Any] = None,
        tokens_used: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> ChatMessage:
        """Adiciona uma mensagem à sessão no MongoDB"""
        await self.ensure_connected()

        # Converte role para enum
        role_enum = MessageRole.USER if role == 'user' else MessageRole.ASSISTANT

        # Cria attachments models se houver
        attachment_models = []
        if attachments:
            for att in attachments:
                attachment_models.append(AttachmentModel(
                    filename=att.get('filename', 'unknown'),
                    content_type=att.get('content_type', 'application/octet-stream'),
                    size=att.get('size', 0),
                    url=att.get('url', '')
                ))

        # Se input/output tokens não foram fornecidos, usa tokens_used como fallback
        if input_tokens == 0 and output_tokens == 0 and tokens_used > 0:
            # Estimativa: assume 40% input, 60% output
            input_tokens = int(tokens_used * 0.4)
            output_tokens = int(tokens_used * 0.6)

        # Cria mensagem no MongoDB
        message_model = MessageModel(
            session_id=session_id,
            role=role_enum,
            content=content,
            timestamp=datetime.utcnow(),
            attachments=attachment_models,
            metadata=metadata or {},
            tokens_used=tokens_used or (input_tokens + output_tokens),
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        await message_model.save()
        logger.info(f"✅ MESSAGE SAVED TO MONGODB - Session: {session_id}, Role: {role}, Content: {content[:50]}...")

        # Atualiza última atividade da sessão
        session = await SessionModel.find_one(SessionModel.session_id == session_id)
        if session:
            session.updated_at = datetime.utcnow()

            # Atualiza total de tokens e custo diretamente nos campos do modelo
            session.total_tokens += (input_tokens + output_tokens)

            # Calcula custo usando preços reais do OpenRouter
            model_used = metadata.get('model_used', 'grok-4-fast') if metadata else 'grok-4-fast'
            message_cost = calculate_cost(input_tokens, output_tokens, model_used)
            session.total_cost += message_cost

            logger.debug(f"💰 Custo calculado ({model_used}): {input_tokens} input + {output_tokens} output = US$ {message_cost:.6f}")

            await session.save()

        logger.debug(f"Mensagem adicionada ao MongoDB - Sessão: {session_id}, Role: {role}")

        return ChatMessage.from_mongo_model(message_model)

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Recupera uma sessão do MongoDB"""
        await self.ensure_connected()

        session_model = await SessionModel.find_one(SessionModel.session_id == session_id)

        if not session_model:
            logger.warning(f"Sessão não encontrada no MongoDB: {session_id}")
            return None

        session = await ChatSession.from_mongo_model(session_model)
        logger.info(f"📥 GET_SESSION loaded: {session_id} with {len(session.messages)} messages")
        for i, msg in enumerate(session.messages):
            logger.info(f"   [{i}] {msg.role}: {msg.content[:50]}...")
        return session

    async def get_session_messages(self, session_id: str, limit: int = 100) -> List[ChatMessage]:
        """Recupera mensagens de uma sessão do MongoDB"""
        await self.ensure_connected()

        messages = await MessageModel.find(
            MessageModel.session_id == session_id
        ).sort("-timestamp").limit(limit).to_list()

        # Reverte a ordem para cronológica
        messages.reverse()

        return [ChatMessage.from_mongo_model(msg) for msg in messages]

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[ChatSession]:
        """Lista sessões do MongoDB"""
        await self.ensure_connected()

        query = {}

        if user_id:
            query["user_id"] = user_id

        if status:
            query["status"] = SessionStatus(status)

        sessions = await SessionModel.find(query).sort("-created_at").limit(limit).to_list()

        # Retorna lista vazia se não houver sessões
        if not sessions:
            return []

        # Converte cada sessão para ChatSession
        result = []
        for session in sessions:
            try:
                chat_session = await ChatSession.from_mongo_model(session)
                result.append(chat_session)
            except Exception as e:
                logger.error(f"Erro ao converter sessão {session.session_id}: {e}")
                continue

        return result

    async def update_session_metadata(self, session_id: str, metadata: Dict[str, Any]):
        """Atualiza metadata de uma sessão no MongoDB"""
        await self.ensure_connected()

        session = await SessionModel.find_one(SessionModel.session_id == session_id)
        if session:
            if not session.metadata:
                session.metadata = {}
            session.metadata.update(metadata)
            session.updated_at = datetime.utcnow()
            await session.save()
            logger.info(f"✅ Metadata da sessão salvo no MongoDB: {session_id} -> {metadata}")
        else:
            logger.warning(f"Sessão não encontrada para atualizar metadata: {session_id}")

    async def update_session_status(self, session_id: str, status: str):
        """Atualiza status de uma sessão no MongoDB"""
        await self.ensure_connected()

        session = await SessionModel.find_one(SessionModel.session_id == session_id)
        if session:
            session.status = SessionStatus(status)
            session.updated_at = datetime.utcnow()
            await session.save()
            logger.info(f"Status da sessão atualizado no MongoDB: {session_id} -> {status}")
        else:
            logger.warning(f"Sessão não encontrada para atualização: {session_id}")

    async def search_sessions(
        self,
        query: str,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[ChatSession]:
        """Busca sessões no MongoDB"""
        await self.ensure_connected()

        # Busca em mensagens que contenham o texto
        message_sessions = await MessageModel.find(
            {"content": {"$regex": query, "$options": "i"}}
        ).distinct("session_id")

        # Constrói query para sessões
        session_query = {"session_id": {"$in": message_sessions}}

        if user_id:
            session_query["user_id"] = user_id

        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            session_query["created_at"] = date_query

        sessions = await SessionModel.find(session_query).sort("-created_at").to_list()

        return [await ChatSession.from_mongo_model(session) for session in sessions]

    async def archive_old_sessions(self, days: int = 30) -> int:
        """Arquiva sessões antigas no MongoDB"""
        await self.ensure_connected()

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Atualiza sessões antigas para status archived
        result = await SessionModel.find(
            SessionModel.created_at < cutoff_date,
            SessionModel.status == SessionStatus.ACTIVE
        ).update({"$set": {"status": SessionStatus.COMPLETED}})

        count = result.modified_count if result else 0
        logger.info(f"Arquivadas {count} sessões antigas no MongoDB")

        return count

    async def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do MongoDB incluindo tokens e custos"""
        await self.ensure_connected()

        # Total de sessões
        total_sessions = await SessionModel.count()

        # Sessões ativas
        active_sessions = await SessionModel.find(
            SessionModel.status == SessionStatus.ACTIVE
        ).count()

        # Total de mensagens
        total_messages = await MessageModel.count()

        # Mensagens hoje
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        messages_today = await MessageModel.find(
            MessageModel.timestamp >= today
        ).count()

        # Calcular total de tokens de todas as mensagens
        all_messages = await MessageModel.find_all().to_list()
        total_tokens = sum(msg.tokens_used or 0 for msg in all_messages)

        # Calcular total de custo de todas as sessões
        all_sessions = await SessionModel.find_all().to_list()
        total_cost = sum(session.total_cost for session in all_sessions)

        # Tokens hoje
        messages_today_list = await MessageModel.find(
            MessageModel.timestamp >= today
        ).to_list()
        tokens_today = sum(msg.tokens_used or 0 for msg in messages_today_list)

        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_messages': total_messages,
            'messages_today': messages_today,
            'total_tokens': total_tokens,
            'total_cost': round(total_cost, 4),
            'tokens_today': tokens_today,
            'storage': 'MongoDB',
            'database': MongoDB.database.name if MongoDB.database is not None else 'Not connected'
        }
