# AI Agents Documentation

This document provides comprehensive documentation for the AI agents system in the Construction Analysis AI platform, built with LangGraph 0.6.7 and LangChain 0.3.27.

## Agent Architecture Overview

### Multi-Agent System Design
The system implements a **Supervisor Pattern** where a central Supervisor Agent orchestrates multiple specialized agents to handle different aspects of construction analysis.

```
┌─────────────────────────────────────────────────────┐
│                Supervisor Agent                     │
│              (LangGraph Workflow)                   │
└──────────┬──────────┬──────────┬──────────┬────────┘
           │          │          │          │
    ┌──────▼───┐ ┌───▼──────┐ ┌─▼──────┐ ┌▼──────────┐
    │Visual    │ │Document  │ │Progress│ │Report     │
    │Agent     │ │Agent     │ │Agent   │ │Generator  │
    │(OpenRtr) │ │(NLP)     │ │(Logic) │ │(Template) │
    └──────────┘ └──────────┘ └────────┘ └───────────┘
```

### Core Technologies
- **LangGraph 0.6.7**: Agent workflow orchestration with state management
- **LangChain 0.3.27**: Agent base classes and prompt management
- **OpenRouter**: AI model access (Grok-4 Fast + Gemini 2.5 Flash)
- **Async/Await**: Full asynchronous processing support

## Supervisor Agent

### Purpose and Responsibilities
The Supervisor Agent acts as the central coordinator that:
- Routes user requests to appropriate specialized agents
- Manages conversation context and memory
- Aggregates responses from multiple agents
- Handles complex multi-step workflows
- Maintains state across interactions

### LangGraph Workflow Implementation

#### State Definition
```python
from typing_extensions import TypedDict
from typing import List, Dict, Any, Optional

class SupervisorState(TypedDict):
    """State managed by supervisor workflow."""
    project_id: str
    session_id: str
    messages: List[Dict[str, Any]]
    current_task: str
    agent_results: Dict[str, Any]
    uploaded_files: List[str]
    final_response: Optional[str]
    metadata: Dict[str, Any]
```

#### Workflow Graph Structure
```python
from langgraph.graph import StateGraph, END

def create_supervisor_workflow() -> StateGraph:
    """Create the main supervisor workflow."""
    workflow = StateGraph(SupervisorState)

    # Add processing nodes
    workflow.add_node("classify_request", classify_user_request)
    workflow.add_node("visual_analysis", visual_analysis_node)
    workflow.add_node("document_processing", document_processing_node)
    workflow.add_node("progress_tracking", progress_tracking_node)
    workflow.add_node("generate_response", generate_final_response)

    # Set entry point
    workflow.set_entry_point("classify_request")

    # Add conditional routing
    workflow.add_conditional_edges(
        "classify_request",
        route_to_agents,
        {
            "visual": "visual_analysis",
            "document": "document_processing",
            "progress": "progress_tracking",
            "general": "generate_response"
        }
    )

    # Connect to response generation
    workflow.add_edge("visual_analysis", "generate_response")
    workflow.add_edge("document_processing", "generate_response")
    workflow.add_edge("progress_tracking", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow
```

#### Request Classification
```python
async def classify_user_request(state: SupervisorState) -> SupervisorState:
    """Classify user request to determine routing."""
    message = state["messages"][-1]["content"].lower()

    # AI-powered classification
    classification_prompt = f"""
    Analyze this user message and classify the request type:
    Message: "{message}"

    Classify as one of:
    - visual: Image analysis, photo review, visual inspection
    - document: Document processing, PDF analysis, file review
    - progress: Progress tracking, timeline, status updates
    - general: General questions, conversation, other

    Return only the classification word.
    """

    # Use lightweight model for classification
    classifier = ChatOpenRouter(
        model="meta-llama/llama-3.1-8b-instruct:free",
        temperature=0.1
    )

    result = await classifier.ainvoke([
        HumanMessage(content=classification_prompt)
    ])

    task_type = result.content.strip().lower()
    if task_type not in ["visual", "document", "progress", "general"]:
        task_type = "general"

    state["current_task"] = task_type
    return state
```

