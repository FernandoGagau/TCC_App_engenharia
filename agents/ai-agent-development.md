# AI Agent Development Agent

## Overview

The AI Agent Development Agent specializes in implementing and orchestrating LangGraph/LangChain-based AI agents for the Construction Analysis AI System. This agent provides guidance on multi-agent workflows, prompt engineering, model integration, and AI system optimization.

## Capabilities

### 🤖 Multi-Agent Architecture
- LangGraph workflow orchestration
- Agent state management and routing
- Inter-agent communication protocols
- Supervisor pattern implementation
- Dynamic agent selection and coordination

### 🧠 Prompt Engineering
- Task-specific prompt optimization
- Chain-of-thought reasoning
- Few-shot learning examples
- Context window management
- Prompt template versioning

### 🔗 Model Integration
- OpenRouter API integration
- Multiple model provider support
- Model fallback strategies
- Response caching and optimization
- Token usage tracking and optimization

## Core Responsibilities

### 1. Agent Workflow Architecture

#### State Definition
```python
# agents/state.py
from typing import Annotated, List, Dict, Optional, Any
from langgraph.graph import add_messages
from pydantic import BaseModel
from enum import Enum

class AgentRole(str, Enum):
    SUPERVISOR = "supervisor"
    VISUAL_ANALYST = "visual_analyst"
    DOCUMENT_PROCESSOR = "document_processor"
    PROGRESS_TRACKER = "progress_tracker"
    REPORT_GENERATOR = "report_generator"
    SAFETY_INSPECTOR = "safety_inspector"

class AnalysisRequest(BaseModel):
    type: str
    priority: int
    context: Dict[str, Any]
    files: List[str] = []
    requirements: List[str] = []

class AgentResponse(BaseModel):
    agent_id: str
    content: str
    confidence: float
    metadata: Dict[str, Any] = {}
    next_actions: List[str] = []

class AgentState(BaseModel):
    messages: Annotated[List, add_messages]
    current_agent: AgentRole
    analysis_request: Optional[AnalysisRequest] = None
    agent_responses: List[AgentResponse] = []
    context: Dict[str, Any] = {}
    final_response: Optional[str] = None
    iteration_count: int = 0
    max_iterations: int = 10

    class Config:
        arbitrary_types_allowed = True
```

#### Supervisor Agent Implementation
```python
# agents/supervisor_agent.py
from typing import Dict, List
import json
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from langgraph.graph import StateGraph, END
from openai import AsyncOpenAI

class SupervisorAgent:
    def __init__(self, openrouter_client: AsyncOpenAI):
        self.client = openrouter_client
        self.model = "anthropic/claude-3.5-sonnet"

        self.routing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Construction Analysis Supervisor Agent. Your role is to:
1. Analyze incoming requests and route them to the appropriate specialized agents
2. Coordinate multi-agent workflows
3. Synthesize responses from multiple agents
4. Ensure quality and completeness of analysis

Available specialized agents:
- VISUAL_ANALYST: Analyzes images, videos, and visual documentation
- DOCUMENT_PROCESSOR: Processes text documents, PDFs, and written content
- PROGRESS_TRACKER: Tracks project progress, timelines, and milestones
- SAFETY_INSPECTOR: Evaluates safety compliance and risk assessment
- REPORT_GENERATOR: Creates comprehensive reports and summaries

Current request: {request}
Context: {context}

Determine which agent(s) should handle this request and in what order.
Respond with a JSON object containing:
{{
  "selected_agents": ["agent1", "agent2"],
  "workflow_type": "sequential|parallel|conditional",
  "reasoning": "explanation of routing decision",
  "priority": 1-5
}}"""),
            ("human", "{input}")
        ])

    async def route_request(self, state: AgentState) -> Dict[str, Any]:
        """Route incoming request to appropriate agents"""

        try:
            prompt = self.routing_prompt.format(
                request=state.analysis_request.type if state.analysis_request else "general_inquiry",
                context=json.dumps(state.context, indent=2),
                input=state.messages[-1].content if state.messages else ""
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )

            routing_decision = json.loads(response.choices[0].message.content)

            # Update state with routing decision
            state.context.update({
                "routing_decision": routing_decision,
                "supervisor_reasoning": routing_decision.get("reasoning", "")
            })

            # Set current agent based on first in sequence
            if routing_decision.get("selected_agents"):
                first_agent = routing_decision["selected_agents"][0]
                state.current_agent = AgentRole(first_agent.lower())

            return state.dict()

        except Exception as e:
            # Fallback to visual analyst for image-heavy requests
            state.current_agent = AgentRole.VISUAL_ANALYST
            state.context["error"] = f"Routing error: {str(e)}"
            return state.dict()

    async def synthesize_responses(self, state: AgentState) -> Dict[str, Any]:
        """Combine and synthesize responses from multiple agents"""

        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are synthesizing responses from multiple construction analysis agents.
Create a comprehensive, coherent response that:
1. Integrates insights from all agents
2. Identifies conflicts or inconsistencies
3. Provides actionable recommendations
4. Maintains professional construction industry tone

Agent responses to synthesize:
{agent_responses}

Original request: {original_request}"""),
            ("human", "Please provide a comprehensive synthesis of these agent responses.")
        ])

        try:
            agent_responses_text = "\n\n".join([
                f"**{resp.agent_id}** (Confidence: {resp.confidence})\n{resp.content}"
                for resp in state.agent_responses
            ])

            prompt = synthesis_prompt.format(
                agent_responses=agent_responses_text,
                original_request=state.messages[0].content if state.messages else ""
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )

            synthesized_response = response.choices[0].message.content
            state.final_response = synthesized_response

            return state.dict()

        except Exception as e:
            # Fallback synthesis
            state.final_response = self._create_fallback_synthesis(state.agent_responses)
            return state.dict()

    def _create_fallback_synthesis(self, responses: List[AgentResponse]) -> str:
        """Create a simple synthesis when AI synthesis fails"""
        if not responses:
            return "No analysis results available."

        synthesis = "## Construction Analysis Summary\n\n"
        for response in responses:
            synthesis += f"### {response.agent_id.replace('_', ' ').title()}\n"
            synthesis += f"{response.content}\n\n"

        return synthesis
```

