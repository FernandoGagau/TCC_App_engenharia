"""
Agente de Análise de Construção usando LangGraph
Sistema multi-agente para análise completa de obras
"""

from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence
from datetime import datetime
import operator
import yaml
import json
from pathlib import Path

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from domain.prompts import construction_prompts

import logging

logger = logging.getLogger(__name__)


from langgraph.graph import MessagesState
from langgraph.types import Command
from typing import Literal

class AgentState(MessagesState):
    """Estado compartilhado entre agentes - herda de MessagesState para melhor gestão de mensagens"""
    current_agent: str
    session_id: str
    project_data: Dict[str, Any]
    analysis_results: Dict[str, Any]
    next_action: Optional[str]
    metadata: Dict[str, Any]


class ConstructionAnalysisAgent:
    """Agente principal de análise de construção com LangGraph"""

    def __init__(self, config_path: str | Path | None = None):
        """Inicializa o agente com configurações"""
        if config_path is None:
            # Usa diretório config dentro de backend por padrão
            self.config_path = Path(__file__).resolve().parents[4] / "backend" / "config"
        else:
            self.config_path = Path(config_path)
        self.prompts = self._load_prompts()
        self.agent_config = self._load_agent_config()
        self.llm = self._initialize_llm()
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _load_prompts(self) -> Dict:
        """Carrega prompts do arquivo YAML"""
        prompts_file = self.config_path / "prompts.yaml"
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar prompts: {e}")
            return {}

    def _load_agent_config(self) -> Dict:
        """Carrega configuração dos agentes"""
        config_file = self.config_path / "agent_config.json"
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            return {}

    def _initialize_llm(self) -> ChatOpenAI:
        """Inicializa o modelo LLM"""
        from infrastructure.config.settings import Settings

        settings = Settings()

        return ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.chat_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            default_headers={
                "HTTP-Referer": settings.openrouter_app_url or "https://construction-agent.local",
                "X-Title": settings.openrouter_app_title or settings.app_name
            }
        )

    def _build_graph(self) -> StateGraph:
        """Constrói o grafo de agentes com LangGraph"""

        # Cria o grafo de estado
        workflow = StateGraph(AgentState)

        # Adiciona nós (agentes)
        workflow.add_node("supervisor", self.supervisor_agent)
        workflow.add_node("visual_analyst", self.visual_analysis_agent)
        workflow.add_node("progress_calculator", self.progress_calculation_agent)
        workflow.add_node("document_processor", self.document_processing_agent)
        workflow.add_node("report_generator", self.report_generation_agent)
        workflow.add_node("quality_inspector", self.quality_inspection_agent)

        # Define o ponto de entrada usando START (best practice)
        workflow.add_edge(START, "supervisor")

        # Não precisamos de edges condicionais pois usamos Command
        # Os agentes agora retornam Command com goto

        # Desabilita tracing explicitamente
        import os
        os.environ.pop('LANGCHAIN_TRACING', None)
        os.environ.pop('LANGCHAIN_TRACING_V2', None)

        # Compila o grafo
        # Nota: Para LangGraph Studio/Dev, não passamos checkpointer
        # pois o Studio gerencia isso automaticamente
        if os.getenv("LANGGRAPH_STUDIO", "false").lower() == "true":
            return workflow.compile()  # Sem checkpointer para Studio
        else:
            return workflow.compile(checkpointer=self.memory)  # Com checkpointer para produção

    def supervisor_agent(self, state: AgentState) -> Command[Literal["visual_analyst", "progress_calculator", "document_processor", "report_generator", "quality_inspector", END]]:
        """Agente supervisor que coordena outros agentes usando Command para melhor controle"""

        messages = state["messages"]
        last_message = messages[-1] if messages else None

        try:
            # Use proper prompts instead of mocked responses
            context_prompt = construction_prompts.get_prompt_for_context(last_message.content if last_message else "")

            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
                HumanMessage(content=context_prompt)
            ])

            # Get LLM response
            response = self.llm.invoke(prompt.format_messages(messages=messages))

            # For supervisor, we just return the response and go to END
            decision = "end"

        except Exception as e:
            logger.error(f"Erro ao chamar LLM no supervisor: {e}")
            # Em caso de erro, usa o LLM com prompt de fallback
            try:
                fallback_prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
                    HumanMessage(content=last_message.content if last_message else "Olá")
                ])
                response = self.llm.invoke(fallback_prompt.format_messages())
                decision = "end"
            except:
                # Last resort - return error message
                from langchain_core.messages import AIMessage
                response = AIMessage(content="Desculpe, estou com problemas técnicos. Por favor, tente novamente.")
                decision = "end"

        # Mapeia para o nome correto do nó
        node_map = {
            "visual_analysis": "visual_analyst",
            "progress_calculation": "progress_calculator",
            "document_processing": "document_processor",
            "report_generation": "report_generator",
            "quality_inspection": "quality_inspector",
            "end": END
        }

        next_node = node_map.get(decision, END)

        # Retorna Command para melhor controle de fluxo e estado
        # Sempre adiciona a resposta, mesmo quando vai para END
        messages_to_add = [response]

        return Command(
            goto=next_node,
            update={
                "messages": messages_to_add,
                "current_agent": "supervisor",
                "next_action": decision
            }
        )

    def visual_analysis_agent(self, state: AgentState) -> Command[Literal["supervisor"]]:
        """Agente especializado em análise visual"""

        # Use construction prompts for visual analysis
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        # Get appropriate prompt based on context
        context_prompt = construction_prompts.get_prompt_for_context(
            last_message.content if last_message else "análise visual"
        )

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            HumanMessage(content="Realize uma análise visual da construção com base nas informações fornecidas.")
        ])

        response = self.llm.invoke(prompt.format_messages(messages=messages))

        # Análise visual simulada (em produção, integraria com vision API)
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "phase_detected": "estrutura",
            "progress_percentage": 45,
            "quality_score": 8.5,
            "observations": response.content
        }

        return Command(
            goto="supervisor",
            update={
                "messages": [response],
                "current_agent": "visual_analyst",
                "analysis_results": {"visual": analysis}
            }
        )

    def progress_calculation_agent(self, state: AgentState) -> Command[Literal["supervisor"]]:
        """Agente calculador de progresso"""

        messages = state["messages"]

        # Use progress analysis prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            HumanMessage(content=construction_prompts.PROGRESS_ANALYSIS_PROMPT)
        ])

        response = self.llm.invoke(prompt.format_messages(messages=messages))

        # Use LLM response for progress analysis
        progress_data = {
            "overall_progress": 42,  # This would come from actual calculation
            "phase_progress": {
                "fundacao": 100,
                "estrutura": 70,
                "alvenaria": 30,
                "instalacoes": 10,
                "acabamento": 0
            },
            "timeline_status": "on_schedule",
            "analysis": response.content  # Always use the LLM response
        }

        return Command(
            goto="supervisor",
            update={
                "messages": [response],
                "current_agent": "progress_calculator",
                "analysis_results": {"progress": progress_data}
            }
        )

    def document_processing_agent(self, state: AgentState) -> Command[Literal["supervisor"]]:
        """Agente processador de documentos"""

        messages = state["messages"]

        # Use analysis prompt for documents
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            HumanMessage(content="Processe e analise os documentos fornecidos sobre a construção.")
        ])

        response = self.llm.invoke(prompt.format_messages(messages=messages))

        return Command(
            goto="supervisor",
            update={
                "messages": [response],
                "current_agent": "document_processor",
                "analysis_results": {"document": {"processed": True, "summary": response.content}}
            }
        )

    def report_generation_agent(self, state: AgentState) -> Command[Literal["supervisor"]]:
        """Agente gerador de relatórios"""

        messages = state["messages"]
        analysis = state.get("analysis_results", {})

        # Compila dados para o relatório
        report_context = f"""
        Dados de Análise Disponíveis:
        {json.dumps(analysis, indent=2, ensure_ascii=False)}
        """

        # Use report generation prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            HumanMessage(content=construction_prompts.REPORT_GENERATION_PROMPT),
            HumanMessage(content=f"Dados para o relatório: {report_context}")
        ])

        response = self.llm.invoke(prompt.format_messages(messages=messages))

        return Command(
            goto="supervisor",
            update={
                "messages": [response],
                "current_agent": "report_generator",
                "analysis_results": {"report": {"generated": True, "content": response.content}}
            }
        )

    def quality_inspection_agent(self, state: AgentState) -> Command[Literal["supervisor"]]:
        """Agente inspetor de qualidade"""

        messages = state["messages"]

        # Use quality inspection prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            HumanMessage(content=construction_prompts.QUALITY_INSPECTION_PROMPT)
        ])

        response = self.llm.invoke(prompt.format_messages(messages=messages))

        quality_data = {
            "score": 7.8,
            "issues": [],
            "recommendations": ["Verificar prumo da alvenaria", "Revisar impermeabilização"],
            "analysis": response.content
        }

        return Command(
            goto="supervisor",
            update={
                "messages": [response],
                "current_agent": "quality_inspector",
                "analysis_results": {"quality": quality_data}
            }
        )

    # Removido supervisor_decision - não é mais necessário com Command

    def _extract_decision(self, response: str) -> str:
        """Extrai a decisão do agente supervisor"""

        response_lower = response.lower()

        if "visual" in response_lower or "imagem" in response_lower or "foto" in response_lower:
            return "visual_analysis"
        elif "progress" in response_lower or "andamento" in response_lower:
            return "progress_calculation"
        elif "document" in response_lower or "arquivo" in response_lower:
            return "document_processing"
        elif "relat" in response_lower:
            return "report_generation"
        elif "qualidade" in response_lower or "quality" in response_lower:
            return "quality_inspection"
        else:
            return "end"

    def _generate_fallback_response(self, message_text: str) -> str:
        """Gera resposta de fallback usando o LLM em caso de erro"""
        try:
            # Use the prompts system to get appropriate context
            context_prompt = construction_prompts.get_prompt_for_context(message_text)

            # Create prompt with system and context
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=construction_prompts.SYSTEM_PROMPT),
                HumanMessage(content=message_text),
                HumanMessage(content=context_prompt)
            ])

            # Get LLM response
            response = self.llm.invoke(prompt.format_messages())
            return response.content

        except Exception as e:
            logger.error(f"Erro no fallback LLM: {e}")
            # Last resort static message
            return "Desculpe, estou com problemas técnicos. Por favor, tente novamente em alguns instantes."

    async def process_message(self, session_id: str, message: str,
                             attachments: List[Dict] = None) -> Dict[str, Any]:
        """Processa uma mensagem através do grafo de agentes"""

        # Prepara o estado inicial
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "current_agent": "supervisor",
            "session_id": session_id,
            "project_data": {},
            "analysis_results": {},
            "next_action": None,
            "metadata": {"attachments": attachments or []}
        }

        try:
            # Executa o grafo com limite de recursão
            config = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 5  # Reduz o limite para evitar loops
            }
            result = await self.graph.ainvoke(initial_state, config)

            # Extrai a resposta final - pega apenas mensagens do assistant, não do user
            messages = result.get("messages", [])

            # Debug logging
            logger.info(f"Total messages in result: {len(messages)}")
            for i, msg in enumerate(messages):
                msg_content = msg.content if hasattr(msg, 'content') else str(msg)
                logger.info(f"Message {i}: type={type(msg).__name__}, content={msg_content[:100] if msg_content else 'no content'}")

            # Filtra mensagens do assistant (AIMessage)
            from langchain_core.messages import AIMessage
            assistant_messages = [msg for msg in messages if isinstance(msg, AIMessage)]

            logger.info(f"Assistant messages found: {len(assistant_messages)}")

            # Pega a última mensagem do assistant que não seja "END"
            final_message = None
            for msg in reversed(assistant_messages):
                if msg.content and msg.content.strip() != "END":
                    final_message = msg
                    break

            # Se não encontrar mensagem válida, usa fallback com LLM
            if not final_message:
                final_response = self._generate_fallback_response(message)
            else:
                final_response = final_message.content

            return {
                "success": True,
                "response": final_response,
                "analysis_results": result.get("analysis_results", {}),
                "current_agent": result.get("current_agent", "supervisor"),
                "metadata": result.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "Desculpe, ocorreu um erro ao processar sua mensagem."
            }

    def get_agent_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o agente"""
        return {
            "name": self.prompts.get("system", {}).get("name", "Construction Agent"),
            "version": self.prompts.get("system", {}).get("version", "2.0.0"),
            "description": self.prompts.get("system", {}).get("description", ""),
            "agents": list(self.prompts.get("agents", {}).keys()),
            "capabilities": self.agent_config.get("capabilities", [])
        }

    def visualize_graph(self, output_path: str = "graph_visualization.png") -> str:
        """Visualiza o grafo de agentes e salva em arquivo"""
        try:
            # Método 1: Usar draw_mermaid para visualização em texto
            mermaid_graph = self.graph.draw_mermaid()

            # Salva o código Mermaid em arquivo
            with open("graph_mermaid.md", "w") as f:
                f.write("```mermaid\n")
                f.write(mermaid_graph)
                f.write("\n```")

            # Método 2: Usar draw_png para imagem (requer graphviz)
            try:
                png_data = self.graph.draw_png()
                with open(output_path, "wb") as f:
                    f.write(png_data)
                logger.info(f"Grafo salvo em: {output_path}")
            except Exception as e:
                logger.warning(f"Não foi possível gerar PNG (instale graphviz): {e}")

            return mermaid_graph

        except Exception as e:
            logger.error(f"Erro ao visualizar grafo: {e}")
            return ""

    def get_graph_ascii(self) -> str:
        """Retorna representação ASCII do grafo"""
        try:
            # Representação simples do fluxo
            ascii_graph = """
    ╔════════════════════════════════════════════╗
    ║          SUPERVISOR AGENT                  ║
    ╚════════════════════════════════════════════╝
                    │
        ┌───────────┼───────────┬───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Visual  │ │Progress │ │Document │ │ Report  │ │Quality  │
    │Analysis │ │  Calc   │ │Process  │ │  Gen    │ │Inspect  │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
        │           │           │           │           │
        └───────────┴───────────┴───────────┴───────────┘
                            ▼
                    ╔════════════╗
                    ║ SUPERVISOR ║
                    ╚════════════╝
                            │
                            ▼
                        [ END ]
            """
            return ascii_graph
        except Exception as e:
            logger.error(f"Erro ao gerar ASCII: {e}")
            return ""