## Visual Analysis Agent

### Capabilities
- Construction site image analysis
- Progress estimation from visual data
- Safety issue detection
- Quality assessment
- Element identification (walls, foundations, roofing, etc.)

### Implementation
```python
from langchain_community.chat_models import ChatOpenRouter
from langchain.schema import HumanMessage
import base64

class VisualAnalysisAgent:
    """Specialized agent for visual construction analysis."""

    def __init__(self):
        self.model = ChatOpenRouter(
            model="anthropic/claude-3-5-sonnet-20241022",
            openrouter_api_key=settings.openrouter_api_key,
            temperature=0.3
        )

    async def analyze_image(self, image_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze construction image with detailed output."""

        # Prepare image
        image_data = self._encode_image(image_path)

        # Construct analysis prompt
        prompt = self._build_analysis_prompt(context)

        # Create message with image
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                }
            ]
        )

        # Get analysis
        response = await self.model.ainvoke([message])

        # Parse structured response
        return self._parse_analysis_response(response.content)

    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build detailed analysis prompt."""
        return f"""
        As a construction analysis expert, analyze this construction site image.

        Project Context:
        - Project ID: {context.get('project_id', 'Unknown')}
        - Previous Progress: {context.get('last_progress', 'Unknown')}

        Provide analysis in JSON format with:
        {{
            "progress_percentage": float (0-100),
            "detected_elements": [list of construction elements],
            "safety_issues": [list of safety concerns],
            "quality_observations": [list of quality notes],
            "recommendations": [list of recommendations],
            "confidence_score": float (0-1),
            "stage_assessment": "foundation|framing|roofing|finishing|completed"
        }}

        Focus on:
        1. Accurate progress estimation
        2. Safety compliance
        3. Work quality assessment
        4. Structural integrity observations
        5. Schedule adherence indicators
        """

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate analysis response."""
        try:
            import json
            analysis = json.loads(response)

            # Validate and set defaults
            return {
                "progress_percentage": max(0, min(100, analysis.get("progress_percentage", 0))),
                "detected_elements": analysis.get("detected_elements", []),
                "safety_issues": analysis.get("safety_issues", []),
                "quality_observations": analysis.get("quality_observations", []),
                "recommendations": analysis.get("recommendations", []),
                "confidence_score": max(0, min(1, analysis.get("confidence_score", 0.5))),
                "stage_assessment": analysis.get("stage_assessment", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except json.JSONDecodeError:
            # Fallback parsing
            return self._fallback_parse(response)
```

### Vision Model Integration
```python
async def enhanced_visual_analysis(
    self,
    image_path: str,
    analysis_type: str = "comprehensive"
) -> Dict[str, Any]:
    """Enhanced analysis with multiple model approaches."""

    # Primary analysis with Claude
    claude_result = await self._claude_analysis(image_path)

    # Complementary analysis with Gemini (for comparison)
    if analysis_type == "comprehensive":
        gemini_result = await self._gemini_analysis(image_path)

        # Combine and validate results
        combined_result = self._combine_analyses(claude_result, gemini_result)
        return combined_result

    return claude_result

async def _gemini_analysis(self, image_path: str) -> Dict[str, Any]:
    """Gemini 2.5 Flash vision analysis for comparison."""
    gemini_model = ChatOpenRouter(
        model="google/gemini-2.0-flash-exp:free",
        temperature=0.2
    )

    # Similar implementation with Gemini-specific prompting
    # ...
```

## Document Processing Agent

### Capabilities
- PDF document analysis and extraction
- Technical specification parsing
- Compliance document review
- Timeline and milestone extraction
- Cost and material identification