### 2. Specialized Agent Implementations

#### Visual Analysis Agent
```python
# agents/visual_analyst.py
import base64
from typing import List, Dict, Any
from PIL import Image
import io
from langchain.prompts import ChatPromptTemplate

class VisualAnalysisAgent:
    def __init__(self, openrouter_client):
        self.client = openrouter_client
        self.model = "google/gemini-pro-vision"  # Vision-capable model

        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Construction Visual Analysis Agent specializing in:
- Progress assessment from photos/videos
- Quality control inspection
- Safety compliance verification
- Material identification and condition assessment
- Structural analysis from visual evidence

Analyze the provided images and provide:
1. Overall assessment
2. Key observations
3. Issues or concerns identified
4. Recommendations
5. Confidence level (0-1)

Focus on construction-specific details and industry standards."""),
            ("human", """Please analyze these construction site images:

Analysis Type: {analysis_type}
Project Context: {context}
Specific Requirements: {requirements}

Provide detailed construction analysis.""")
        ])

    async def analyze_images(self,
                           image_data: List[bytes],
                           analysis_type: str,
                           context: Dict[str, Any] = None) -> AgentResponse:
        try:
            # Convert images to base64
            image_messages = []
            for img_bytes in image_data:
                # Resize image if too large
                img = Image.open(io.BytesIO(img_bytes))
                if img.width > 1024 or img.height > 1024:
                    img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode()

                image_messages.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })

            # Create prompt
            prompt_text = self.analysis_prompt.format(
                analysis_type=analysis_type,
                context=json.dumps(context or {}, indent=2),
                requirements=context.get("requirements", []) if context else []
            )

            # Prepare messages
            messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt_text},
                    *image_messages
                ]}
            ]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1500,
                temperature=0.2
            )

            analysis_result = response.choices[0].message.content

            # Extract confidence from response or estimate
            confidence = self._extract_confidence(analysis_result)

            return AgentResponse(
                agent_id="visual_analyst",
                content=analysis_result,
                confidence=confidence,
                metadata={
                    "images_analyzed": len(image_data),
                    "analysis_type": analysis_type,
                    "model_used": self.model
                }
            )

        except Exception as e:
            return AgentResponse(
                agent_id="visual_analyst",
                content=f"Visual analysis failed: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )

    def _extract_confidence(self, analysis_text: str) -> float:
        """Extract confidence score from analysis text"""
        # Simple pattern matching for confidence indicators
        confidence_indicators = {
            "highly confident": 0.9,
            "confident": 0.8,
            "moderately confident": 0.7,
            "somewhat confident": 0.6,
            "uncertain": 0.4,
            "unclear": 0.3
        }

        text_lower = analysis_text.lower()
        for indicator, score in confidence_indicators.items():
            if indicator in text_lower:
                return score

        return 0.75  # Default confidence
```

