"""
Supervisor Agent - LangGraph Orchestration
Coordinates multiple specialized agents using LangGraph
Following SOLID and Chain of Responsibility patterns
"""

import json
import logging
import base64
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime, timedelta, date
from uuid import UUID, uuid4
from enum import Enum

from langchain.schema import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, add_messages
from langgraph.checkpoint.memory import MemorySaver

from agents.interfaces.agent_interface import AgentContext, AgentResult
from agents.visual_agent import VisualAgent
from agents.document_agent import DocumentAgent
from agents.progress_agent import ProgressAgent
from agents.report_agent import ReportAgent
from domain.entities.project import Project
from domain.exceptions.domain_exceptions import DomainException
from infrastructure.config.prompt_manager import get_prompt_manager
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State shared between agents in the graph"""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    project_id: Optional[str]
    current_agent: Optional[str]
    task: Optional[str]
    context: Dict[str, Any]
    results: Dict[str, Any]
    errors: List[str]
    next_agent: Optional[str]
    completed: bool


class TaskType(Enum):
    """Types of tasks the supervisor can handle"""
    ANALYZE_IMAGE = "analyze_image"
    PROCESS_DOCUMENT = "process_document"
    UPDATE_PROGRESS = "update_progress"
    GENERATE_REPORT = "generate_report"
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"
    CHAT_INTERACTION = "chat_interaction"


class SupervisorAgent:
    """
    Supervisor Agent - Orchestrates multiple specialized agents
    Implements the Supervisor pattern for agent coordination
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize supervisor with configuration"""
        self.config = config
        settings = get_settings()
        self.llm = config.get('llm')
        if self.llm is None:
            self.llm = ChatOpenAI(
                model=config.get('model', settings.chat_model),
                temperature=config.get('temperature', 0.3)
            )

        # Load prompts from centralized YAML
        self.prompt_manager = get_prompt_manager()

        # Store project repository for user project checks
        self.project_repository = config.get('project_repository')

        # Store storage service for saving attachments
        self.storage_service = config.get('storage_service')

        # Store chat history manager for accessing session messages
        self.chat_history_manager = config.get('chat_history_manager')

        # Current session ID for accessing chat history
        self.current_session_id = None

        # Initialize specialized agents with shared LLM
        visual_config = config.get('visual_config', {})
        visual_config['llm'] = self.llm
        self.visual_agent = VisualAgent(visual_config)

        document_config = config.get('document_config', {})
        document_config['llm'] = self.llm
        self.document_agent = DocumentAgent(document_config)

        progress_config = config.get('progress_config', {})
        progress_config['llm'] = self.llm
        self.progress_agent = ProgressAgent(
            progress_config,
            project_repository=config.get('project_repository')
        )

        report_config = config.get('report_config', {})
        report_config['llm'] = self.llm
        self.report_agent = ReportAgent(
            report_config,
            project_repository=config.get('project_repository')
        )

        # Build the agent graph
        self.graph = self._build_graph()
        self.memory = MemorySaver()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        # Create state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("visual", self._visual_node)
        workflow.add_node("document", self._document_node)
        workflow.add_node("progress", self._progress_node)
        workflow.add_node("report", self._report_node)
        workflow.add_node("synthesize", self._synthesize_node)
        
        # Define conditional routing from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            self._route_from_supervisor,
            {
                "visual": "visual",
                "document": "document",
                "progress": "progress",
                "report": "report",
                "synthesize": "synthesize",
                "end": END
            }
        )

        # Conditional edges based on task completion
        workflow.add_conditional_edges(
            "visual",
            self._route_after_visual,
            {
                "progress": "progress",
                "report": "report",
                "synthesize": "synthesize",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "document",
            self._route_after_document,
            {
                "progress": "progress",
                "report": "report",
                "synthesize": "synthesize",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "progress",
            self._route_after_progress,
            {
                "report": "report",
                "synthesize": "synthesize",
                "end": END
            }
        )
        
        workflow.add_edge("report", "synthesize")
        workflow.add_edge("synthesize", END)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        return workflow.compile()

    async def _get_session_messages(self, session_id: str, limit: int = 60) -> List[Dict[str, str]]:
        """Fetch last N messages from MongoDB for the session"""
        if not self.chat_history_manager or not session_id:
            logger.warning("No chat_history_manager or session_id - cannot fetch messages")
            return []

        try:
            messages = await self.chat_history_manager.get_session_messages(session_id, limit=limit)
            logger.info(f"📥 Fetched {len(messages)} messages from MongoDB for session {session_id}")

            # Convert to OpenRouter format
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })

            return history
        except Exception as e:
            logger.error(f"Error fetching session messages: {e}", exc_info=True)
            return []

    async def process_request(
        self,
        user_input: str,
        project_id: Optional[UUID] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None  # Add session_id parameter
    ) -> Dict[str, Any]:
        """Process user request through the agent graph"""
        try:
            # Store session ID for accessing chat history
            if session_id:
                self.current_session_id = session_id
            # Load project context if project_id is provided
            project_context = None
            if project_id and self.config.get('project_repository'):
                try:
                    project = await self.config['project_repository'].get_project(str(project_id))
                    if project:
                        project_context = {
                            'project_id': str(project.id),
                            'name': project.info.project_name,
                            'type': project.info.project_type,
                            'location': project.info.address,
                            'description': f"Obra {project.info.project_type} em {project.info.address}",
                            'status': getattr(project, 'status', 'planning')
                        }
                        logger.info(f"Loaded project context: {project.info.project_name}")
                except Exception as e:
                    logger.warning(f"Failed to load project context: {e}")

            # Analyze user intent with conversation history and project context
            task_type, task_details = await self._analyze_intent(user_input, attachments, conversation_history, project_id)

            # Prepare messages with conversation history
            messages = []

            # Add project context as system message if available
            if project_context:
                project_summary = f"Contexto do Projeto:\n- Nome: {project_context['name']}\n- Tipo: {project_context['type']}\n- Localização: {project_context['location']}\n- Status: {project_context['status']}"
                if project_context.get('description'):
                    project_summary += f"\n- Descrição: {project_context['description']}"
                messages.append({'role': 'system', 'content': project_summary})
                logger.info("Added project context to messages")

            # Add conversation history if available
            if conversation_history:
                # Conversation history already in OpenRouter format
                messages.extend(conversation_history)
                logger.info(f"Added {len(conversation_history)} previous messages to context")

            # Add current user message
            messages.append({'role': 'user', 'content': user_input})

            # Log attachments for debugging
            if attachments:
                logger.info(f"📎 Received {len(attachments)} attachment(s)")
                for i, att in enumerate(attachments):
                    logger.info(f"  Attachment {i+1}: type={att.get('type')}, filename={att.get('filename', 'unknown')}")
            else:
                logger.info("📎 No attachments received")

            # Initialize state
            initial_state: AgentState = {
                'messages': messages,
                'project_id': str(project_id) if project_id else None,
                'current_agent': None,
                'task': task_type.value,
                'context': {
                    'user_input': user_input,
                    'attachments': attachments or [],
                    'task_details': task_details,
                    'conversation_history': conversation_history or [],
                    'timestamp': datetime.utcnow().isoformat()
                },
                'results': {},
                'errors': [],
                'next_agent': None,
                'completed': False
            }
            
            # Execute the graph
            config = {"configurable": {"thread_id": str(project_id) if project_id else "default"}}
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Format response
            response = self._format_response(final_state)
            
            return response
            
        except Exception as e:
            logger.error(f"Supervisor processing error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'messages': [{'role': 'assistant', 'content': f"I encountered an error: {str(e)}"}],
                'results': {}
            }

    async def _check_user_has_projects(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Check if user has any projects in database"""
        try:
            # TODO: Get actual user_id from session/context
            # For now, get all projects (will be filtered by user_id later)
            if self.project_repository and hasattr(self.project_repository, 'get_all'):
                projects = await self.project_repository.get_all()

                has_projects = len(projects) > 0
                project_list = [p.info.project_name for p in projects] if projects else []

                logger.info(f"Found {len(projects)} projects: {project_list}")

                return {
                    "has_projects": has_projects,
                    "project_count": len(projects),
                    "project_list": ", ".join(project_list) if project_list else "Nenhum"
                }
            else:
                # No repository available - assume no projects
                return {
                    "has_projects": False,
                    "project_count": 0,
                    "project_list": "Nenhum"
                }
        except Exception as e:
            logger.error(f"Error checking user projects: {str(e)}", exc_info=True)
            return {
                "has_projects": False,
                "project_count": 0,
                "project_list": "Nenhum"
            }

    async def _analyze_intent(
        self,
        user_input: str,
        attachments: Optional[List[Dict[str, Any]]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        project_id: Optional[UUID] = None
    ) -> tuple[TaskType, Dict[str, Any]]:
        """Analyze user intent to determine task type"""

        # PRIORITY CHECK: If user sent images, skip intent analysis and go directly to visual agent
        if attachments:
            images = [a for a in attachments if a.get('type', '').startswith('image/')]
            if images:
                logger.info(f"🖼️ Detected {len(images)} images - skipping intent analysis, routing directly to visual agent")
                return TaskType.ANALYZE_IMAGE, {
                    "primary_focus": "image_analysis",
                    "required_agents": ["visual"],
                    "image_count": len(images),
                    "skip_intent_analysis": True
                }

        # First check if user has any projects in database
        project_check = await self._check_user_has_projects()

        logger.info(f"Project check result: {project_check}")

        # Check if this is initial message (no conversation history)
        is_initial_message = not conversation_history or len(conversation_history) == 0

        # Check if user has attachments (images/documents) - if so, skip onboarding
        has_attachments = attachments and len(attachments) > 0

        # Check if we're in onboarding mode: no projects in DB AND no project_id in session
        # This keeps onboarding active until project is created
        # Check if we're waiting for cronograma data
        waiting_for_cronograma = False
        if conversation_history and len(conversation_history) > 0:
            # Check last assistant message
            for msg in reversed(conversation_history):
                if msg.get('role') == 'assistant':
                    content = msg.get('content', '').lower()
                    # Check if asked about cronograma
                    if any(phrase in content for phrase in [
                        'cronograma de atividades',
                        'percentuais de andamento',
                        'percentuais das atividades',
                        'compartilhar os percentuais'
                    ]):
                        # Check if user declined (said no)
                        user_declined = False
                        if user_input:
                            user_lower = user_input.lower().strip()
                            if user_lower in ['não', 'nao', 'no', 'nope', 'não tenho', 'nao tenho']:
                                user_declined = True
                                logger.info("📋 User declined cronograma - skipping onboarding")

                        if not user_declined:
                            waiting_for_cronograma = True
                            logger.info("📋 Detected: Last assistant message asked about cronograma")
                    break

        # BUT: if user has attachments, skip onboarding and go to analysis
        is_onboarding_needed = (not project_check["has_projects"] and not project_id and not has_attachments) or waiting_for_cronograma

        # Debug logging
        logger.info(f"🔍 Onboarding check:")
        logger.info(f"  - Has projects in DB: {project_check['has_projects']}")
        logger.info(f"  - Has project_id in session: {project_id is not None}")
        logger.info(f"  - Has attachments: {has_attachments}")
        logger.info(f"  - Waiting for cronograma: {waiting_for_cronograma}")
        logger.info(f"  - Onboarding needed: {is_onboarding_needed}")

        if has_attachments:
            logger.info(f"🖼️ User has {len(attachments)} attachment(s) - skipping onboarding, going to analysis")

        # If no projects and no project_id and no attachments, continue onboarding flow
        if is_onboarding_needed:
            # Only use check_project_exists_prompt on FIRST message
            # For subsequent messages, go directly to onboarding
            if is_initial_message:
                logger.info("Initial message - checking project status")

                # Use check_project_exists_prompt to decide flow
                check_system = self.prompt_manager.get_prompt('supervisor', 'check_project_exists_system')

                check_prompt = self.prompt_manager.get_prompt(
                    'supervisor',
                    'check_project_exists_prompt',
                    has_projects=str(project_check["has_projects"]),
                    project_count=str(project_check["project_count"]),
                    project_list=project_check["project_list"],
                    user_input=user_input,
                    context_history=""
                )

                messages = [
                    {"role": "system", "content": check_system},
                    {"role": "user", "content": check_prompt}
                ]

                try:
                    response = await self.llm.ainvoke(messages)
                    content = response.content.strip()

                    # Parse JSON response
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        content = json_match.group()

                    check_result = json.loads(content)

                    if check_result.get("needs_onboarding", True):
                        # Return CHAT_INTERACTION with onboarding flag
                        return TaskType.CHAT_INTERACTION, {
                            "needs_onboarding": True,
                            "reason": check_result.get("reason", "Nenhum projeto cadastrado" if not project_check["has_projects"] else "Configuração necessária"),
                            "response_type": "onboarding_welcome",
                            "has_existing_projects": project_check["has_projects"],
                            "project_list": project_check["project_list"]
                        }
                except Exception as e:
                    logger.error(f"Error checking project status: {str(e)}")
                    # Fallback based on project existence
                    return TaskType.CHAT_INTERACTION, {
                        "needs_onboarding": True,
                        "reason": "Nenhum projeto cadastrado" if not project_check["has_projects"] else "Configuração necessária",
                        "response_type": "onboarding_welcome",
                        "has_existing_projects": project_check["has_projects"],
                        "project_list": project_check["project_list"]
                    }
            else:
                # Continuation of onboarding - skip LLM check and go directly to onboarding
                logger.info("Onboarding continuation - continuing project data collection")
                return TaskType.CHAT_INTERACTION, {
                    "needs_onboarding": True,
                    "reason": "Coletando informações do projeto",
                    "response_type": "onboarding_welcome",
                    "has_existing_projects": project_check["has_projects"],
                    "project_list": project_check["project_list"]
                }

        # Build context from conversation history
        context_text = ""
        if conversation_history:
            context_text = "\n\nContexto da conversa anterior:\n"
            for msg in conversation_history[-5:]:  # Include last 5 messages for context
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]  # Limit content length
                context_text += f"- {role}: {content}\n"

        # Get prompts from centralized YAML
        system_msg = self.prompt_manager.get_prompt('supervisor', 'intent_analysis_system')

        # Get available projects from check
        available_projects = project_check["project_list"] if project_check["has_projects"] else "Nenhum projeto disponível no momento"

        user_prompt = self.prompt_manager.get_prompt(
            'supervisor',
            'intent_analysis_prompt',
            user_input=user_input,
            attachment_count=len(attachments) if attachments else 0,
            attachment_types=str([a.get('type') for a in attachments] if attachments else []),
            available_projects=available_projects,
            context_history=context_text
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            logger.info(f"LLM response for intent analysis: {response.content}")

            # Clean the response content to extract JSON
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()

            analysis = json.loads(content)

            # Map LLM response to TaskType enum with fallback
            task_type_str = analysis.get('task_type', 'chat_interaction')

            # Map common LLM responses to valid TaskType values
            task_type_mapping = {
                'project_selection': TaskType.CHAT_INTERACTION,
                'project_creation': TaskType.CHAT_INTERACTION,
                'onboarding': TaskType.CHAT_INTERACTION,
                'analyze_image': TaskType.ANALYZE_IMAGE,
                'process_document': TaskType.PROCESS_DOCUMENT,
                'update_progress': TaskType.UPDATE_PROGRESS,
                'generate_report': TaskType.GENERATE_REPORT,
                'comprehensive_analysis': TaskType.COMPREHENSIVE_ANALYSIS,
                'chat_interaction': TaskType.CHAT_INTERACTION,
            }

            # Try direct mapping first, then check if it's a valid TaskType value
            if task_type_str in task_type_mapping:
                task_type = task_type_mapping[task_type_str]
            else:
                try:
                    task_type = TaskType(task_type_str)
                except ValueError:
                    logger.warning(f"Unknown task type '{task_type_str}', defaulting to CHAT_INTERACTION")
                    task_type = TaskType.CHAT_INTERACTION

            return task_type, analysis.get('details', {})

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response.content}")
            logger.error(f"JSON error: {str(e)}")
            # Fallback to chat interaction for general conversation
            return TaskType.CHAT_INTERACTION, {
                "primary_focus": "general conversation",
                "required_agents": ["chat"],
                "expected_output": "conversational response"
            }
        except Exception as e:
            logger.error(f"Error in intent analysis: {str(e)}")
            # Fallback to chat interaction
            return TaskType.CHAT_INTERACTION, {
                "primary_focus": "error handling",
                "required_agents": ["chat"],
                "expected_output": "error response"
            }

    async def _supervisor_node(self, state: AgentState) -> AgentState:
        """Supervisor node - decides which agent to invoke"""
        try:
            task = state['task']
            context = state['context']
            task_details = context.get('task_details', {})

            # Check if onboarding is needed - skip routing to agents
            if task_details.get('needs_onboarding', False):
                # Go directly to synthesize for onboarding
                new_state = state.copy()
                new_state['current_agent'] = 'supervisor'
                new_state['next_agent'] = 'synthesize'
                logger.info("Onboarding detected - routing directly to synthesis")
                return new_state

            # Determine which agent(s) to invoke based on task
            if task == TaskType.ANALYZE_IMAGE.value:
                next_agent = 'visual'
            elif task == TaskType.PROCESS_DOCUMENT.value:
                next_agent = 'document'
            elif task == TaskType.UPDATE_PROGRESS.value:
                next_agent = 'progress'
            elif task == TaskType.GENERATE_REPORT.value:
                next_agent = 'report'
            elif task == TaskType.COMPREHENSIVE_ANALYSIS.value:
                # For comprehensive analysis, start with visual if images present
                if context.get('attachments'):
                    has_images = any(a.get('type') in ['image', 'photo'] for a in context['attachments'])
                    next_agent = 'visual' if has_images else 'document'
                else:
                    next_agent = 'progress'
            elif task == TaskType.CHAT_INTERACTION.value:
                # For general chat, go to synthesize directly
                next_agent = 'synthesize'
            else:
                # Default to progress agent for general queries
                next_agent = 'progress'

            # Update state with single values to avoid concurrent update errors
            new_state = state.copy()
            new_state['current_agent'] = 'supervisor'
            new_state['next_agent'] = next_agent
            new_state['messages'] = state['messages'] + [{
                'role': 'assistant',
                'content': f"Routing to {next_agent} agent for {task}"
            }]

            return new_state

        except Exception as e:
            new_state = state.copy()
            new_state['errors'] = state['errors'] + [f"Supervisor error: {str(e)}"]
            new_state['completed'] = True
            return new_state

    async def _save_attachment_to_storage(
        self,
        attachment: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Save attachment to MinIO/storage and return the file path

        Args:
            attachment: Attachment dict with 'data' (base64), 'url', or 'path'
            project_id: Project ID for organizing files

        Returns:
            File path in storage or None if failed
        """
        try:
            import tempfile
            from pathlib import Path

            # Determine project folder
            project_folder = project_id or 'temp'

            # Check if attachment has base64 data
            if 'data' in attachment:
                # Decode base64
                data_url = attachment['data']
                if ',' in data_url:
                    # Format: "data:image/jpeg;base64,/9j/4AAQ..."
                    header, base64_data = data_url.split(',', 1)
                else:
                    base64_data = data_url

                image_bytes = base64.b64decode(base64_data)

                # Determine file extension from mime type or default to jpg
                mime_type = attachment.get('mime_type', 'image/jpeg')
                extension = mime_type.split('/')[-1] if '/' in mime_type else 'jpg'

                # Create temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{extension}') as tmp_file:
                    tmp_file.write(image_bytes)
                    tmp_path = tmp_file.name

                # Upload to storage if available
                if self.storage_service:
                    storage_path = self.storage_service.upload_image(
                        file_path=tmp_path,
                        project_id=project_folder,
                        category='attachments',
                        metadata={
                            'original_name': attachment.get('filename', 'unknown'),
                            'mime_type': mime_type,
                            'uploaded_at': datetime.utcnow().isoformat()
                        }
                    )
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
                    logger.info(f"Attachment saved to storage: {storage_path}")
                    return storage_path
                else:
                    # No storage service, return temp path
                    logger.warning("No storage service available, using temp file")
                    return tmp_path

            # If attachment has URL, download and save
            elif 'url' in attachment:
                logger.info(f"Attachment URL provided: {attachment['url']}")
                return attachment['url']  # Visual agent will handle URL download

            # If attachment already has path
            elif 'path' in attachment:
                return attachment['path']

            else:
                logger.error("Attachment has no data, url, or path")
                return None

        except Exception as e:
            logger.error(f"Failed to save attachment: {str(e)}", exc_info=True)
            return None

    async def _visual_node(self, state: AgentState) -> AgentState:
        """Visual agent node"""
        try:
            # Generate a valid UUID for context (use project_id if available, otherwise generate new)
            context_project_id = UUID(state['project_id']) if state['project_id'] else uuid4()

            context = AgentContext(
                project_id=context_project_id,
                session_id='visual_session',
                metadata=state['context']
            )

            # Process images if present
            attachments = state['context'].get('attachments', [])
            logger.info(f"🖼️ Visual node: found {len(attachments)} total attachments")

            # Filter images by MIME type (image/jpeg, image/png, etc) or simple type
            images = [a for a in attachments if (
                a.get('type', '').startswith('image/') or
                a.get('type') in ['image', 'photo']
            )]
            logger.info(f"🖼️ Visual node: filtered to {len(images)} images (types: {[a.get('type') for a in attachments]})")

            # If no images in attachments but has project_id, fetch images from database
            if not images and state['project_id'] and self.config.get('project_repository'):
                try:
                    logger.info(f"📁 No attachments found, fetching images from database for project {state['project_id']}")

                    # Import here to avoid circular dependency
                    from infrastructure.database.project_models import ProjectImageModel

                    # Fetch latest images from this project (limit to 5 most recent)
                    db_images = await ProjectImageModel.find(
                        ProjectImageModel.project_id == state['project_id']
                    ).sort("-captured_at").limit(5).to_list()

                    if db_images:
                        logger.info(f"✅ Found {len(db_images)} images in database")
                        # Convert database images to attachment format
                        for db_img in db_images:
                            images.append({
                                'type': 'image/jpeg',  # Assume JPEG for now
                                'filename': db_img.file_path.split('/')[-1] if db_img.file_path else 'unknown.jpg',
                                'path': db_img.file_path,
                                'from_database': True,
                                'image_id': str(db_img.image_id),
                                'captured_at': db_img.captured_at.isoformat() if db_img.captured_at else None
                            })
                        logger.info(f"📸 Prepared {len(images)} images from database for analysis")
                    else:
                        logger.warning("⚠️ No images found in database for this project")

                except Exception as e:
                    logger.error(f"Error fetching images from database: {e}", exc_info=True)
                    new_state = state.copy()
                    new_state['errors'] = state['errors'] + [f"Error fetching images from database: {str(e)}"]

            new_state = state.copy()
            new_state['current_agent'] = 'visual'

            if images:
                logger.info(f"✅ Starting visual analysis for {len(images)} images")
                visual_results = new_state['results'].get('visual', [])

                for i, image in enumerate(images):
                    logger.info(f"📸 Processing image {i+1}/{len(images)}: {image.get('filename', 'unknown')}")

                    # Extract base64 data if available (for new attachments)
                    image_base64 = None
                    if image.get('data'):
                        data_url = image['data']
                        if ',' in data_url:
                            # Format: "data:image/jpeg;base64,/9j/4AAQ..."
                            _, image_base64 = data_url.split(',', 1)
                        else:
                            image_base64 = data_url
                        logger.info(f"✅ Extracted base64 data from attachment (length: {len(image_base64)})")

                    # Check if image is from database (already in storage) or new attachment
                    if image.get('from_database'):
                        storage_path = image.get('path')
                        logger.info(f"Using existing image from database: {storage_path}")
                    else:
                        # Save new attachment to storage (MinIO/S3)
                        storage_path = await self._save_attachment_to_storage(
                            attachment=image,
                            project_id=state['project_id']
                        )

                        if not storage_path:
                            logger.error(f"Failed to save image attachment: {image.get('filename', 'unknown')}")
                            new_state['errors'] = new_state['errors'] + [f"Failed to save image: {image.get('filename', 'unknown')}"]
                            continue

                        # Update image dict with storage path for later use
                        image['path'] = storage_path
                        logger.info(f"Processing image from storage: {storage_path}")

                    input_data = {
                        'task': 'analyze',
                        'image_path': storage_path,
                        'location_type': image.get('location_type', 'general')
                    }

                    # Add base64 data if available (avoids 403 error from MinIO)
                    if image_base64:
                        input_data['image_base64'] = image_base64
                        logger.info(f"🔑 Passing base64 data directly to Visual Agent")

                    result = await self.visual_agent.process(input_data, context)

                    if result.success:
                        visual_results.append(result.data)
                    else:
                        new_state['errors'] = new_state['errors'] + (result.errors or [])

                new_state['results'] = new_state['results'].copy()
                new_state['results']['visual'] = visual_results
                logger.info(f"✅ Visual analysis completed: {len(visual_results)} results generated")

                # Save processed images to MongoDB with detailed analysis reports
                if state['project_id'] and visual_results:
                    try:
                        from infrastructure.database.project_models import ProjectImageModel, AnalysisReport
                        from infrastructure.timezone_utils import now_brazil

                        logger.info(f"💾 Saving {len(images)} images to MongoDB...")
                        logger.info(f"   Project ID: {state['project_id']}")

                        for idx, (img, result) in enumerate(zip(images, visual_results)):
                            # Get storage path (already saved to MinIO if storage service available)
                            storage_path = img.get('path', img.get('filename', f'image_{idx}.jpg'))

                            # Extract relative path from full URL if needed
                            # If storage_path is a full URL like http://localhost:9000/bucket/path/file.jpg
                            # Extract just the path part: path/file.jpg
                            file_path = storage_path
                            if storage_path.startswith('http://') or storage_path.startswith('https://'):
                                # Extract path after bucket name
                                # URL format: http://localhost:9000/construction-images/project_id/category/file.jpg
                                # We want: project_id/category/file.jpg
                                parts = storage_path.split('/construction-images/')
                                if len(parts) > 1:
                                    file_path = parts[1]
                                    logger.info(f"   Extracted relative path from URL: {file_path}")

                            logger.info(f"💾 Saving image {idx+1}: {img.get('filename')}")
                            logger.info(f"   Storage path: {storage_path}")
                            logger.info(f"   File path for DB: {file_path}")
                            logger.info(f"   Project ID: {state['project_id']}")

                            # Create image record in MongoDB
                            # Convert phase to lowercase and normalize to enum format
                            phase_detected = result.get('phase_detected')
                            if phase_detected:
                                import unicodedata
                                # Remove accents
                                phase_detected = ''.join(
                                    c for c in unicodedata.normalize('NFD', phase_detected)
                                    if unicodedata.category(c) != 'Mn'
                                )
                                # Normalize: convert to lowercase and replace spaces/special chars with underscores
                                phase_detected = phase_detected.lower()
                                phase_detected = phase_detected.replace(' ', '_')
                                phase_detected = phase_detected.replace('-', '_')
                                phase_detected = phase_detected.replace('/', '_')
                                phase_detected = phase_detected.replace('(', '')
                                phase_detected = phase_detected.replace(')', '')

                                # Map common variations to standard enum names
                                phase_mapping = {
                                    'instalacoes_hidraulicas_embutidas': 'instalacoes_hidraulicas',
                                    'infra_de_eletrica': 'infra_eletrica',
                                    'infra_eletrica_eletrodutos': 'infra_eletrica',
                                    'caixinhas_de_eletrica': 'caixinhas_eletricas',
                                    'instalacoes_eletricas_drywall': 'instalacoes_eletricas_drywall',
                                    'ceramica_soleira': 'ceramica_soleira',
                                    'loucas_e_metais': 'loucas_metais',
                                    'demao_de_pintura_fundo_selador': 'demao_pintura_fundo',
                                    'demao_de_pintura': 'demao_pintura_fundo',
                                    'gesso_emboco_aq': 'gesso_emboco',
                                }
                                phase_detected = phase_mapping.get(phase_detected, phase_detected)

                            image_record = ProjectImageModel(
                                project_id=str(state['project_id']),
                                file_path=file_path,  # Use relative path, not full URL
                                bucket='construction-images' if self.storage_service else None,
                                mime_type=img.get('type', 'image/jpeg'),
                                size_bytes=img.get('size', 0),
                                phase_detected=phase_detected,  # Converted to lowercase
                                components_detected=result.get('components_detected', []),  # Changed key
                                confidence_score=result.get('confidence', 0.0),
                                analyzed_at=now_brazil(),
                                metadata={
                                    'analysis': result,
                                    'original_filename': img.get('filename')
                                }
                            )
                            await image_record.insert()
                            logger.info(f"✅ Image saved to MongoDB with ID: {image_record.image_id}")

                            # Create detailed analysis report
                            analysis_report = AnalysisReport(
                                project_id=str(state['project_id']),
                                image_id=image_record.image_id,
                                analyzer_model="google/gemini-2.5-flash-image-preview",
                                analysis_type="comprehensive",

                                # Phase detection (use lowercased phase)
                                phase_detected=phase_detected,  # Already converted to lowercase above
                                phase_confidence=result.get('phase_confidence', result.get('confidence', 0.0)),
                                phase_details=result.get('phase_details', ''),

                                # Elements and components
                                elements_found=result.get('elements_found', []),
                                components_detected=result.get('components', []),

                                # Progress
                                progress_percentage=result.get('progress_percentage', 0),
                                progress_justification=result.get('progress_justification', ''),

                                # Quality
                                quality_score=result.get('quality_score', 0),
                                quality_notes=result.get('quality_notes', ''),

                                # Safety
                                safety_issues=result.get('safety_issues', []),
                                safety_severity=result.get('safety_severity', 'unknown'),

                                # Recommendations
                                recommendations=result.get('recommendations', []),
                                issues=result.get('issues', []),

                                # Raw data
                                raw_analysis=result,
                                confidence_score=result.get('confidence', 0.0)
                            )
                            await analysis_report.insert()
                            logger.info(f"📊 Saved analysis report for image: {img.get('filename')}")

                            # Update cronograma with detected activity progress
                            if phase_detected and result.get('progress_percentage'):
                                logger.info(f"🔍 Imagem detectou: atividade='{phase_detected}', progresso={result.get('progress_percentage')}%")
                                await self._update_cronograma_from_analysis(
                                    project_id=str(state['project_id']),
                                    activity=phase_detected,
                                    progress_percentage=result.get('progress_percentage', 0)
                                )

                    except Exception as e:
                        logger.error(f"Error saving images/reports to MongoDB: {e}", exc_info=True)
            else:
                logger.warning(f"⚠️ No images found to process! Attachments received: {len(attachments)}")

            new_state['messages'] = state['messages'] + [{
                'role': 'assistant',
                'content': f"Visual analysis completed: {len(images)} images processed"
            }]

            return new_state

        except Exception as e:
            new_state = state.copy()
            new_state['current_agent'] = 'visual'
            new_state['errors'] = state['errors'] + [f"Visual agent error: {str(e)}"]
            return new_state

    async def _document_node(self, state: AgentState) -> AgentState:
        """Document agent node"""
        try:
            context = AgentContext(
                project_id=UUID(state['project_id']) if state['project_id'] else UUID(),
                session_id='document_session',
                metadata=state['context']
            )

            # Process documents if present
            attachments = state['context'].get('attachments', [])
            documents = [a for a in attachments if a.get('type') in ['document', 'pdf', 'text']]

            new_state = state.copy()
            new_state['current_agent'] = 'document'

            if documents:
                document_results = new_state['results'].get('document', [])

                for doc in documents:
                    input_data = {
                        'task': 'extract_specifications',
                        'document_path': doc.get('path')
                    }

                    result = await self.document_agent.process(input_data, context)

                    if result.success:
                        document_results.append(result.data)
                    else:
                        new_state['errors'] = new_state['errors'] + (result.errors or [])

                new_state['results'] = new_state['results'].copy()
                new_state['results']['document'] = document_results

            new_state['messages'] = state['messages'] + [{
                'role': 'assistant',
                'content': f"Document analysis completed: {len(documents)} documents processed"
            }]

            return new_state

        except Exception as e:
            new_state = state.copy()
            new_state['current_agent'] = 'document'
            new_state['errors'] = state['errors'] + [f"Document agent error: {str(e)}"]
            return new_state

    async def _progress_node(self, state: AgentState) -> AgentState:
        """Progress agent node"""
        try:
            if not state['project_id']:
                new_state = state.copy()
                new_state['errors'] = state['errors'] + ["Project ID required for progress analysis"]
                return new_state

            context = AgentContext(
                project_id=UUID(state['project_id']),
                session_id='progress_session',
                metadata=state['context']
            )

            # Calculate progress based on visual results if available
            visual_results = state['results'].get('visual', [])

            input_data = {
                'task': 'calculate_progress',
                'project_id': state['project_id'],
                'visual_results': visual_results
            }

            new_state = state.copy()
            new_state['current_agent'] = 'progress'

            result = await self.progress_agent.process(input_data, context)

            if result.success:
                new_state['results'] = new_state['results'].copy()
                new_state['results']['progress'] = result.data
            else:
                new_state['errors'] = new_state['errors'] + (result.errors or [])

            new_state['messages'] = state['messages'] + [{
                'role': 'assistant',
                'content': f"Progress analysis completed"
            }]

            return new_state

        except Exception as e:
            new_state = state.copy()
            new_state['current_agent'] = 'progress'
            new_state['errors'] = state['errors'] + [f"Progress agent error: {str(e)}"]
            return new_state

    async def _report_node(self, state: AgentState) -> AgentState:
        """Report agent node"""
        try:
            if not state['project_id']:
                new_state = state.copy()
                new_state['errors'] = state['errors'] + ["Project ID required for report generation"]
                return new_state

            context = AgentContext(
                project_id=UUID(state['project_id']),
                session_id='report_session',
                metadata=state['context']
            )

            # Determine report type based on context
            report_type = state['context'].get('task_details', {}).get('report_type', 'progress_report')

            input_data = {
                'task': report_type,
                'project_id': state['project_id'],
                'include_visuals': bool(state['results'].get('visual')),
                'include_documents': bool(state['results'].get('document'))
            }

            new_state = state.copy()
            new_state['current_agent'] = 'report'

            result = await self.report_agent.process(input_data, context)

            if result.success:
                new_state['results'] = new_state['results'].copy()
                new_state['results']['report'] = result.data
            else:
                new_state['errors'] = new_state['errors'] + (result.errors or [])

            new_state['messages'] = state['messages'] + [{
                'role': 'assistant',
                'content': f"Report generation completed"
            }]

            return new_state

        except Exception as e:
            new_state = state.copy()
            new_state['current_agent'] = 'report'
            new_state['errors'] = state['errors'] + [f"Report agent error: {str(e)}"]
            return new_state

    async def _synthesize_node(self, state: AgentState) -> AgentState:
        """Synthesize results from all agents"""
        try:
            # Check if onboarding - skip normal synthesis
            task_details = state['context'].get('task_details', {})
            if task_details.get('needs_onboarding', False):
                # For onboarding, just generate the welcome message
                new_state = state.copy()
                new_state['completed'] = True

                # Generate final message
                final_message = await self._generate_final_response(new_state)

                new_state['messages'] = state['messages'] + [{
                    'role': 'assistant',
                    'content': final_message
                }]

                return new_state

            # Combine all results into coherent response
            synthesis = {
                'summary': self._generate_summary(state['results']),
                'key_findings': self._extract_key_findings(state['results']),
                'recommendations': self._compile_recommendations(state['results']),
                'next_steps': self._suggest_next_steps(state['results'], state['context'])
            }

            new_state = state.copy()
            new_state['results'] = new_state['results'].copy()
            new_state['results']['synthesis'] = synthesis
            new_state['completed'] = True

            # Generate final message
            final_message = await self._generate_final_response(new_state)

            new_state['messages'] = state['messages'] + [{
                'role': 'assistant',
                'content': final_message
            }]

            return new_state

        except Exception as e:
            logger.error(f"Synthesis error: {str(e)}", exc_info=True)
            new_state = state.copy()
            new_state['errors'] = state['errors'] + [f"Synthesis error: {str(e)}"]
            new_state['completed'] = True
            return new_state

    def _route_from_supervisor(self, state: AgentState) -> str:
        """Determine which agent to invoke from supervisor"""
        # Check if onboarding is needed - skip to synthesis
        task_details = state['context'].get('task_details', {})
        if task_details.get('needs_onboarding', False):
            return 'synthesize'

        return state.get('next_agent', 'progress')  # Default to progress if no next_agent set

    def _route_after_visual(self, state: AgentState) -> str:
        """Determine next step after visual agent"""
        task = state['task']
        
        if task == TaskType.COMPREHENSIVE_ANALYSIS.value:
            # Continue to progress analysis
            return 'progress'
        elif task == TaskType.ANALYZE_IMAGE.value:
            # Check if report is needed
            if state['context'].get('generate_report', False):
                return 'report'
            else:
                return 'synthesize'
        else:
            return 'end'

    def _route_after_document(self, state: AgentState) -> str:
        """Determine next step after document agent"""
        task = state['task']
        
        if task == TaskType.COMPREHENSIVE_ANALYSIS.value:
            return 'progress'
        elif state['context'].get('generate_report', False):
            return 'report'
        else:
            return 'synthesize'

    def _route_after_progress(self, state: AgentState) -> str:
        """Determine next step after progress agent"""
        if state['context'].get('generate_report', False) or state['task'] == TaskType.GENERATE_REPORT.value:
            return 'report'
        else:
            return 'synthesize'

    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate summary of all results"""
        summary_parts = []

        if 'visual' in results and len(results['visual']) > 0:
            visual_count = len(results['visual'])
            summary_parts.append(f"Analisadas {visual_count} imagem(ns)")

            # Add details from visual analysis using structured fields
            for visual in results['visual']:
                # Build summary from structured data instead of raw analysis
                if 'phase_detected' in visual and visual['phase_detected']:
                    phase_name = visual['phase_detected']
                    summary_parts.append(f"Fase: {phase_name}")

                if 'progress_percentage' in visual and visual['progress_percentage'] > 0:
                    progress = visual['progress_percentage']
                    summary_parts.append(f"Progresso: {progress}%")

        if 'document' in results:
            doc_count = len(results['document'])
            summary_parts.append(f"Processados {doc_count} documento(s)")

        if 'progress' in results:
            progress = results['progress'].get('overall_progress', 0)
            summary_parts.append(f"Progresso do projeto: {progress}%")

        if 'report' in results:
            summary_parts.append("Relatório detalhado gerado")

        return ". ".join(summary_parts) if summary_parts else "Análise concluída"

    def _extract_key_findings(self, results: Dict[str, Any]) -> List[str]:
        """Extract key findings from results"""
        findings = []

        # Extract visual findings using structured fields
        if 'visual' in results:
            for i, visual in enumerate(results['visual'], 1):
                # Build findings from structured data
                finding_parts = []

                if 'phase_detected' in visual and visual['phase_detected']:
                    phase_name = visual['phase_detected']
                    confidence = visual.get('phase_confidence', 0)
                    finding_parts.append(f"Fase: {phase_name}")
                    if confidence > 0:
                        finding_parts.append(f"(confiança: {confidence*100:.0f}%)")

                if 'progress_percentage' in visual and visual['progress_percentage'] > 0:
                    progress_pct = visual['progress_percentage']
                    finding_parts.append(f"Progresso: {progress_pct}%")

                if finding_parts:
                    findings.append(f"📸 Imagem {i}: {' '.join(finding_parts)}")

                if 'elements_found' in visual and visual['elements_found']:
                    elements = visual['elements_found']
                    if isinstance(elements, list) and len(elements) > 0:
                        elements_str = ", ".join(elements[:5])  # Limit to first 5
                        findings.append(f"  Elementos: {elements_str}")

        # Extract document findings
        if 'document' in results:
            for doc in results['document']:
                if 'specifications' in doc:
                    findings.append("📄 Especificações técnicas extraídas")

        # Extract progress findings
        if 'progress' in results:
            if results['progress'].get('is_on_track'):
                findings.append("Project is on track")
            else:
                findings.append("Project shows delays")
        
        return findings[:5]  # Limit to top 5 findings

    def _compile_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Compile recommendations from all agents"""
        recommendations = []

        # Extract recommendations from visual analysis
        if 'visual' in results:
            for visual in results['visual']:
                if 'recommendations' in visual and isinstance(visual['recommendations'], list):
                    for rec in visual['recommendations']:
                        if isinstance(rec, str):
                            recommendations.append(rec)

        # Extract recommendations from progress analysis
        if 'progress' in results:
            recs = results['progress'].get('recommendations', [])
            if isinstance(recs, list):
                for rec in recs:
                    if isinstance(rec, str):
                        recommendations.append(rec)

        # Extract recommendations from report
        if 'report' in results:
            if 'recommendations' in results['report'] and isinstance(results['report']['recommendations'], list):
                for rec in results['report']['recommendations']:
                    if isinstance(rec, str):
                        recommendations.append(rec)

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            # Only add if it's a string and not too long (avoid prompt injection)
            if isinstance(rec, str) and len(rec) < 500:
                if rec not in seen:
                    seen.add(rec)
                    unique_recommendations.append(rec)

        return unique_recommendations[:5]  # Limit to top 5

    def _suggest_next_steps(self, results: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Suggest next steps based on analysis"""
        next_steps = []
        
        # Check if photos need updating
        if 'visual' in results:
            for visual in results['visual']:
                if visual.get('confidence', 0) < 0.7:
                    next_steps.append("Consider taking clearer photos for better analysis")
                    break
        
        # Check if progress needs updating
        if 'progress' in results:
            if results['progress'].get('overall_progress', 0) < 30:
                next_steps.append("Focus on accelerating initial phases")
            elif results['progress'].get('is_delayed'):
                next_steps.append("Review resource allocation to address delays")
        
        # Check if documentation is needed
        if 'document' not in results and context.get('task') == TaskType.COMPREHENSIVE_ANALYSIS.value:
            next_steps.append("Upload project documents for complete analysis")
        
        return next_steps[:3]  # Limit to top 3

    async def _try_create_project_from_conversation(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        Try to extract project data from conversation and create project in database

        Returns:
            Project ID if created successfully, None otherwise
        """
        if not self.project_repository or not hasattr(self.project_repository, 'create_project'):
            logger.warning("No project_repository available to create project")
            return None

        try:
            # Use LLM to extract structured project data from conversation
            extract_system = """Você é um extrator de dados especializado. Analise TODA a conversa e extraia informações sobre o projeto de construção.

IMPORTANTE:
- Procure informações mencionadas de forma direta ou indireta
- SEMPRE traduza o tipo para inglês (residencial → residential, comercial → commercial, reforma → reform)

Retorne JSON:
{
  "has_sufficient_data": true/false,
  "name": "nome do projeto (se mencionado)",
  "type": "residential/commercial/industrial/reform/infrastructure (SEMPRE EM INGLÊS)",
  "address": "endereço/localização (se mencionado)",
  "responsible_engineer": "nome do engenheiro (se mencionado)",
  "description": "resumo do que foi discutido"
}

CRITÉRIO para has_sufficient_data = true:
- TEM que ter: name E type E address
- Exemplo: "Obra predial, residencial, Jardins SP" = suficiente
- Exemplo: "Obra em SP, residencial" = insuficiente (falta nome)

MAPEAMENTO DE TIPOS (SEMPRE USE INGLÊS NO JSON):
- residencial → residential
- comercial → commercial
- industrial → industrial
- reforma → reform
- infraestrutura → infrastructure

Se usuário apenas listou opções sem escolher, retorne has_sufficient_data: false."""

            # Format messages handling both dict and LangChain message objects
            conversation_lines = []
            for msg in messages[-10:]:  # Last 10 messages
                if isinstance(msg, dict):
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                elif hasattr(msg, 'type'):
                    # LangChain message object
                    role = "user" if msg.type == "human" else "assistant" if msg.type == "ai" else "system"
                    content = msg.content if hasattr(msg, 'content') else ''
                else:
                    continue

                conversation_lines.append(f"{role}: {content}")

            extract_prompt = "Conversa:\n" + "\n".join(conversation_lines)

            extract_messages = [
                {"role": "system", "content": extract_system},
                {"role": "user", "content": extract_prompt}
            ]

            response = await self.llm.ainvoke(extract_messages)
            content = response.content.strip()

            # Parse JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return None

            extracted_data = json.loads(json_match.group())

            if not extracted_data.get('has_sufficient_data', False):
                logger.info("Insufficient data to create project")
                return None

            if not extracted_data.get('name'):
                logger.info("Missing required field: name")
                return None

            # Mapeamento de tipos em português para inglês
            type_mapping = {
                'residencial': 'residential',
                'comercial': 'commercial',
                'industrial': 'industrial',
                'reforma': 'reform',
                'infraestrutura': 'infrastructure'
            }

            # Get and normalize type
            project_type = extracted_data.get('type', 'residential').lower()
            normalized_type = type_mapping.get(project_type, project_type)

            # Create project data dict
            project_data = {
                "name": extracted_data.get('name'),
                "type": normalized_type,
                "address": extracted_data.get('address', ''),
                "responsible_engineer": extracted_data.get('responsible_engineer', ''),
                "description": extracted_data.get('description', ''),
                "start_date": None,
                "expected_completion": None
            }

            # Create project in database
            project = await self.project_repository.create_project(project_data)

            logger.info(f"Project created successfully: {project.id} - {project.info.project_name}")
            return str(project.id)

        except Exception as e:
            logger.error(f"Error creating project from conversation: {str(e)}", exc_info=True)
            return None

    async def _extract_cronograma_from_conversation(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
        """
        Extract activity percentages from conversation

        Returns:
            Dictionary with activity names and percentages, e.g., {"alvenaria": 80.0, "contrapiso": 50.0}
        """
        try:
            # Use LLM to extract cronograma data from conversation
            extract_system = """Você é um extrator de dados especializado em cronogramas de obras.

Analise a conversa e extraia TODAS as informações do cronograma: percentuais, datas de início, duração.

28 ATIVIDADES PADRÃO (use EXATAMENTE esses nomes no JSON):
1. prumada
2. alvenaria
3. contramarco
4. instalacoes_hidraulicas
5. infra_eletrica
6. fiacao
7. caixinhas_eletricas
8. argamassa_am
9. contrapiso
10. impermeabilizacao
11. protecao_mecanica
12. guarda_corpo
13. capa_peitoril
14. gesso_emboco
15. guias_montantes_drywall
16. instalacoes_eletricas_drywall
17. drywall_fechamento
18. ceramica_soleira
19. forro
20. caixilhos
21. massa_paredes
22. demao_pintura_fundo
23. portas_madeira
24. loucas_metais
25. desengrosso
26. pintura_final
27. limpeza_final
28. comunicacao_visual

Retorne JSON com as atividades e TODOS os dados disponíveis:
{
  "has_cronograma_data": true/false,
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

REGRAS:
- Use APENAS os nomes das 28 atividades listadas acima (lowercase, com underscores)
- Normalize variações (ex: "Instalações Hidráulicas" → "instalacoes_hidraulicas")
- percentage: peso da atividade no projeto total (soma deve dar 100%)
- duration_days: duração em dias úteis (se mencionado)
- start_date: data de início no formato YYYY-MM-DD (se mencionada)
- NÃO inclua campos de progresso (actual_progress, expected_progress) - serão calculados pelo sistema
- Se dados não foram fornecidos, omita os campos (mas sempre inclua percentage se disponível)
- Se usuário não forneceu cronograma, retorne has_cronograma_data: false"""

            # Format messages
            conversation_lines = []
            for msg in messages[-20:]:  # Last 20 messages
                if isinstance(msg, dict):
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                elif hasattr(msg, 'type'):
                    role = "user" if msg.type == "human" else "assistant" if msg.type == "ai" else "system"
                    content = msg.content if hasattr(msg, 'content') else ''
                else:
                    continue

                conversation_lines.append(f"{role}: {content}")

            extract_prompt = "Conversa:\n" + "\n".join(conversation_lines)

            extract_messages = [
                {"role": "system", "content": extract_system},
                {"role": "user", "content": extract_prompt}
            ]

            response = await self.llm.ainvoke(extract_messages)
            content = response.content.strip()

            # Parse JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return None

            extracted_data = json.loads(json_match.group())

            if not extracted_data.get('has_cronograma_data', False):
                logger.info("No cronograma data found in conversation")
                return None

            activities = extracted_data.get('activities', {})
            if not activities:
                return None

            logger.info(f"Extracted {len(activities)} activities from cronograma")
            return activities

        except Exception as e:
            logger.error(f"Error extracting cronograma from conversation: {str(e)}", exc_info=True)
            return None

    def _evaluate_activity_schedule(self, activity_name: str, activity_data: Dict[str, Any], current_date: date) -> Dict[str, Any]:
        """Evaluate schedule expectations for a single activity on a given date."""
        evaluation = {
            'expected_progress': 0.0,
            'status': activity_data.get('status', 'não_iniciada'),
            'start_date': None,
            'end_date': None,
            'has_started': False,
            'is_overdue': False
        }

        start_date_str = activity_data.get('start_date')
        raw_duration = activity_data.get('duration_days', activity_data.get('duration'))

        try:
            duration_days = float(raw_duration) if raw_duration not in (None, '') else None
        except (TypeError, ValueError):
            duration_days = None

        if start_date_str and duration_days and duration_days > 0:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                calendar_duration = max(1, int(round(duration_days * 1.4)))
                end_date = start_date + timedelta(days=calendar_duration)

                evaluation['start_date'] = start_date
                evaluation['end_date'] = end_date

                if current_date >= end_date:
                    evaluation['expected_progress'] = 100.0
                    evaluation['status'] = 'deveria_estar_concluída'
                    evaluation['has_started'] = True
                    evaluation['is_overdue'] = current_date > end_date
                elif current_date >= start_date:
                    total_days = max(1, (end_date - start_date).days)
                    days_elapsed = max(0, (current_date - start_date).days)
                    expected = (days_elapsed / total_days) * 100
                    evaluation['expected_progress'] = round(min(100.0, expected), 2)
                    evaluation['status'] = 'em_andamento'
                    evaluation['has_started'] = True
                else:
                    evaluation['expected_progress'] = 0.0
                    evaluation['status'] = 'não_iniciada'
            except ValueError:
                logger.warning(
                    f"⚠️  Formato de data inválido para {activity_name}: {start_date_str}")
        else:
            # Fall back to existing values if schedule data is incomplete
            evaluation['expected_progress'] = float(activity_data.get('expected_progress', 0.0))
            evaluation['status'] = activity_data.get('status', 'não_iniciada')

        evaluation['expected_progress'] = round(max(0.0, min(100.0, evaluation['expected_progress'])), 2)
        return evaluation

    def _recalculate_cronograma_summary(self, cronograma: Dict[str, Any], current_date: date) -> Dict[str, Any]:
        """Recalculate aggregated cronograma metrics and update activity schedule metadata."""
        activities = cronograma.get('activities', {}) or {}

        total_expected_progress = 0.0
        total_actual_progress = 0.0
        total_weight_completed = 0.0
        total_weight_in_progress = 0.0

        for activity_name, activity_data in activities.items():
            if not isinstance(activity_data, dict):
                continue

            evaluation = self._evaluate_activity_schedule(activity_name, activity_data, current_date)
            activity_data['expected_progress'] = evaluation['expected_progress']
            activity_data['status'] = evaluation['status']
            activity_data['has_started'] = evaluation['has_started']
            activity_data['is_overdue'] = evaluation['is_overdue']
            activity_data['last_expected_update'] = current_date.isoformat()

            if evaluation['end_date']:
                activity_data['end_date'] = evaluation['end_date'].isoformat()

            has_detection = bool(activity_data.get('history')) or bool(activity_data.get('last_detected'))
            baseline_progress = evaluation['expected_progress']
            raw_actual = activity_data.get('actual_progress')

            if has_detection and raw_actual is not None:
                try:
                    actual_progress = float(raw_actual)
                except (TypeError, ValueError):
                    actual_progress = baseline_progress
            else:
                # Enquanto não há imagens, o progresso real segue o esperado
                actual_progress = baseline_progress
                activity_data['actual_progress'] = round(actual_progress, 2)
                activity_data.setdefault('baseline_synced_at', current_date.isoformat())

            actual_progress = max(0.0, min(100.0, actual_progress))
            activity_data['actual_progress'] = round(actual_progress, 2)

            weight = float(activity_data.get('percentage', 0.0))

            total_actual_progress += (weight / 100.0) * activity_data['actual_progress']
            total_expected_progress += (weight / 100.0) * evaluation['expected_progress']

            if evaluation['status'] == 'deveria_estar_concluída':
                total_weight_completed += weight
            elif evaluation['status'] == 'em_andamento':
                total_weight_in_progress += weight

        total_weight_remaining = max(0.0, 100.0 - total_weight_completed - total_weight_in_progress)

        summary = {
            'total_weight_completed': round(total_weight_completed, 2),
            'total_weight_in_progress': round(total_weight_in_progress, 2),
            'total_weight_remaining': round(total_weight_remaining, 2),
            'expected_progress_until_today': round(total_expected_progress, 2),
            'actual_progress': round(total_actual_progress, 2),
            'variance': round(total_actual_progress - total_expected_progress, 2),
            'reference_date': current_date.isoformat()
        }

        return summary

    async def _save_cronograma_to_project(self, project_id: str, cronograma_data: Dict[str, Any]) -> bool:
        """
        Save cronograma data to project metadata and calculate expected progress

        Args:
            project_id: Project UUID string
            cronograma_data: Dictionary with activity names and full data (percentage, dates, duration)

        Returns:
            True if saved successfully
        """
        try:
            if not self.project_repository:
                logger.warning("No project_repository available to save cronograma")
                return False

            from infrastructure.database.project_models import ConstructionProjectModel
            from infrastructure.timezone_utils import now_brazil
            from infrastructure.timezone_utils import now_brazil

            # Find project in MongoDB
            doc = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == project_id
            )

            if not doc:
                logger.warning(f"Project not found: {project_id}")
                return False

            # Update metadata with cronograma
            if not doc.metadata:
                doc.metadata = {}

            current_date = now_brazil().date()
            logger.info(f"📅 Data atual (Brasil): {current_date}")
            logger.info("📊 Calculando progresso esperado e real considerando o cronograma vigente...")

            cronograma_struct = doc.metadata.get('cronograma', {})
            cronograma_struct['activities'] = cronograma_data

            summary = self._recalculate_cronograma_summary(cronograma_struct, current_date)
            cronograma_struct['summary'] = summary
            cronograma_struct['updated_at'] = datetime.utcnow().isoformat()
            cronograma_struct['calculated_at'] = current_date.isoformat()

            doc.metadata['cronograma'] = cronograma_struct
            doc.overall_progress = summary['actual_progress']

            logger.info("\n📊 RESUMO DO CRONOGRAMA ATUALIZADO:")
            logger.info(f"   Peso total concluído: {summary['total_weight_completed']:.2f}%")
            logger.info(f"   Peso em andamento: {summary['total_weight_in_progress']:.2f}%")
            logger.info(f"   Progresso esperado até hoje: {summary['expected_progress_until_today']:.2f}%")
            logger.info(f"   Progresso real consolidado: {summary['actual_progress']:.2f}%")
            logger.info(f"   Variância acumulada: {summary['variance']:.2f}%")

            # Save to MongoDB
            await doc.save()

            logger.info(f"✅ Cronograma saved to project {project_id} metadata")
            logger.info(f"   Activities: {list(cronograma_data.keys())}")
            logger.info(f"   Overall Progress (real): {doc.overall_progress}%")

            return True

        except Exception as e:
            logger.error(f"Error saving cronograma to project {project_id}: {str(e)}", exc_info=True)
            return False

    async def _update_cronograma_from_analysis(
        self,
        project_id: str,
        activity: str,
        progress_percentage: float
    ) -> bool:
        """
        Update activity percentage in cronograma metadata based on image analysis

        Args:
            project_id: Project UUID string
            activity: Activity name (normalized, e.g., "alvenaria")
            progress_percentage: Progress percentage detected (0-100)

        Returns:
            True if updated successfully
        """
        try:
            from infrastructure.database.project_models import ConstructionProjectModel

            # Find project in MongoDB
            doc = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == project_id
            )

            if not doc:
                logger.warning(f"Project not found: {project_id}")
                return False

            # Initialize metadata if needed
            if not doc.metadata:
                doc.metadata = {}

            # Initialize cronograma if needed
            if 'cronograma' not in doc.metadata:
                doc.metadata['cronograma'] = {
                    'activities': {},
                    'updated_at': datetime.utcnow().isoformat()
                }

            # Get current cronograma
            cronograma = doc.metadata['cronograma']
            activities = cronograma.get('activities', {})

            logger.info(f"📋 Cronograma tem {len(activities)} atividades cadastradas")
            logger.info(f"🔎 Procurando atividade '{activity}' no cronograma...")

            # Handle both old format (float) and new format (dict)
            activity_data = activities.get(activity)

            if isinstance(activity_data, dict):
                current_timestamp = now_brazil()
                reference_date = current_timestamp.date()

                activity_weight = activity_data.get('percentage', 0)
                current_percentage = float(activity_data.get('actual_progress', 0))
                logger.info(f"✅ Atividade '{activity}' encontrada no cronograma:")
                logger.info(f"   Peso no projeto: {activity_weight}%")
                logger.info(f"   Progresso atual: {current_percentage}%")
                logger.info(f"   Progresso detectado: {progress_percentage}%")

                evaluation = self._evaluate_activity_schedule(activity, activity_data, reference_date)
                detected_progress = max(0.0, min(100.0, float(progress_percentage)))
                note = 'applied'

                if evaluation['start_date'] and not evaluation['has_started']:
                    logger.info(
                        f"⏸️  Atualização ignorada: atividade '{activity}' ainda não iniciou (início previsto: {evaluation['start_date']})."
                    )
                    history_entry = {
                        'timestamp': current_timestamp.isoformat(),
                        'detected_progress': round(detected_progress, 2),
                        'previous_progress': round(current_percentage, 2),
                        'applied_progress': round(current_percentage, 2),
                        'expected_progress_until_today': evaluation['expected_progress'],
                        'status_on_detection': evaluation['status'],
                        'note': 'ignored_before_schedule'
                    }
                    activity_history = activity_data.setdefault('history', [])
                    activity_history.append(history_entry)
                    if len(activity_history) > 20:
                        activity_data['history'] = activity_history[-20:]
                    cronograma['activities'] = activities
                    doc.metadata['cronograma'] = cronograma
                    await doc.save()
                    return False

                previous_progress = current_percentage
                applied_percentage = detected_progress

                if detected_progress > previous_progress:
                    note = 'increase'
                elif detected_progress < previous_progress:
                    note = 'decrease'
                else:
                    note = 'unchanged'

                activity_data['actual_progress'] = round(applied_percentage, 2)
                activity_data['last_detected'] = current_timestamp.isoformat()

                if evaluation['is_overdue'] and applied_percentage < 100.0:
                    note = f'{note}_after_deadline'
                    logger.warning(
                        f"⚠️  Atualizando '{activity}' com {applied_percentage}% após prazo previsto (fim: {evaluation['end_date']})."
                    )

                logger.info(
                    f"📈 Updated activity '{activity}': {previous_progress}% → {activity_data['actual_progress']}%"
                )

                history_entry = {
                    'timestamp': current_timestamp.isoformat(),
                    'detected_progress': round(detected_progress, 2),
                    'previous_progress': round(previous_progress, 2),
                    'applied_progress': round(applied_percentage, 2),
                    'expected_progress_until_today': evaluation['expected_progress'],
                    'status_on_detection': evaluation['status'],
                    'note': note
                }

                if evaluation.get('start_date'):
                    history_entry['start_date'] = evaluation['start_date'].isoformat()
                if evaluation.get('end_date'):
                    history_entry['end_date'] = evaluation['end_date'].isoformat()
                if evaluation.get('is_overdue'):
                    history_entry['is_overdue'] = evaluation['is_overdue']

                activity_history = activity_data.setdefault('history', [])
                activity_history.append(history_entry)
                if len(activity_history) > 20:
                    activity_data['history'] = activity_history[-20:]

                activities[activity] = activity_data
                cronograma['activities'] = activities

                summary = self._recalculate_cronograma_summary(cronograma, reference_date)
                cronograma['summary'] = summary
                cronograma['updated_at'] = current_timestamp.isoformat()
                cronograma['calculated_at'] = summary['reference_date']

                doc.metadata['cronograma'] = cronograma
                doc.overall_progress = summary['actual_progress']

                logger.info(f"📊 Resumo atualizado: esperado {summary['expected_progress_until_today']:.2f}% | real {summary['actual_progress']:.2f}% | variância {summary['variance']:.2f}%")

                await doc.save()
                logger.info(f"✅ Cronograma updated for project {project_id}")
                return True
            else:
                # Activity not found in cronograma
                logger.warning(f"⚠️ Atividade '{activity}' NÃO encontrada no cronograma cadastrado!")
                logger.warning(f"   Atividades disponíveis no cronograma: {list(activities.keys())[:5]}...")
                logger.warning(f"   Esta detecção será IGNORADA. Para considerar, adicione '{activity}' ao cronograma.")
                logger.warning(f"   Progresso detectado na imagem ({progress_percentage}%) não será aplicado ao total.")

                # Não cria entrada arbitrária - apenas loga o aviso
                # O progresso só deve ser atualizado para atividades que estão no cronograma
                return False

        except Exception as e:
            logger.error(f"Error updating cronograma from analysis: {str(e)}", exc_info=True)
            return False

    async def _generate_final_response(self, state: AgentState) -> str:
        """Generate final response using LLM"""
        # Check if onboarding is needed
        task_details = state['context'].get('task_details', {})
        if task_details.get('needs_onboarding', False):
            # Return onboarding welcome message WITH conversation history
            # Extract user input from last user message
            user_input = ''
            for msg in reversed(state['messages']):
                if isinstance(msg, dict):
                    if msg.get('role') == 'user':
                        user_input = msg.get('content', '')
                        break
                elif hasattr(msg, 'type') and msg.type == 'human':
                    user_input = msg.content
                    break

            # Get project information from task_details
            has_existing_projects = task_details.get('has_existing_projects', False)
            project_list = task_details.get('project_list', 'Nenhum')

            onboarding_prompt = self.prompt_manager.get_prompt(
                'supervisor',
                'onboarding_welcome_prompt',
                user_input=user_input,
                has_existing_projects=str(has_existing_projects),
                project_list=project_list
            )

            # IMPORTANT: Fetch COMPLETE history from MongoDB instead of trusting state
            messages = []

            # Add system message with onboarding prompt
            messages.append({"role": "system", "content": onboarding_prompt})

            # Fetch complete history from MongoDB if we have session_id
            if self.current_session_id:
                logger.info(f"🔍 Fetching complete conversation history from MongoDB for session {self.current_session_id}")
                mongo_history = await self._get_session_messages(self.current_session_id, limit=60)
                logger.info(f"📥 Fetched {len(mongo_history)} messages from MongoDB")
                for i, msg in enumerate(mongo_history):
                    logger.info(f"   MongoDB [{i}] {msg['role']}: {msg['content'][:80]}...")
                messages.extend(mongo_history)
            else:
                logger.warning("⚠️ No session_id - using state messages (may be incomplete)")
                # Fallback to state messages if no session_id
                for msg in state['messages']:
                    if isinstance(msg, dict):
                        messages.append(msg)
                    elif hasattr(msg, 'type'):
                        # Convert LangChain message to dict
                        messages.append({
                            "role": "assistant" if msg.type == "ai" else "user" if msg.type == "human" else "system",
                            "content": msg.content
                        })

            # Log final message count being sent to LLM
            logger.info(f"📤 Sending {len(messages)} messages to LLM for onboarding response")
            for i, msg in enumerate(messages):
                logger.info(f"   LLM Input [{i}] {msg['role']}: {msg['content'][:80]}...")

            # DETECTION: Check if we should force project creation
            # Look for pattern: Assistant asked "Posso cadastrar?" + User confirmed
            should_force_creation = False
            if len(messages) >= 2:
                # Get last 2 non-system messages
                last_msgs = [m for m in messages if m['role'] != 'system'][-2:]
                if len(last_msgs) >= 2:
                    assistant_msg = last_msgs[-2].get('content', '').lower()
                    user_msg = last_msgs[-1].get('content', '').lower()

                    # Check if assistant asked for confirmation
                    asked_confirmation = any(phrase in assistant_msg for phrase in [
                        'posso cadastrar', 'pode cadastrar', 'cadastrar a obra',
                        'confirmar', 'está correto'
                    ])

                    # Check if user confirmed
                    user_confirmed = any(word in user_msg for word in [
                        'sim', 'pode', 'ok', 'isso', 'confirma', 'confirmar',
                        'yes', 'certo', 'correto', 'vai', 'vamos'
                    ])

                    should_force_creation = asked_confirmation and user_confirmed

                    if should_force_creation:
                        logger.info(f"🔍 Detected confirmation pattern - forcing project creation")
                        logger.info(f"  Assistant asked: '{assistant_msg[:100]}...'")
                        logger.info(f"  User confirmed: '{user_msg}'")

            try:
                # If we detected confirmation, skip LLM and create project directly
                if should_force_creation and not state.get('project_id'):
                    logger.info("⚡ Skipping LLM - creating project immediately after confirmation")

                    # Try to create project from conversation
                    created_project_id = await self._try_create_project_from_conversation(state['messages'])

                    if created_project_id:
                        logger.info(f"✅ Project created after confirmation: {created_project_id}")
                        state['project_id'] = created_project_id
                        response_text = f"""✅ Obra cadastrada com sucesso!

Você possui um cronograma de atividades com percentuais de andamento? Se sim, pode compartilhar os percentuais das atividades já executadas?"""
                    else:
                        logger.error("❌ Failed to create project after confirmation")
                        response_text = "Ops! Tive um problema ao cadastrar o projeto. Vamos tentar novamente. Qual o nome da obra?"

                    return response_text

                # Normal flow: Generate response with LLM
                response = await self.llm.ainvoke(messages)
                response_text = response.content

                # Check if response contains the marker to create project
                if '[CADASTRAR_PROJETO]' in response_text:
                    # Remove marker from response first
                    response_text = response_text.replace('[CADASTRAR_PROJETO]', '')

                    # Check if project was already created in this session (prevent duplicates)
                    if state.get('project_id'):
                        logger.info(f"Project already created in this session: {state['project_id']} - skipping duplicate creation")
                    else:
                        logger.info("Detected [CADASTRAR_PROJETO] marker - attempting to create project")

                        # Try to create project from conversation
                        created_project_id = await self._try_create_project_from_conversation(state['messages'])

                        # If project was created, ask about cronograma
                        if created_project_id:
                            logger.info(f"✅ Project created during onboarding: {created_project_id}")
                            # Update state with project_id for session update
                            state['project_id'] = created_project_id
                            # Append confirmation and cronograma question
                            response_text += f"""\n\n✅ Obra cadastrada com sucesso!

Você possui um cronograma de atividades com percentuais de andamento? Se sim, pode compartilhar os percentuais das atividades já executadas?"""
                        else:
                            logger.warning("Failed to create project - technical issue or insufficient data")
                            # Don't add fallback message - let the LLM response speak for itself
                            # If it reached [CADASTRAR_PROJETO], LLM already has the info and will handle it

                # Check if response contains the marker to save cronograma
                if '[SALVAR_CRONOGRAMA]' in response_text:
                    # Remove marker from response first
                    response_text = response_text.replace('[SALVAR_CRONOGRAMA]', '')

                    if state.get('project_id'):
                        logger.info("Detected [SALVAR_CRONOGRAMA] marker - attempting to extract and save cronograma")

                        # Try to extract cronograma from conversation
                        cronograma_data = await self._extract_cronograma_from_conversation(state['messages'])

                        if cronograma_data:
                            # Save cronograma to project metadata
                            saved = await self._save_cronograma_to_project(state['project_id'], cronograma_data)

                            if saved:
                                logger.info(f"✅ Cronograma saved for project {state['project_id']}")

                                # Also create/update timeline schedule
                                schedule_created = await self._create_schedule_from_activities(
                                    state['project_id'],
                                    cronograma_data
                                )

                                if schedule_created:
                                    logger.info(f"✅ Timeline schedule created for project {state['project_id']}")
                                    response_text += f"\n\n✅ **Cronograma salvo com sucesso!** {len(cronograma_data)} atividades cadastradas e timeline criada.\n\nQual o engenheiro responsável pela obra?"
                                else:
                                    response_text += f"\n\n✅ **Cronograma salvo!** {len(cronograma_data)} atividades cadastradas.\n\nQual o engenheiro responsável pela obra?"
                            else:
                                logger.warning("Failed to save cronograma to database")
                        else:
                            logger.warning("Failed to extract cronograma from conversation")
                    else:
                        logger.warning("Cannot save cronograma - no project_id in state")

                return response_text
            except Exception as e:
                logger.error(f"Error generating onboarding message: {str(e)}")
                return "Olá! Vejo que você ainda não tem nenhum projeto cadastrado. Vamos começar! Me conta um pouco sobre o que você gostaria de analisar ou acompanhar?"

        synthesis = state['results'].get('synthesis', {})
        conversation_history = state['context'].get('conversation_history', [])

        # Build context from conversation history
        context_text = ""
        if conversation_history:
            context_text = "\n\nContexto da conversa anterior:\n"
            for msg in conversation_history[-3:]:  # Include last 3 messages for context
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:150]  # Limit content length
                role_display = "Usuário" if role == "user" else "Assistente" if role == "assistant" else role
                context_text += f"- {role_display}: {content}\n"

        # Get prompts from centralized YAML
        system_msg = self.prompt_manager.get_prompt('supervisor', 'final_response_system')
        user_prompt = self.prompt_manager.get_prompt(
            'supervisor',
            'final_response_prompt',
            context_history=context_text,
            summary=synthesis.get('summary', 'Análise realizada'),
            key_findings=str(synthesis.get('key_findings', [])),
            recommendations=str(synthesis.get('recommendations', [])),
            next_steps=str(synthesis.get('next_steps', [])),
            errors=str(state.get('errors', []))
        )

        # Include conversation history in the messages for the LLM
        messages = [
            {"role": "system", "content": system_msg}
        ]

        # Add limited conversation history to maintain context
        if conversation_history:
            for msg in conversation_history[-2:]:  # Include last 2 messages
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')[:300]  # Limit content length
                })

        messages.append({"role": "user", "content": user_prompt})

        response = await self.llm.ainvoke(messages)
        return response.content

    def _format_response(self, state: AgentState) -> Dict[str, Any]:
        """Format final response for API"""
        response = {
            'success': len(state['errors']) == 0,
            'results': state['results'],
            'messages': state['messages'],
            'errors': state['errors'],
            'completed': state['completed'],
            'metadata': {
                'agents_used': self._get_agents_used(state),
                'processing_time': datetime.utcnow().isoformat()
            }
        }

        # Include project_id if it was created/updated during processing
        if state.get('project_id'):
            response['project_id'] = state['project_id']
            response['metadata']['project_created'] = True

        return response

    def _get_agents_used(self, state: AgentState) -> List[str]:
        """Get list of agents that were used"""
        agents = []
        if 'visual' in state['results']:
            agents.append('visual')
        if 'document' in state['results']:
            agents.append('document')
        if 'progress' in state['results']:
            agents.append('progress')
        if 'report' in state['results']:
            agents.append('report')
        return agents

    async def _create_schedule_from_activities(self, project_id: str, activities: Dict[str, Any]) -> bool:
        """
        Create or update project schedule from extracted activities

        Args:
            project_id: Project UUID
            activities: Dict with activity names and their data (percentage, duration_days, start_date)

        Returns:
            True if schedule created successfully
        """
        try:
            from infrastructure.database.project_models import (
                ProjectScheduleModel,
                ProjectMilestone,
                MilestoneStatus,
                ConstructionPhase
            )
            from datetime import datetime, timedelta

            logger.info(f"Creating schedule for project {project_id} with {len(activities)} activities")

            # Get project
            from infrastructure.database.project_models import ConstructionProjectModel
            project = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == project_id
            )

            if not project:
                logger.warning(f"Project {project_id} not found")
                return False

            # Map activity names to construction phases
            phase_mapping = {
                'prumada': ConstructionPhase.FOUNDATION,
                'alvenaria': ConstructionPhase.MASONRY,
                'contramarco': ConstructionPhase.STRUCTURE,
                'instalacoes_hidraulicas': ConstructionPhase.PLUMBING,
                'infra_eletrica': ConstructionPhase.ELECTRICAL,
                'fiacao': ConstructionPhase.ELECTRICAL,
                'caixinhas_eletricas': ConstructionPhase.ELECTRICAL,
                'argamassa_am': ConstructionPhase.MASONRY,
                'contrapiso': ConstructionPhase.FINISHING,
                'impermeabilizacao': ConstructionPhase.ROOFING,
                'protecao_mecanica': ConstructionPhase.ROOFING,
                'guarda_corpo': ConstructionPhase.FINISHING,
                'capa_peitoril': ConstructionPhase.FINISHING,
                'gesso_emboco': ConstructionPhase.FINISHING,
                'guias_montantes_drywall': ConstructionPhase.FINISHING,
                'instalacoes_eletricas_drywall': ConstructionPhase.ELECTRICAL,
                'drywall_fechamento': ConstructionPhase.FINISHING,
                'ceramica_soleira': ConstructionPhase.FINISHING,
                'forro': ConstructionPhase.FINISHING,
                'caixilhos': ConstructionPhase.FINISHING,
                'massa_paredes': ConstructionPhase.FINISHING,
                'demao_pintura_fundo': ConstructionPhase.PAINTING,
                'portas_madeira': ConstructionPhase.FINISHING,
                'loucas_metais': ConstructionPhase.FINISHING,
                'desengrosso': ConstructionPhase.FINISHING,
                'pintura_final': ConstructionPhase.PAINTING,
                'limpeza_final': ConstructionPhase.CLEANUP,
                'comunicacao_visual': ConstructionPhase.CLEANUP
            }

            # Get project start date or use today
            project_start = project.start_date or datetime.utcnow()
            current_date = project_start

            # Create milestones from activities
            milestones = []
            for activity_name, activity_data in activities.items():
                # Get duration (default to 7 days if not specified)
                duration_days = activity_data.get('duration_days', 7)

                # Calculate dates
                if activity_data.get('start_date'):
                    try:
                        start_date = datetime.fromisoformat(activity_data['start_date'])
                    except:
                        start_date = current_date
                else:
                    start_date = current_date

                end_date = start_date + timedelta(days=duration_days)

                # Get phase
                phase = phase_mapping.get(activity_name, ConstructionPhase.STRUCTURE)

                # Create milestone
                milestone = ProjectMilestone(
                    name=activity_name.replace('_', ' ').title(),
                    description=f"Etapa: {activity_name}",
                    phase=phase,
                    planned_start=start_date,
                    planned_end=end_date,
                    status=MilestoneStatus.PENDING,
                    progress_percentage=0.0,
                    dependencies=[],
                    notes=f"Peso no cronograma: {activity_data.get('percentage', 0)}%"
                )

                milestones.append(milestone)
                current_date = end_date  # Next activity starts after this one

            # Calculate project end date
            if milestones:
                project_end = max(m.planned_end for m in milestones)
            else:
                project_end = project_start + timedelta(days=180)  # Default 6 months

            # Check if schedule exists
            existing_schedule = await ProjectScheduleModel.find_one(
                ProjectScheduleModel.project_id == project_id
            )

            if existing_schedule:
                # Update existing
                existing_schedule.milestones = milestones
                existing_schedule.project_start = project_start
                existing_schedule.project_end = project_end
                existing_schedule.updated_at = datetime.utcnow()
                await existing_schedule.save()
                logger.info(f"✅ Updated schedule for project {project_id} with {len(milestones)} milestones")
            else:
                # Create new
                schedule = ProjectScheduleModel(
                    project_id=project_id,
                    name="Cronograma da Obra",
                    description="Cronograma gerado automaticamente a partir das informações fornecidas",
                    project_start=project_start,
                    project_end=project_end,
                    milestones=milestones,
                    overall_progress=0.0
                )
                await schedule.save()
                logger.info(f"✅ Created schedule for project {project_id} with {len(milestones)} milestones")

            return True

        except Exception as e:
            logger.error(f"Error creating schedule from activities: {str(e)}", exc_info=True)
            return False