### Implementation
```python
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessingAgent:
    """Agent for processing construction documents."""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

        self.model = ChatOpenRouter(
            model="anthropic/claude-3-5-sonnet-20241022",
            temperature=0.1
        )

    async def process_document(self, file_path: str, document_type: str) -> Dict[str, Any]:
        """Process construction document and extract key information."""

        # Load and split document
        documents = await self._load_document(file_path, document_type)
        chunks = self.text_splitter.split_documents(documents)

        # Process chunks and extract information
        extracted_data = {}

        for i, chunk in enumerate(chunks):
            chunk_analysis = await self._analyze_chunk(chunk.page_content, i)
            extracted_data = self._merge_chunk_data(extracted_data, chunk_analysis)

        # Final consolidation
        final_analysis = await self._consolidate_analysis(extracted_data)

        return final_analysis

    async def _analyze_chunk(self, text: str, chunk_index: int) -> Dict[str, Any]:
        """Analyze individual document chunk."""

        analysis_prompt = f"""
        Analyze this construction document section and extract:

        Text: {text}

        Extract in JSON format:
        {{
            "document_type": "plans|specs|contract|report|other",
            "key_dates": ["YYYY-MM-DD", ...],
            "materials": ["material1", "material2", ...],
            "specifications": {{"spec_name": "value", ...}},
            "compliance_items": ["item1", "item2", ...],
            "milestones": ["milestone1", "milestone2", ...],
            "costs": {{"item": "amount", ...}},
            "personnel": ["person/role", ...],
            "locations": ["location1", ...],
            "risks": ["risk1", "risk2", ...],
            "quality_requirements": ["req1", "req2", ...]
        }}

        Focus on construction-specific information.
        """

        response = await self.model.ainvoke([
            HumanMessage(content=analysis_prompt)
        ])

        return self._parse_json_response(response.content)
```

## Progress Tracking Agent

### Capabilities
- Timeline analysis and updates
- Milestone tracking
- Schedule adherence monitoring
- Progress prediction
- Bottleneck identification

### Implementation
```python
class ProgressTrackingAgent:
    """Agent for tracking construction progress."""

    def __init__(self, project_repository):
        self.project_repository = project_repository
        self.model = ChatOpenRouter(
            model="anthropic/claude-3-5-sonnet-20241022",
            temperature=0.2
        )

    async def analyze_progress(self, project_id: str, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze project progress with new data."""

        # Get historical data
        historical_data = await self._get_historical_progress(project_id)

        # Calculate progress metrics
        progress_analysis = await self._calculate_progress_metrics(
            historical_data,
            new_data
        )

        # Predict future progress
        predictions = await self._predict_future_progress(
            historical_data,
            progress_analysis
        )

        # Identify issues and recommendations
        insights = await self._generate_insights(
            progress_analysis,
            predictions
        )

        return {
            "current_progress": progress_analysis,
            "predictions": predictions,
            "insights": insights,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _calculate_progress_metrics(
        self,
        historical: List[Dict],
        current: Dict
    ) -> Dict[str, Any]:
        """Calculate detailed progress metrics."""

        analysis_prompt = f"""
        Analyze construction progress data:

        Historical Data: {json.dumps(historical[-10:])}  # Last 10 entries
        Current Data: {json.dumps(current)}

        Calculate and return JSON:
        {{
            "overall_progress": float (0-100),
            "phase_progress": {{"phase_name": progress_percentage}},
            "velocity": float (progress per week),
            "trend": "accelerating|steady|declining",
            "critical_path_status": "on_track|at_risk|delayed",
            "completion_estimate": "YYYY-MM-DD",
            "confidence_level": float (0-1)
        }}

        Consider factors:
        - Weather impacts
        - Resource availability
        - Quality requirements
        - Safety considerations
        """

        response = await self.model.ainvoke([
            HumanMessage(content=analysis_prompt)
        ])

        return self._parse_json_response(response.content)
```

## Report Generation Agent

### Capabilities
- Executive summary generation
- Technical report compilation
- Progress report creation
- Custom report formats (JSON, PDF, Excel)
- Data visualization preparation

