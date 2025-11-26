"""
Agent Factory
Factory pattern for creating and managing agents
Using latest LangChain and LangGraph versions
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain.memory import ConversationBufferMemory
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from infrastructure.config.settings import Settings
from infrastructure.llm_service import get_llm_service
from agents.visual_agent import VisualAgent
from agents.document_agent import DocumentAgent
from agents.progress_agent import ProgressAgent
from agents.report_agent import ReportAgent
from agents.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating and managing AI agents
    Implements latest LangChain (0.3.12) and LangGraph (0.2.63)
    """
    
    def __init__(self, settings: Settings, storage_service = None):
        """Initialize agent factory"""
        self.settings = settings
        self.storage_service = storage_service
        self.is_initialized = False
        self.agents: Dict[str, Any] = {}
        self.llm = None
        self.vision_llm = None
        self.memory_saver = None
        self.agent_config = None
        self.llm_service = get_llm_service()
        
    async def initialize(self):
        """Initialize all agents and models"""
        try:
            logger.info("Initializing Agent Factory with latest LangChain/LangGraph...")
            
            # Load agent configuration
            self.agent_config = await self._load_agent_config()
            
            # Initialize LLMs using LLM Service (supports OpenRouter)
            self.llm = self.llm_service.get_llm(model_type="chat")
            self.vision_llm = self.llm_service.get_llm(model_type="vision")

            # Log model configuration
            model_info = self.llm_service.get_model_info()
            logger.info(f"Using {model_info['provider']} with model: {model_info['model']}")
            
            # Initialize memory saver for LangGraph
            self.memory_saver = MemorySaver()
            
            # Create specialized agents
            await self._create_agents()
            
            # Create supervisor with LangGraph
            await self._create_supervisor()
            
            self.is_initialized = True
            logger.info("Agent Factory initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent Factory: {str(e)}")
            raise
    
    async def _load_agent_config(self) -> Dict[str, Any]:
        """Load agent configuration from JSON"""
        config_path = Path("backend/config/agent_config.json")
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Return default configuration
            return {
                "locations": {
                    "location_1": {
                        "name": "Área Externa - Fachada",
                        "description": "Fachada principal e área externa"
                    },
                    "location_2": {
                        "name": "Área Interna - Principal",
                        "description": "Ambiente interno principal"
                    },
                    "location_3": {
                        "name": "Área Técnica",
                        "description": "Áreas técnicas e instalações"
                    }
                },
                "construction_phases": {
                    "foundation": {"name": "Fundação"},
                    "structure": {"name": "Estrutura"},
                    "masonry": {"name": "Alvenaria"},
                    "installations": {"name": "Instalações"},
                    "finishing": {"name": "Acabamento"}
                },
                "prompts": {
                    "initial_interview": {
                        "system_prompt": "Você é um especialista em obras..."
                    }
                }
            }
    
    async def _create_agents(self):
        """Create specialized agents"""
        try:
            # Visual Agent with GPT-4 Vision
            visual_config = {
                **self.settings.agent_config["visual_config"],
                "llm": self.vision_llm,
                "phases": self.agent_config.get("construction_phases", {})
            }
            self.agents["visual"] = VisualAgent(visual_config)
            
            # Document Agent
            document_config = {
                **self.settings.agent_config["document_config"],
                "llm": self.llm
            }
            self.agents["document"] = DocumentAgent(document_config)
            
            # Progress Agent
            progress_config = {
                **self.settings.agent_config["progress_config"],
                "llm": self.llm
            }
            self.agents["progress"] = ProgressAgent(progress_config)
            
            # Report Agent
            report_config = {
                **self.settings.agent_config["report_config"],
                "llm": self.llm
            }
            self.agents["report"] = ReportAgent(report_config)
            
            logger.info("Specialized agents created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create agents: {str(e)}")
            raise
    
    async def _create_supervisor(self):
        """Create supervisor agent with LangGraph"""
        try:
            supervisor_config = {
                "llm": self.llm,
                "model": self.settings.chat_model,
                "temperature": self.settings.temperature,
                "visual_config": {
                    **self.settings.agent_config["visual_config"],
                    "llm": self.vision_llm,
                    "phases": self.agent_config.get("construction_phases", {})
                },
                "document_config": {
                    **self.settings.agent_config["document_config"],
                    "llm": self.llm
                },
                "progress_config": {
                    **self.settings.agent_config["progress_config"],
                    "llm": self.llm
                },
                "report_config": {
                    **self.settings.agent_config["report_config"],
                    "llm": self.llm
                },
                "project_repository": None,  # Will be injected later
                "storage_service": self.storage_service
            }
            
            self.agents["supervisor"] = SupervisorAgent(supervisor_config)
            
            logger.info("Supervisor agent created with LangGraph orchestration")
            
        except Exception as e:
            logger.error(f"Failed to create supervisor: {str(e)}")
            raise
    
    def get_agent(self, agent_type: str) -> Any:
        """Get specific agent by type"""
        if agent_type not in self.agents:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return self.agents[agent_type]
    
    def get_supervisor(self) -> SupervisorAgent:
        """Get supervisor agent"""
        return self.agents.get("supervisor")
    
    async def create_chat_chain(self, session_id: str) -> Any:
        """Create a chat chain with memory using LangChain 0.3.12"""
        try:
            # Create memory
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=self.agent_config["prompts"]["initial_interview"]["system_prompt"]),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessage(content="{input}")
            ])
            
            # Create chain using LCEL (LangChain Expression Language)
            chain = prompt | self.llm | JsonOutputParser()
            
            return {
                "chain": chain,
                "memory": memory,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Failed to create chat chain: {str(e)}")
            raise
    
    async def create_langgraph_workflow(self, workflow_type: str = "comprehensive") -> StateGraph:
        """Create a LangGraph workflow for complex multi-agent tasks"""
        try:
            from typing import TypedDict, List
            
            # Define state schema
            class WorkflowState(TypedDict):
                messages: List[dict]
                current_agent: str
                results: dict
                next_action: str
                completed: bool
            
            # Create workflow
            workflow = StateGraph(WorkflowState)
            
            # Define agent nodes
            async def visual_node(state: WorkflowState) -> WorkflowState:
                """Visual analysis node"""
                visual_agent = self.agents["visual"]
                # Process with visual agent
                state["results"]["visual"] = "Visual analysis completed"
                state["next_action"] = "document" if workflow_type == "comprehensive" else "report"
                return state
            
            async def document_node(state: WorkflowState) -> WorkflowState:
                """Document processing node"""
                document_agent = self.agents["document"]
                # Process with document agent
                state["results"]["document"] = "Document processing completed"
                state["next_action"] = "progress"
                return state
            
            async def progress_node(state: WorkflowState) -> WorkflowState:
                """Progress analysis node"""
                progress_agent = self.agents["progress"]
                # Process with progress agent
                state["results"]["progress"] = "Progress analysis completed"
                state["next_action"] = "report"
                return state
            
            async def report_node(state: WorkflowState) -> WorkflowState:
                """Report generation node"""
                report_agent = self.agents["report"]
                # Process with report agent
                state["results"]["report"] = "Report generated"
                state["completed"] = True
                state["next_action"] = "end"
                return state
            
            # Add nodes to workflow
            workflow.add_node("visual", visual_node)
            workflow.add_node("document", document_node)
            workflow.add_node("progress", progress_node)
            workflow.add_node("report", report_node)
            
            # Define edges
            workflow.add_edge("visual", "document")
            workflow.add_edge("document", "progress")
            workflow.add_edge("progress", "report")
            workflow.add_edge("report", END)
            
            # Set entry point
            workflow.set_entry_point("visual")
            
            # Compile workflow with memory
            compiled = workflow.compile(checkpointer=self.memory_saver)
            
            return compiled
            
        except Exception as e:
            logger.error(f"Failed to create LangGraph workflow: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Cleanup agents
            self.agents.clear()
            
            # Clear memory
            if self.memory_saver:
                self.memory_saver = None
            
            self.is_initialized = False
            logger.info("Agent Factory cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about available agents"""
        return {
            "initialized": self.is_initialized,
            "available_agents": list(self.agents.keys()),
            "langchain_version": "0.3.12",
            "langgraph_version": "0.2.63",
            "llm_provider": self.llm_service.get_model_info()["provider"] if self.llm_service else "Not initialized",
            "models": {
                "chat": self.settings.chat_model,
                "vision": self.settings.vision_model
            },
            "features": [
                "Multi-agent orchestration",
                "GPT-4 Vision integration",
                "Conversational memory",
                "Workflow automation",
                "Document processing",
                "Progress tracking",
                "Report generation"
            ]
        }