#### Document Processing Agent
```python
# agents/document_processor.py
import PyPDF2
from docx import Document
import json
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate

class DocumentProcessingAgent:
    def __init__(self, openrouter_client):
        self.client = openrouter_client
        self.model = "anthropic/claude-3.5-sonnet"

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Construction Document Processing Agent specializing in:
- Contract analysis and interpretation
- Specification review and compliance checking
- Drawing and blueprint text analysis
- Regulatory compliance verification
- Risk assessment from documentation

Analyze the provided documents and extract:
1. Key information and requirements
2. Compliance issues or gaps
3. Risk factors and concerns
4. Recommendations and next steps
5. Critical dates and milestones

Focus on construction industry standards and best practices."""),
            ("human", """Analyze this construction document:

Document Type: {document_type}
Analysis Focus: {analysis_focus}
Project Context: {context}

Document Content:
{document_content}

Provide comprehensive analysis relevant to construction project management.""")
        ])

    async def process_documents(self,
                              file_paths: List[str],
                              document_type: str,
                              analysis_focus: str,
                              context: Dict[str, Any] = None) -> AgentResponse:
        try:
            # Extract text from all documents
            all_text = ""
            processed_files = []

            for file_path in file_paths:
                text = await self._extract_text_from_file(file_path)
                all_text += f"\n\n--- {file_path} ---\n{text}"
                processed_files.append(file_path)

            # Split text into manageable chunks
            text_chunks = self.text_splitter.split_text(all_text)

            # Process each chunk and combine results
            chunk_analyses = []
            for i, chunk in enumerate(text_chunks):
                chunk_analysis = await self._analyze_text_chunk(
                    chunk, document_type, analysis_focus, context, i
                )
                chunk_analyses.append(chunk_analysis)

            # Synthesize all chunk analyses
            final_analysis = await self._synthesize_chunk_analyses(
                chunk_analyses, document_type, analysis_focus
            )

            return AgentResponse(
                agent_id="document_processor",
                content=final_analysis,
                confidence=0.85,
                metadata={
                    "files_processed": processed_files,
                    "chunks_analyzed": len(text_chunks),
                    "document_type": document_type,
                    "analysis_focus": analysis_focus
                }
            )

        except Exception as e:
            return AgentResponse(
                agent_id="document_processor",
                content=f"Document processing failed: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text content from various file formats"""
        try:
            if file_path.lower().endswith('.pdf'):
                return self._extract_pdf_text(file_path)
            elif file_path.lower().endswith('.docx'):
                return self._extract_docx_text(file_path)
            elif file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"Unsupported file format: {file_path}"
        except Exception as e:
            return f"Error reading {file_path}: {str(e)}"

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

    async def _analyze_text_chunk(self,
                                 chunk: str,
                                 document_type: str,
                                 analysis_focus: str,
                                 context: Dict[str, Any],
                                 chunk_index: int) -> str:
        """Analyze a single text chunk"""
        try:
            prompt = self.analysis_prompt.format(
                document_type=document_type,
                analysis_focus=analysis_focus,
                context=json.dumps(context or {}, indent=2),
                document_content=chunk
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Chunk {chunk_index} analysis failed: {str(e)}"

    async def _synthesize_chunk_analyses(self,
                                       chunk_analyses: List[str],
                                       document_type: str,
                                       analysis_focus: str) -> str:
        """Synthesize analyses from multiple chunks"""
        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """Synthesize the following document analysis chunks into a comprehensive report.
Eliminate redundancy, identify key themes, and provide actionable insights.
Focus on construction project implications."""),
            ("human", """Document Type: {document_type}
Analysis Focus: {analysis_focus}

Chunk Analyses:
{chunk_analyses}

Provide a unified, comprehensive analysis.""")
        ])

        try:
            chunks_text = "\n\n".join([
                f"--- Chunk {i+1} ---\n{analysis}"
                for i, analysis in enumerate(chunk_analyses)
            ])

            prompt = synthesis_prompt.format(
                document_type=document_type,
                analysis_focus=analysis_focus,
                chunk_analyses=chunks_text
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            # Fallback: combine chunks with basic formatting
            return self._create_fallback_synthesis(chunk_analyses)

    def _create_fallback_synthesis(self, chunk_analyses: List[str]) -> str:
        """Create basic synthesis when AI synthesis fails"""
        synthesis = "## Document Analysis Summary\n\n"
        for i, analysis in enumerate(chunk_analyses):
            synthesis += f"### Section {i+1}\n{analysis}\n\n"
        return synthesis
```