### Implementation
```python
from jinja2 import Environment, FileSystemLoader
import json

class ReportGenerationAgent:
    """Agent for generating comprehensive reports."""

    def __init__(self):
        self.model = ChatOpenRouter(
            model="anthropic/claude-3-5-sonnet-20241022",
            temperature=0.3
        )

        self.template_env = Environment(
            loader=FileSystemLoader("templates/reports")
        )

    async def generate_report(
        self,
        project_id: str,
        report_type: str,
        data_sources: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive project report."""

        # Aggregate data from all sources
        aggregated_data = await self._aggregate_data(data_sources)

        # Generate report sections
        sections = await self._generate_sections(
            report_type,
            aggregated_data
        )

        # Create executive summary
        executive_summary = await self._generate_executive_summary(
            aggregated_data,
            sections
        )

        # Format final report
        report = {
            "project_id": project_id,
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "executive_summary": executive_summary,
            "sections": sections,
            "metadata": {
                "data_sources_count": len(data_sources),
                "total_images_analyzed": aggregated_data.get("image_count", 0),
                "document_pages_processed": aggregated_data.get("document_pages", 0)
            }
        }

        return report

    async def _generate_executive_summary(
        self,
        data: Dict[str, Any],
        sections: Dict[str, Any]
    ) -> str:
        """Generate AI-powered executive summary."""

        summary_prompt = f"""
        Create an executive summary for this construction project report:

        Project Data: {json.dumps(data, default=str)[:2000]}
        Report Sections: {list(sections.keys())}

        Generate a concise executive summary (200-300 words) covering:
        1. Project status and overall progress
        2. Key achievements and milestones
        3. Current challenges and risks
        4. Recommendations and next steps
        5. Timeline and budget implications

        Write in professional, clear language for project stakeholders.
        """

        response = await self.model.ainvoke([
            HumanMessage(content=summary_prompt)
        ])

        return response.content
```

## Agent Orchestration Patterns

### Parallel Processing
```python
async def parallel_agent_processing(
    self,
    image_files: List[str],
    document_files: List[str]
) -> Dict[str, Any]:
    """Process multiple files with parallel agents."""

    # Create tasks for parallel execution
    image_tasks = [
        self.visual_agent.analyze_image(img_path)
        for img_path in image_files
    ]

    document_tasks = [
        self.document_agent.process_document(doc_path, "pdf")
        for doc_path in document_files
    ]

    # Execute in parallel
    image_results = await asyncio.gather(*image_tasks, return_exceptions=True)
    document_results = await asyncio.gather(*document_tasks, return_exceptions=True)

    # Aggregate results
    return {
        "visual_analyses": [r for r in image_results if not isinstance(r, Exception)],
        "document_analyses": [r for r in document_results if not isinstance(r, Exception)],
        "errors": [str(r) for r in image_results + document_results if isinstance(r, Exception)]
    }
```

### Sequential Workflow
```python
async def sequential_analysis_workflow(
    self,
    project_id: str,
    uploaded_files: List[str]
) -> Dict[str, Any]:
    """Sequential workflow for comprehensive analysis."""

    workflow_state = {
        "project_id": project_id,
        "stage": "initial",
        "results": {}
    }

    # Stage 1: Visual Analysis
    if any(f.endswith(('.jpg', '.jpeg', '.png')) for f in uploaded_files):
        image_files = [f for f in uploaded_files if f.endswith(('.jpg', '.jpeg', '.png'))]
        visual_results = await self._process_images(image_files)
        workflow_state["results"]["visual"] = visual_results
        workflow_state["stage"] = "visual_complete"

    # Stage 2: Document Processing
    if any(f.endswith(('.pdf', '.docx')) for f in uploaded_files):
        doc_files = [f for f in uploaded_files if f.endswith(('.pdf', '.docx'))]
        document_results = await self._process_documents(doc_files)
        workflow_state["results"]["documents"] = document_results
        workflow_state["stage"] = "documents_complete"

    # Stage 3: Progress Update
    if "visual" in workflow_state["results"]:
        progress_update = await self._update_progress(
            project_id,
            workflow_state["results"]["visual"]
        )
        workflow_state["results"]["progress"] = progress_update
        workflow_state["stage"] = "progress_complete"

    # Stage 4: Report Generation
    final_report = await self._generate_comprehensive_report(
        project_id,
        workflow_state["results"]
    )
    workflow_state["results"]["report"] = final_report
    workflow_state["stage"] = "complete"

    return workflow_state
```

