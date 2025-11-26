"""
Chat Service
Conversational AI service for project documentation
Following the MVP PRD specifications
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path
import base64

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationSummaryBufferMemory
from pydantic import BaseModel, Field

from agents.supervisor import SupervisorAgent
from infrastructure.agents.agent_factory import AgentFactory
from infrastructure.llm_service import get_llm_service
from application.services.project_service import ProjectService
from domain.entities.project import Project
from domain.entities.location import Location
from domain.value_objects.project_info import ProjectInfo
from domain.value_objects.progress import Progress
from domain.value_objects.phase import Phase
from domain.chat_history_mongo import ChatHistoryManagerMongo
from domain.chat.models import MessageRole

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ChatSession(BaseModel):
    """Chat session model"""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    state: str = Field(default="initial")  # initial, interviewing, analyzing, completed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewState:
    """Manages interview state for project documentation"""
    
    QUESTIONS = [
        "Olá! Sou seu agente de documentação de obras. Vamos começar! Qual é o nome ou identificação desta obra?",
        "Perfeito! Que tipo de construção estamos acompanhando? (residencial, comercial, industrial, reforma, etc.)",
        "Entendi! Qual é o endereço ou localização da obra?",
        "Quem é o responsável técnico pela obra? (engenheiro, arquiteto, mestre de obras)",
        "Qual a data de início prevista ou já iniciada?",
        "Qual a previsão de conclusão da obra?",
        "Agora preciso de fotos dos 3 locais principais. Pode enviar uma foto da ÁREA EXTERNA/FACHADA?",
        "Perfeito! Agora uma foto da ÁREA INTERNA PRINCIPAL (sala, ambiente principal)?",
        "Ótimo! Por último, uma foto da ÁREA TÉCNICA (cozinha, banheiro ou área de instalações)?",
        "Excelente! Analisei tudo e criei a documentação inicial da obra."
    ]
    
    def __init__(self):
        self.current_question = 0
        self.answers = {}
        self.photos = {}
        self.is_complete = False
    
    def get_next_question(self) -> str:
        """Get next interview question"""
        if self.current_question < len(self.QUESTIONS):
            return self.QUESTIONS[self.current_question]
        return None
    
    def process_answer(self, answer: str, question_index: int):
        """Process user answer"""
        field_mapping = {
            0: "project_name",
            1: "project_type",
            2: "address",
            3: "responsible_engineer",
            4: "start_date",
            5: "expected_completion"
        }
        
        if question_index in field_mapping:
            self.answers[field_mapping[question_index]] = answer
    
    def add_photo(self, photo_data: str, location_index: int):
        """Add photo for location"""
        location_mapping = {
            6: "location_1",  # Externa
            7: "location_2",  # Interna
            8: "location_3"   # Técnica
        }
        
        if location_index in location_mapping:
            self.photos[location_mapping[location_index]] = photo_data
    
    def advance(self):
        """Advance to next question"""
        self.current_question += 1
        if self.current_question >= len(self.QUESTIONS):
            self.is_complete = True


class ChatService:
    """
    Main chat service for conversational project documentation
    Implements the MVP conversational agent from PRD
    """
    
    def __init__(
        self,
        agent_factory: AgentFactory,
        project_service: ProjectService,
        settings: Any
    ):
        self.agent_factory = agent_factory
        self.project_service = project_service
        self.settings = settings
        self.history_manager = ChatHistoryManagerMongo()
        self.interview_states: Dict[str, InterviewState] = {}

        # Initialize LLM for chat
        self.llm_service = get_llm_service()
        self.llm = self.llm_service.get_llm(model_type="chat")

        # Initialize SupervisorAgent for real agent orchestration
        supervisor_config = {
            'llm': self.llm,
            'model': settings.chat_model,
            'temperature': 0.3,
            'project_repository': self.project_service,
            'storage_service': agent_factory.storage_service if agent_factory else None,
            'chat_history_manager': self.history_manager  # Pass chat history manager to supervisor
        }
        self.supervisor_agent = SupervisorAgent(supervisor_config)
    
    async def create_session(self, add_greeting: bool = False) -> ChatSession:
        """Create new chat session with optional greeting"""
        # Create session using MongoDB manager (pass add_greeting parameter)
        session = await self.history_manager.create_session(
            project_name="Nova Sessão",
            user_id="anonymous",
            add_greeting=add_greeting
        )

        # Initialize interview state for the session
        self.interview_states[session.id] = InterviewState()

        # Only add greeting if explicitly requested (for backward compatibility)
        if add_greeting:
            greeting = ChatMessage(
                role="assistant",
                content=self.interview_states[session.id].get_next_question()
            )
            session.messages.append(greeting)
            session.state = "interviewing"
        else:
            session.state = "waiting"

        logger.info(f"Created chat session: {session.id} (greeting: {add_greeting})")
        return session

    async def _initialize_session_on_first_message(self, session: ChatSession):
        """Initialize session state when first user message is received (without adding greeting)"""
        if session.status == "active" and len(session.messages) == 0:
            # Just update state to interviewing - let agent process the message and respond
            # Note: MongoDB ChatSession uses 'status' not 'state'
            pass  # Status will remain 'active' in MongoDB
            logger.info(f"Session {session.id} state changed to interviewing on first message")
    
    async def process_message(
        self,
        session_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Process user message through SupervisorAgent workflow"""
        try:
            # DEBUG: Log incoming attachments
            logger.info(f"🔍 process_message called with:")
            logger.info(f"  - session_id: {session_id}")
            logger.info(f"  - message: {message[:100]}...")
            logger.info(f"  - attachments: {attachments is not None}, count: {len(attachments) if attachments else 0}")
            if attachments:
                for i, att in enumerate(attachments):
                    att_keys = list(att.keys()) if isinstance(att, dict) else "NOT_DICT"
                    logger.info(f"    [{i}] keys={att_keys}")

            # Get session from MongoDB (message already added by API route)
            session = await self.history_manager.get_session(session_id)
            if not session:
                return {"error": "Session not found"}

            # Initialize session state on first message
            await self._initialize_session_on_first_message(session)

            # Convert previous messages to OpenRouter format for conversation history
            # Note: API already added the current user message to session before calling this
            conversation_history = []
            for msg in session.messages[:-1]:  # Exclude the current user message (last one)
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })

            logger.info(f"Session has {len(session.messages)} total messages")
            logger.info(f"Sending {len(conversation_history)} previous messages as conversation history")
            logger.info(f"📝 CONVERSATION HISTORY BEING SENT TO SUPERVISOR:")
            for i, msg in enumerate(conversation_history):
                logger.info(f"  [{i}] {msg['role']}: {msg['content'][:100]}...")
            logger.info(f"📝 CURRENT USER MESSAGE: {message[:100]}...")

            # Use SupervisorAgent to process the request through LangGraph workflow
            # Get project_id from metadata if available
            logger.info(f"🔍 Session metadata: {session.metadata}")
            project_id_str = session.metadata.get("project_id") if session.metadata else None
            project_id = UUID(project_id_str) if project_id_str else None

            if project_id:
                logger.info(f"🎯 Using project_id from session: {project_id}")
            else:
                logger.info("⚠️ No project_id in session metadata - checking for existing projects")

                # Debug: Show all messages
                logger.info(f"🔍 Total messages in session: {len(session.messages)}")
                for i, msg in enumerate(session.messages):
                    logger.info(f"  [{i}] role={msg.role}, content={msg.content[:80] if msg.content else 'None'}...")

                # SPECIAL CASE: If user sent attachments (photos) and has only 1 project, auto-select it
                has_attachments = attachments and len(attachments) > 0
                if has_attachments:
                    logger.info(f"📎 User sent {len(attachments)} attachments - checking if we can auto-select project")
                    try:
                        existing_projects = await self.project_service.list_projects(limit=10)
                        if len(existing_projects) == 1:
                            # Auto-select the only project
                            matched_project = existing_projects[0]
                            logger.info(f"✅ Auto-selected only project: {matched_project.info.project_name}")

                            # Update session metadata
                            if not session.metadata:
                                session.metadata = {}
                            session.metadata["project_id"] = str(matched_project.id)
                            await self.history_manager.update_session_metadata(session.id, session.metadata)
                            project_id = matched_project.id
                            logger.info(f"✅ Project auto-selected, continuing with analysis")
                        elif len(existing_projects) > 1:
                            logger.info(f"⚠️ Multiple projects found, need user to select")
                            # Will ask below
                        else:
                            logger.info(f"⚠️ No projects found, will need to create one")
                    except Exception as e:
                        logger.error(f"Error auto-selecting project: {e}", exc_info=True)

                # Try to detect if user is mentioning a project name
                # Even if not immediately after project list message
                message_lower = message.lower()

                # Check if we're currently in onboarding flow
                # If last assistant message contains onboarding questions, DON'T try to match projects
                is_in_onboarding = False
                if session.messages:
                    # Check last few assistant messages for onboarding keywords
                    for msg in reversed(session.messages[-3:]):  # Check last 3 messages
                        if msg.role == MessageRole.ASSISTANT and msg.content:
                            content_lower = msg.content.lower()
                            onboarding_keywords = [
                                "qual o nome da obra",
                                "qual o tipo",
                                "qual o endereço",
                                "vamos cadastrar",
                                "cadastrar a primeira",
                                "nome do projeto",
                                "tipo da obra"
                            ]
                            if any(keyword in content_lower for keyword in onboarding_keywords):
                                is_in_onboarding = True
                                logger.info(f"🔍 Detected onboarding in progress - will NOT try project matching")
                                break

                # Check if user mentions keywords related to projects
                project_keywords = ["obra", "projeto", "project", "construção"]
                mentions_project = any(keyword in message_lower for keyword in project_keywords)

                logger.info(f"🔍 Checking if user mentions a project: mentions_project={mentions_project}, is_in_onboarding={is_in_onboarding}")

                # Check for keywords indicating new project FIRST (before matching existing)
                wants_new_project = False
                if any(keyword in message_lower for keyword in ["nova", "novo", "cadastrar", "criar", "2", "nova obra", "novo projeto"]):
                    wants_new_project = True
                    logger.info("🆕 User wants to create a NEW project - forcing onboarding flow")
                    # Clear project_id to force onboarding
                    project_id = None
                    # Update session metadata to indicate new project request
                    if not session.metadata:
                        session.metadata = {}
                    session.metadata["wants_new_project"] = True
                    await self.history_manager.update_session_metadata(session.id, session.metadata)

                # If user mentions a project AND we're NOT in onboarding AND doesn't want new project, try to match existing projects
                if mentions_project and not is_in_onboarding and not wants_new_project:
                    logger.info("✅ User mentioned a project keyword (not in onboarding)")
                    logger.info(f"🔍 User message: {message}")

                    # Try to match project name
                    try:
                        existing_projects = await self.project_service.list_projects(limit=10)
                        logger.info(f"🔍 Matching user input '{message_lower}' against {len(existing_projects)} projects")
                        matched_project = None

                        for proj in existing_projects:
                            project_name_lower = proj.info.project_name.lower()
                            logger.info(f"  Checking: '{project_name_lower}' vs '{message_lower}'")
                            # Fuzzy match: check if user message contains project name
                            if project_name_lower in message_lower or message_lower in project_name_lower:
                                matched_project = proj
                                logger.info(f"  ✅ MATCH!")
                                break

                        if matched_project:
                            logger.info(f"✅ Matched project: {matched_project.info.project_name} (ID: {matched_project.id})")

                            # Update session metadata with project_id
                            if not session.metadata:
                                session.metadata = {}
                            session.metadata["project_id"] = str(matched_project.id)
                            logger.info(f"💾 Saving project_id to session metadata: {session.metadata}")

                            await self.history_manager.update_session_metadata(
                                session.id,
                                session.metadata
                            )
                            logger.info(f"✅ Session metadata updated in MongoDB")

                            # Update project_id for this request
                            project_id = matched_project.id
                            logger.info(f"✅ Set project_id for current request: {project_id}")

                            response_content = f"""Perfeito! Agora estamos trabalhando na obra **{matched_project.info.project_name}**.

Como posso ajudar você hoje com essa obra?
- Ver o progresso atual
- Analisar imagens
- Gerar relatórios
- Ou algo mais específico?"""

                            await self.history_manager.add_message(
                                session_id=session.id,
                                role="assistant",
                                content=response_content,
                                metadata={"project_id": str(matched_project.id)}
                            )

                            return {
                                "success": True,
                                "session_id": session.id,
                                "response": response_content,
                                "state": session.status,
                                "data": {"project": {"id": str(matched_project.id), "name": matched_project.info.project_name}},
                                "next_action": "ready",
                                "message_saved": True  # Indica que mensagem já foi salva no MongoDB
                            }
                        else:
                            logger.warning(f"⚠️ Could not match project from user input: {message}")
                            # Ask for clarification - list projects again
                            existing_projects = await self.project_service.list_projects(limit=10)
                            project_list = []
                            for proj in existing_projects:
                                project_list.append(
                                    f"• **{proj.info.project_name}** - {proj.info.project_type}"
                                )
                            projects_text = "\n".join(project_list)

                            response_content = f"""Não consegui identificar qual obra você quer acessar. Suas obras cadastradas são:

{projects_text}

Por favor, me diga o nome exato da obra que deseja acessar, ou diga "nova obra" para cadastrar uma nova."""

                            await self.history_manager.add_message(
                                session_id=session.id,
                                role="assistant",
                                content=response_content
                            )

                            return {
                                "success": True,
                                "session_id": session.id,
                                "response": response_content,
                                "state": session.status,
                                "data": {"projects": [{"id": str(p.id), "name": p.info.project_name} for p in existing_projects]},
                                "next_action": "select_project",
                                "message_saved": True  # Indica que mensagem já foi salva no MongoDB
                            }
                    except Exception as e:
                        logger.error(f"Error matching project: {e}", exc_info=True)
                        # Continue with normal flow

                # Check if user has any existing projects (only if not already shown AND not auto-selected above)
                # Skip this check if we already have project_id from auto-selection or if user sent attachments with multiple projects
                if not project_id:
                    # Check if we already asked about projects by looking at recent assistant messages
                    already_asked_about_projects = False
                    if len(session.messages) >= 2:
                        for msg in session.messages[-3:]:  # Check last 3 messages
                            if msg.role == "assistant" and "obra(s) cadastrada(s)" in msg.content:
                                already_asked_about_projects = True
                                break

                    try:
                        existing_projects = await self.project_service.list_projects(limit=10)

                        # Only ask about projects if:
                        # 1. Has projects
                        # 2. Not already asked
                        # 3. User didn't send attachments (photos should trigger project selection differently)
                        if existing_projects and not already_asked_about_projects and not has_attachments:
                            logger.info(f"✅ Found {len(existing_projects)} existing projects for user")

                            # Format project list for response
                            project_list = []
                            for proj in existing_projects:
                                project_list.append(
                                    f"• **{proj.info.project_name}** - {proj.info.project_type} em {proj.info.address}"
                                )

                            projects_text = "\n".join(project_list)

                            response_content = f"""Olá! Vi que você já tem {len(existing_projects)} obra(s) cadastrada(s):

{projects_text}

Você gostaria de:
1. **Continuar** trabalhando em uma dessas obras (me diga o nome)
2. **Cadastrar uma nova obra**

Como posso ajudar?"""

                            # Add assistant response to MongoDB
                            await self.history_manager.add_message(
                                session_id=session.id,
                                role="assistant",
                                content=response_content,
                                metadata={"existing_projects": len(existing_projects)}
                            )

                            return {
                                "success": True,
                                "session_id": session.id,
                                "response": response_content,
                                "state": session.status,
                                "data": {"projects": [{"id": str(p.id), "name": p.info.project_name} for p in existing_projects]},
                                "next_action": "select_project",
                                "message_saved": True  # Indica que mensagem já foi salva no MongoDB
                            }
                        elif not existing_projects:
                            logger.info("ℹ️ No existing projects found - will proceed with onboarding")
                        elif has_attachments:
                            logger.info("ℹ️ User sent attachments but has multiple projects - will handle via supervisor")
                        else:
                            logger.info("ℹ️ Already asked about projects - continuing with normal flow")

                    except Exception as e:
                        logger.error(f"Error checking existing projects: {e}", exc_info=True)
                        # Continue with normal flow if check fails

            # Debug: Check attachments before calling supervisor
            logger.info(f"🔍 About to call supervisor with:")
            logger.info(f"  - project_id: {project_id}")
            logger.info(f"  - attachments count: {len(attachments) if attachments else 0}")
            if attachments:
                for i, att in enumerate(attachments):
                    logger.info(f"    [{i}] type={att.get('type')}, has_data={bool(att.get('data'))}, filename={att.get('filename', 'N/A')}")

            result = await self.supervisor_agent.process_request(
                user_input=message,
                project_id=project_id,
                attachments=attachments,
                conversation_history=conversation_history if conversation_history else None,
                session_id=session_id  # Pass session_id so supervisor can fetch history from MongoDB
            )

            logger.info(f"SupervisorAgent result keys: {list(result.keys())}")
            logger.info(f"SupervisorAgent success: {result.get('success')}")
            logger.info(f"SupervisorAgent messages count: {len(result.get('messages', []))}")
            logger.info(f"SupervisorAgent errors: {result.get('errors', [])}")

            # Debug: Log message types and content
            for i, msg in enumerate(result.get('messages', [])):
                logger.info(f"Message {i}: type={type(msg)}, content preview: {str(msg)[:100]}")

            # Extract response from supervisor result
            # Check if we have valid messages even if success=False (may have warnings/errors but still valid response)
            messages = result.get("messages", [])
            assistant_messages = [msg for msg in messages if hasattr(msg, 'content') or msg.get("role") == "assistant"]

            if assistant_messages:
                # Get the final assistant message from the workflow
                last_message = assistant_messages[-1]
                if hasattr(last_message, 'content'):
                    response_content = last_message.content
                else:
                    response_content = last_message.get("content", "Analysis completed.")

                # Update session state based on results
                await self._update_session_from_results(session, result)

                response_data = {
                    "message": response_content,
                    "data": result.get("results"),
                    "next_action": self._determine_next_action(result, session),
                    "metadata": result.get("metadata"),
                    "errors": result.get("errors", [])
                }
            elif result.get("success"):
                # Fallback to synthesis summary when no assistant messages but success=True
                synthesis = result.get("results", {}).get("synthesis", {})
                response_content = synthesis.get("summary", "Request processed successfully.")

                await self._update_session_from_results(session, result)

                response_data = {
                    "message": response_content,
                    "data": result.get("results"),
                    "next_action": self._determine_next_action(result, session),
                    "metadata": result.get("metadata")
                }
            else:
                # Handle true error case (no valid messages and success=False)
                error_message = result.get("error", "Sorry, I encountered an error processing your request.")
                response_data = {
                    "message": error_message,
                    "next_action": "retry",
                    "errors": result.get("errors", [])
                }

            # Add assistant response to MongoDB
            await self.history_manager.add_message(
                session_id=session.id,
                role="assistant",
                content=response_data["message"],
                metadata=response_data.get("metadata")
            )

            return {
                "session_id": session.id,
                "response": response_data["message"],
                "state": session.status,
                "data": response_data.get("data"),
                "next_action": response_data.get("next_action")
            }

        except Exception as e:
            logger.error(f"Error processing message through SupervisorAgent: {str(e)}")
            return {"error": str(e)}

    async def _update_session_from_results(self, session, result: Dict[str, Any]):
        """Update session state based on SupervisorAgent results"""
        try:
            results = result.get("results", {})

            # Check if project was created/updated during onboarding
            if result.get("project_id"):
                # Update project ID in session metadata - create if doesn't exist
                if not hasattr(session, 'metadata') or session.metadata is None:
                    session.metadata = {}
                session.metadata["project_id"] = str(result["project_id"])
                logger.info(f"Session {session.id} updated with new project_id: {result['project_id']}")

                # Save metadata to MongoDB
                await self.history_manager.update_session_metadata(
                    session.id,
                    {"project_id": str(result["project_id"])}
                )

            # Check if project was created/updated in progress results
            elif "progress" in results and results["progress"].get("project_id"):
                # Update project ID in session metadata - create if doesn't exist
                if not hasattr(session, 'metadata') or session.metadata is None:
                    session.metadata = {}
                session.metadata["project_id"] = str(results["progress"]["project_id"])
                # Can update session status to completed if needed
                await self.history_manager.update_session_status(session.id, "completed")

            # Store results in session metadata for future reference
            if not hasattr(session, 'metadata') or session.metadata is None:
                session.metadata = {}
            session.metadata.update({
                "last_analysis": results,
                "last_update": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error updating session from results: {str(e)}")

    def _determine_next_action(self, result: Dict[str, Any], session: ChatSession) -> str:
        """Determine next action based on SupervisorAgent results"""
        try:
            synthesis = result.get("results", {}).get("synthesis", {})
            next_steps = synthesis.get("next_steps", [])

            # Check for specific recommendations
            if any("photo" in step.lower() for step in next_steps):
                return "upload_photo"
            elif any("document" in step.lower() for step in next_steps):
                return "upload_document"
            elif session.status == "completed":
                return "continue_monitoring"
            elif session.status == "active":
                return "text_input"
            else:
                return "continue"

        except Exception as e:
            logger.error(f"Error determining next action: {str(e)}")
            return "continue"

    async def _handle_interview(
        self,
        session: ChatSession,
        interview_state: InterviewState,
        message: str,
        attachments: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Handle interview phase - DEPRECATED: Now handled by SupervisorAgent"""
        # This method is deprecated and replaced by SupervisorAgent workflow
        # Keep for backward compatibility but redirect to SupervisorAgent
        logger.warning("_handle_interview called but deprecated - use SupervisorAgent workflow")

        return {
            "message": "Processing through agent workflow...",
            "next_action": "continue"
        }
    
    async def _handle_analysis(
        self,
        session: ChatSession,
        message: str,
        attachments: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Handle analysis phase - DEPRECATED: Now handled by SupervisorAgent"""
        # This method is deprecated and replaced by SupervisorAgent workflow
        logger.warning("_handle_analysis called but deprecated - use SupervisorAgent workflow")

        return {
            "message": "Processing through agent workflow...",
            "next_action": "continue"
        }
    
    async def _handle_followup(
        self,
        session: ChatSession,
        message: str,
        attachments: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Handle follow-up questions - DEPRECATED: Now handled by SupervisorAgent"""
        # This method is deprecated and replaced by SupervisorAgent workflow
        logger.warning("_handle_followup called but deprecated - use SupervisorAgent workflow")

        return {
            "message": "Processing through agent workflow...",
            "next_action": "continue"
        }
    
    async def _handle_general(
        self,
        session: ChatSession,
        message: str
    ) -> Dict[str, Any]:
        """Handle general conversation - DEPRECATED: Now handled by SupervisorAgent"""
        # This method is deprecated and replaced by SupervisorAgent workflow
        logger.warning("_handle_general called but deprecated - use SupervisorAgent workflow")

        return {
            "message": "Processing through agent workflow...",
            "next_action": "continue"
        }
    
    async def _analyze_photo(
        self,
        photo_data: str,
        location_index: int
    ) -> Dict[str, Any]:
        """Analyze photo using visual agent"""
        try:
            visual_agent = self.agent_factory.get_agent("visual")
            
            # Create context
            from agents.interfaces.agent_interface import AgentContext
            context = AgentContext(
                project_id=uuid4(),
                session_id="photo_analysis",
                metadata={"location_index": location_index}
            )
            
            # Analyze image
            result = await visual_agent.analyze_image(photo_data, context)
            
            if result.success:
                return result.data
            else:
                return {
                    "phase": "unknown",
                    "progress": 0,
                    "elements": [],
                    "error": "Analysis failed"
                }
                
        except Exception as e:
            logger.error(f"Photo analysis error: {str(e)}")
            return {
                "phase": "unknown",
                "progress": 0,
                "elements": []
            }
    
    async def _create_project_from_interview(
        self,
        interview_state: InterviewState
    ) -> Project:
        """Create project from interview data"""
        try:
            # Parse dates
            from datetime import datetime
            start_date = None
            expected_completion = None
            
            if "start_date" in interview_state.answers:
                try:
                    start_date = datetime.strptime(
                        interview_state.answers["start_date"],
                        "%d/%m/%Y"
                    ).date()
                except:
                    pass
            
            if "expected_completion" in interview_state.answers:
                try:
                    expected_completion = datetime.strptime(
                        interview_state.answers["expected_completion"],
                        "%d/%m/%Y"
                    ).date()
                except:
                    pass
            
            # Create project info
            project_info = ProjectInfo(
                project_name=interview_state.answers.get("project_name", "Projeto Sem Nome"),
                project_type=interview_state.answers.get("project_type", "residential"),
                address=interview_state.answers.get("address", "Não informado"),
                responsible_engineer=interview_state.answers.get("responsible_engineer", "Não informado"),
                start_date=start_date,
                expected_completion=expected_completion
            )
            
            # Create project
            project = Project(
                info=project_info,
                overall_progress=Progress(percentage=15)  # Initial progress
            )
            
            # Add locations
            location_configs = [
                ("location_1", "Área Externa - Fachada", "external"),
                ("location_2", "Área Interna Principal", "internal"),
                ("location_3", "Área Técnica", "technical")
            ]
            
            for key, name, loc_type in location_configs:
                if key in interview_state.photos:
                    location = Location(
                        name=name,
                        description=f"{name} da obra",
                        location_type=loc_type,
                        current_phase=Phase(name="foundation"),
                        progress=Progress(percentage=30),
                        last_photo_date=datetime.utcnow()
                    )
                    project.add_location(location)
            
            # Save project
            saved_project = await self.project_service.create_project(project)
            
            # Save to JSON
            await self._save_project_json(saved_project, interview_state)
            
            return saved_project
            
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise
    
    async def _save_project_json(
        self,
        project: Project,
        interview_state: InterviewState
    ):
        """Save project to JSON file"""
        try:
            # Create output directory
            output_dir = Path("projects")
            output_dir.mkdir(exist_ok=True)
            
            # Generate filename
            safe_name = project.info.project_name.replace(" ", "_").lower()
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"obra_{safe_name}_{timestamp}.json"
            
            # Prepare JSON data
            json_data = {
                "project_info": project.info.to_dict(),
                "locations_status": {
                    f"location_{i+1}": {
                        "name": loc.name,
                        "current_phase": loc.current_phase.name if loc.current_phase else "planning",
                        "progress_percentage": loc.progress.percentage,
                        "last_photo_date": loc.last_photo_date.isoformat() if loc.last_photo_date else None,
                        "elements_detected": loc.elements_detected,
                        "observations": "",
                        "next_milestone": "Concretagem" if loc.current_phase and loc.current_phase.name == "foundation" else "Próxima fase"
                    }
                    for i, loc in enumerate(project.locations)
                },
                "timeline": [
                    {
                        "date": datetime.utcnow().isoformat(),
                        "event": "Projeto criado",
                        "phase": "initial",
                        "progress": project.overall_progress.percentage
                    }
                ],
                "overall_progress": {
                    "total_progress_percentage": project.overall_progress.percentage,
                    "current_main_phase": "foundation",
                    "estimated_completion": project.info.expected_completion.isoformat() if project.info.expected_completion else None,
                    "delays_identified": [],
                    "recommendations": project.get_recommendations()
                },
                "metadata": {
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat(),
                    "agent_version": "2.0.0",
                    "interview_data": interview_state.answers
                }
            }
            
            # Save to file
            filepath = output_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Project saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving project JSON: {str(e)}")
    
    def _generate_project_summary(self, project: Project, interview_state: InterviewState) -> str:
        """Generate project summary after creation"""
        summary = f"""
📦 **RESUMO DA OBRA DOCUMENTADA:**
- **Projeto**: {project.info.project_name}
- **Tipo**: {project.info.project_type}
- **Responsável**: {project.info.responsible_engineer}
- **Período**: {project.info.start_date} a {project.info.expected_completion} ({project.info.calculate_duration_days()} dias)

📍 **STATUS DOS 3 LOCAIS:**
"""
        
        for i, location in enumerate(project.locations, 1):
            summary += f"{i}. **{location.name}**: {location.current_phase.name if location.current_phase else 'Inicial'} - {location.progress.percentage}%\n"
        
        summary += f"""

📊 **Progresso Geral**: {project.overall_progress.percentage}% concluído
🎯 **Próxima Etapa**: {project.locations[0].current_phase.get_next_phases()[0] if project.locations and project.locations[0].current_phase else 'Fundação'}

✅ Documentação salva em: `obra_{project.info.project_name.replace(' ', '_').lower()}_{datetime.utcnow().strftime('%Y%m%d')}.json`

A partir de agora, sempre que enviar novas fotos, vou atualizar automaticamente o progresso da obra!
"""
        
        return summary
    
    async def _handle_project_query(
        self,
        session: ChatSession,
        message: str
    ) -> Dict[str, Any]:
        """Handle queries about existing project"""
        try:
            # Get project
            project = await self.project_service.get_project(UUID(session.project_id))
            
            if not project:
                return {
                    "message": "Projeto não encontrado.",
                    "next_action": "create_new"
                }
            
            # Use LLM to answer query
            context = f"""
            Projeto: {project.info.project_name}
            Progresso: {project.overall_progress.percentage}%
            Locais: {len(project.locations)}
            Status: {'Em dia' if not project.is_delayed() else 'Atrasado'}
            """
            
            messages = [
                SystemMessage(content="Responda sobre o projeto de forma clara e objetiva."),
                HumanMessage(content=f"Contexto: {context}\n\nPergunta: {message}")
            ]
            
            response = await self.llm.ainvoke(messages)
            
            return {
                "message": response.content,
                "data": {"project": project.to_dict()},
                "next_action": "continue"
            }
            
        except Exception as e:
            logger.error(f"Error handling project query: {str(e)}")
            return {
                "message": "Erro ao consultar projeto.",
                "next_action": "retry"
            }
    
    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Format recommendations list"""
        if not recommendations:
            return "- Projeto progredindo bem. Manter ritmo atual."
        
        formatted = ""
        for i, rec in enumerate(recommendations[:3], 1):  # Limit to 3
            formatted += f"{i}. {rec}\n"
        
        return formatted
    
    def _build_context(self, session: ChatSession) -> Dict[str, Any]:
        """Build context from session"""
        project_id = session.metadata.get("project_id") if session.metadata else None
        return {
            "session_id": session.id,
            "project_id": project_id,
            "message_count": len(session.messages),
            "state": session.status,
            "last_messages": [
                {"role": msg.role, "content": msg.content[:100]}
                for msg in session.messages[-5:]  # Last 5 messages
            ]
        }
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get chat session by ID"""
        return await self.history_manager.get_session(session_id)

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all chat sessions"""
        sessions = await self.history_manager.list_sessions()
        return [
            {
                "session_id": session.id,
                "project_id": session.metadata.get("project_id") if session.metadata else None,
                "state": session.status,
                "message_count": len(session.messages),
                "created_at": session.started_at.isoformat(),
                "updated_at": session.last_activity.isoformat()
            }
            for session in sessions
        ]