### 3. Workflow Orchestration

#### Main Workflow Graph
```python
# agents/workflow.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any

class ConstructionAnalysisWorkflow:
    def __init__(self, openrouter_client):
        self.client = openrouter_client

        # Initialize agents
        self.supervisor = SupervisorAgent(openrouter_client)
        self.visual_analyst = VisualAnalysisAgent(openrouter_client)
        self.document_processor = DocumentProcessingAgent(openrouter_client)

        # Setup workflow graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("visual_analyst", self._visual_analyst_node)
        graph.add_node("document_processor", self._document_processor_node)
        graph.add_node("progress_tracker", self._progress_tracker_node)
        graph.add_node("synthesizer", self._synthesizer_node)

        # Set entry point
        graph.set_entry_point("supervisor")

        # Add routing logic
        graph.add_conditional_edges(
            "supervisor",
            self._route_to_agents,
            {
                "visual_analyst": "visual_analyst",
                "document_processor": "document_processor",
                "progress_tracker": "progress_tracker",
                "synthesize": "synthesizer"
            }
        )

        # Add edges back to supervisor or synthesizer
        graph.add_edge("visual_analyst", "synthesizer")
        graph.add_edge("document_processor", "synthesizer")
        graph.add_edge("progress_tracker", "synthesizer")
        graph.add_edge("synthesizer", END)

        # Add memory for state persistence
        memory = MemorySaver()
        return graph.compile(checkpointer=memory)

    async def _supervisor_node(self, state: AgentState) -> Dict[str, Any]:
        """Supervisor agent node"""
        return await self.supervisor.route_request(state)

    async def _visual_analyst_node(self, state: AgentState) -> Dict[str, Any]:
        """Visual analysis agent node"""
        # Extract image data from context
        image_data = state.context.get("image_data", [])
        analysis_type = state.analysis_request.type if state.analysis_request else "general"

        response = await self.visual_analyst.analyze_images(
            image_data, analysis_type, state.context
        )

        state.agent_responses.append(response)
        return state.dict()

    async def _document_processor_node(self, state: AgentState) -> Dict[str, Any]:
        """Document processing agent node"""
        file_paths = state.context.get("file_paths", [])
        document_type = state.context.get("document_type", "general")
        analysis_focus = state.analysis_request.type if state.analysis_request else "general"

        response = await self.document_processor.process_documents(
            file_paths, document_type, analysis_focus, state.context
        )

        state.agent_responses.append(response)
        return state.dict()

    async def _progress_tracker_node(self, state: AgentState) -> Dict[str, Any]:
        """Progress tracking agent node"""
        # Placeholder for progress tracking logic
        response = AgentResponse(
            agent_id="progress_tracker",
            content="Progress tracking analysis would be performed here.",
            confidence=0.8,
            metadata={"implementation": "pending"}
        )

        state.agent_responses.append(response)
        return state.dict()

    async def _synthesizer_node(self, state: AgentState) -> Dict[str, Any]:
        """Synthesis node"""
        return await self.supervisor.synthesize_responses(state)

    def _route_to_agents(self, state: AgentState) -> str:
        """Routing logic based on analysis request"""
        if not state.context.get("routing_decision"):
            return "synthesize"

        routing_decision = state.context["routing_decision"]
        selected_agents = routing_decision.get("selected_agents", [])

        # Simple routing for now - choose first agent
        if selected_agents:
            agent_name = selected_agents[0].lower()
            if agent_name in ["visual_analyst", "document_processor", "progress_tracker"]:
                return agent_name

        return "synthesize"

    async def process_request(self,
                            user_input: str,
                            files: List[str] = None,
                            images: List[bytes] = None,
                            context: Dict[str, Any] = None) -> str:
        """Process a user request through the workflow"""

        # Prepare initial state
        initial_state = AgentState(
            messages=[{"role": "user", "content": user_input}],
            current_agent=AgentRole.SUPERVISOR,
            context={
                "file_paths": files or [],
                "image_data": images or [],
                **(context or {})
            }
        )

        # Determine analysis request type
        if images:
            initial_state.analysis_request = AnalysisRequest(
                type="visual_analysis",
                priority=2,
                context=initial_state.context
            )
        elif files:
            initial_state.analysis_request = AnalysisRequest(
                type="document_analysis",
                priority=2,
                context=initial_state.context
            )

        # Run the workflow
        result = await self.graph.ainvoke(
            initial_state.dict(),
            config={"configurable": {"thread_id": "default"}}
        )

        return result.get("final_response", "Analysis completed.")
```