## Memory and Context Management

### Conversation Memory
```python
from langgraph.checkpoint.memory import MemorySaver

class ConversationMemory:
    """Manage conversation context and memory."""

    def __init__(self):
        self.memory = MemorySaver()

    async def save_context(
        self,
        session_id: str,
        project_id: str,
        interaction_data: Dict[str, Any]
    ):
        """Save interaction context."""
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "project_id": project_id,
            "interaction": interaction_data
        }

        await self.memory.asave({
            "session_id": session_id,
            "context": context
        })

    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieve conversation context."""
        return await self.memory.aget(session_id)
```

### Project Context
```python
class ProjectContext:
    """Maintain project-specific context across interactions."""

    def __init__(self, project_repository):
        self.project_repository = project_repository

    async def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive project context."""
        project = await self.project_repository.find_by_id(project_id)

        # Get recent analyses
        recent_analyses = await self._get_recent_analyses(project_id, limit=10)

        # Get progress history
        progress_history = await self._get_progress_history(project_id)

        return {
            "project": project,
            "recent_analyses": recent_analyses,
            "progress_history": progress_history,
            "current_phase": self._determine_current_phase(progress_history),
            "key_stakeholders": project.stakeholders if hasattr(project, 'stakeholders') else [],
            "critical_milestones": await self._get_upcoming_milestones(project_id)
        }
```

## Error Handling and Resilience

### Agent Error Recovery
```python
class AgentErrorHandler:
    """Handle agent errors and implement recovery strategies."""

    @staticmethod
    async def with_retry(
        agent_func: Callable,
        max_retries: int = 3,
        backoff_delay: float = 1.0
    ):
        """Execute agent function with retry logic."""
        for attempt in range(max_retries):
            try:
                return await agent_func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise AgentProcessingError(f"Agent failed after {max_retries} attempts: {str(e)}")

                await asyncio.sleep(backoff_delay * (2 ** attempt))

    @staticmethod
    async def fallback_processing(
        primary_agent: Callable,
        fallback_agent: Callable,
        input_data: Any
    ):
        """Use fallback agent if primary fails."""
        try:
            return await primary_agent(input_data)
        except Exception as e:
            logger.warning(f"Primary agent failed: {e}, using fallback")
            return await fallback_agent(input_data)
```

### Circuit Breaker Pattern
```python
class AgentCircuitBreaker:
    """Implement circuit breaker for agent reliability."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, agent_func: Callable, *args, **kwargs):
        """Execute agent function through circuit breaker."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise AgentUnavailableError("Agent circuit breaker is open")

        try:
            result = await agent_func(*args, **kwargs)

            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

            raise e
```

## Performance Optimization

### Caching Strategy
```python
from functools import lru_cache
import hashlib

class AgentCache:
    """Cache agent results for performance."""

    def __init__(self):
        self.cache = {}

    def cache_key(self, file_path: str, agent_type: str) -> str:
        """Generate cache key for file analysis."""
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return f"{agent_type}:{file_hash}"

    async def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available."""
        cached = self.cache.get(cache_key)
        if cached and time.time() - cached['timestamp'] < 3600:  # 1 hour TTL
            return cached['result']
        return None

    async def cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache analysis result."""
        self.cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
```

This comprehensive AI agents documentation provides the foundation for understanding, implementing, and extending the multi-agent system for construction analysis.