### 4. Token Usage Optimization

```python
# utils/token_optimization.py
import tiktoken
from typing import List, Dict, Any
import asyncio

class TokenOptimizer:
    def __init__(self, model_name: str = "gpt-4"):
        self.encoding = tiktoken.encoding_for_model(model_name)
        self.max_tokens = 8192  # Conservative limit

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)

    def optimize_messages(self, messages: List[Dict[str, str]],
                         system_prompt: str = "") -> List[Dict[str, str]]:
        """Optimize message list to fit within token limits"""

        # Reserve tokens for system prompt and response
        system_tokens = self.count_tokens(system_prompt) if system_prompt else 0
        response_tokens = 1000  # Reserve for response
        available_tokens = self.max_tokens - system_tokens - response_tokens

        # Start from most recent messages and work backwards
        optimized_messages = []
        current_tokens = 0

        for message in reversed(messages):
            message_tokens = self.count_tokens(message["content"])

            if current_tokens + message_tokens <= available_tokens:
                optimized_messages.insert(0, message)
                current_tokens += message_tokens
            else:
                # Truncate this message if it's the first one
                if not optimized_messages:
                    remaining_tokens = available_tokens - current_tokens
                    truncated_content = self.truncate_text(
                        message["content"], remaining_tokens
                    )
                    optimized_messages.insert(0, {
                        **message,
                        "content": truncated_content
                    })
                break

        return optimized_messages

# Usage in agents
async def optimized_llm_call(self, prompt: str, context: str = "") -> str:
    optimizer = TokenOptimizer(self.model)

    # Optimize prompt if too long
    prompt_tokens = optimizer.count_tokens(prompt)
    context_tokens = optimizer.count_tokens(context)

    if prompt_tokens + context_tokens > optimizer.max_tokens - 1000:
        # Truncate context first
        max_context_tokens = optimizer.max_tokens - prompt_tokens - 1000
        context = optimizer.truncate_text(context, max_context_tokens)

    # Make API call with optimized content
    response = await self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
```

### 5. Error Handling and Fallbacks

```python
# utils/error_handling.py
import asyncio
from typing import List, Callable, Any
import logging

class AgentErrorHandler:
    def __init__(self, max_retries: int = 3, fallback_models: List[str] = None):
        self.max_retries = max_retries
        self.fallback_models = fallback_models or [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4",
            "google/gemini-pro"
        ]
        self.logger = logging.getLogger(__name__)

    async def with_retry_and_fallback(self,
                                    operation: Callable,
                                    *args, **kwargs) -> Any:
        """Execute operation with retry logic and model fallback"""

        last_exception = None

        for model in self.fallback_models:
            for attempt in range(self.max_retries):
                try:
                    # Update model in kwargs if applicable
                    if 'model' in kwargs:
                        kwargs['model'] = model

                    result = await operation(*args, **kwargs)

                    if attempt > 0 or model != self.fallback_models[0]:
                        self.logger.info(
                            f"Operation succeeded on attempt {attempt + 1} "
                            f"with model {model}"
                        )

                    return result

                except Exception as e:
                    last_exception = e
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed with model {model}: {str(e)}"
                    )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # All attempts failed
        self.logger.error(f"All attempts failed. Last error: {str(last_exception)}")
        raise last_exception

# Usage example
error_handler = AgentErrorHandler()

async def robust_agent_call(self, prompt: str) -> str:
    async def make_api_call(model: str):
        return await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )

    try:
        response = await error_handler.with_retry_and_fallback(
            make_api_call,
            model=self.model
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Analysis failed after all retry attempts: {str(e)}"
```

This AI Agent Development Agent provides comprehensive guidance for building sophisticated, reliable AI agent systems using LangGraph and LangChain for the Construction Analysis AI System.