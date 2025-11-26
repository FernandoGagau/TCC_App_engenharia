# LangGraph v0.6.7 Documentation

## Overview
LangGraph v0.6.7 represents a major evolution from v0.2.63, introducing production-ready features for building complex multi-agent systems. This version brings significant architectural improvements, enhanced state management, and better integration with the LangGraph Platform.

## Major Changes from v0.2.63 to v0.6.7

### Breaking Changes ⚠️
1. **StateGraph API Changes**
   - New import structure: `from langgraph.graph import StateGraph, MessagesGraph`
   - Deprecated: `from langgraph.graph import StateGraph as Graph`
   - State annotations now require TypedDict or Pydantic models

2. **Checkpoint System Overhaul**
   - New checkpoint format incompatible with v0.2.x
   - Migration required for existing checkpoints
   - Enhanced checkpoint metadata and versioning

3. **Agent Creation Pattern**
   - Simplified agent creation with prebuilt components
   - New functional API alongside graph API
   - Better type safety and validation

### New Features 🚀

#### 1. Functional API
```python
from langgraph.functional import entrypoint, task

@entrypoint()
async def my_agent(state: dict) -> dict:
    """New functional API for simpler agents"""
    result = await some_task(state)
    return {"output": result}

@task()
async def some_task(input: str) -> str:
    """Reusable task decorator"""
    return process(input)
```

#### 2. Enhanced State Management
```python
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    messages: Annotated[list, add]  # Reducer annotation
    context: dict
    metadata: dict

graph = StateGraph(AgentState)
```

#### 3. Streaming Improvements
```python
# Multiple streaming modes
async for chunk in graph.astream(input, mode="updates"):
    print(chunk)

# Available modes: "values", "updates", "messages", "custom", "all"
```

#### 4. Human-in-the-Loop
```python
from langgraph.prebuilt import interrupt

def human_approval_node(state):
    if state["requires_approval"]:
        # Pause for human input
        human_input = interrupt("Please approve this action")
        state["approved"] = human_input
    return state
```

## Core Components

### Graph Construction
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Create graph with checkpoint support
memory = MemorySaver()
graph = StateGraph(AgentState, checkpointer=memory)

# Add nodes
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

# Add edges
graph.add_edge(START, "agent")
graph.add_conditional_edges(
    "agent",
    should_use_tools,
    {
        "tools": "tools",
        "end": END,
    }
)

# Compile
app = graph.compile()
```

### Prebuilt Agents
```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# Quick agent creation
agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4"),
    tools=[...],
    state_schema=AgentState,
    interrupt_before=["tools"],  # Human approval
    checkpointer=memory,
)
```

### Subgraphs
```python
from langgraph.graph import StateGraph

# Define subgraph
subgraph = StateGraph(SubState)
subgraph.add_node("process", process_node)
subgraph.add_edge(START, "process")
subgraph.add_edge("process", END)

# Add as node in parent graph
parent_graph = StateGraph(ParentState)
parent_graph.add_node("subflow", subgraph.compile())
```

## State Management

### State Reducers
```python
from typing import Annotated
from operator import add

class State(TypedDict):
    # Accumulate messages
    messages: Annotated[list, add]

    # Replace value
    status: str

    # Custom reducer
    scores: Annotated[dict, lambda x, y: {**x, **y}]
```

### State Persistence
```python
from langgraph.checkpoint.postgres import PostgresSaver

# Production checkpoint storage
checkpointer = PostgresSaver(
    connection_string="postgresql://...",
    schema="langgraph",
)

graph = StateGraph(State, checkpointer=checkpointer)
```

### Memory Patterns
```python
from langgraph.memory import InMemoryStore

# Cross-thread memory
store = InMemoryStore()

def agent_with_memory(state: State, config: RunnableConfig):
    namespace = ("memories", config["configurable"]["user_id"])
    memories = store.search(namespace)

    # Use memories in processing
    result = process_with_context(state, memories)

    # Store new memories
    store.put(namespace, state["key"], result)
    return {"output": result}
```

## Multi-Agent Patterns

### Supervisor Architecture
```python
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

# Supervisor decides which agent to call
class SupervisorState(TypedDict):
    messages: list
    next_agent: str

def supervisor(state: SupervisorState):
    # Decide next agent based on state
    if needs_research(state):
        return {"next_agent": "researcher"}
    elif needs_analysis(state):
        return {"next_agent": "analyst"}
    return {"next_agent": "END"}

# Build supervisor graph
graph = StateGraph(SupervisorState)
graph.add_node("supervisor", supervisor)
graph.add_node("researcher", research_agent)
graph.add_node("analyst", analyst_agent)

graph.add_conditional_edges(
    "supervisor",
    lambda x: x["next_agent"],
    {
        "researcher": "researcher",
        "analyst": "analyst",
        "END": END,
    }
)
```

### Swarm Pattern
```python
from langgraph.prebuilt import create_react_agent

# Agents can hand off to each other
def create_swarm_agent(name: str, handoff_agents: list):
    def agent_node(state):
        # Process and decide handoff
        if should_handoff(state):
            return {"handoff_to": select_agent(handoff_agents)}
        return process(state)
    return agent_node

# Create swarm
agents = {
    "coordinator": create_swarm_agent("coordinator", ["specialist1", "specialist2"]),
    "specialist1": create_swarm_agent("specialist1", ["coordinator"]),
    "specialist2": create_swarm_agent("specialist2", ["coordinator"]),
}
```

## Deployment with LangGraph Platform

### Application Structure
```python
# langgraph.json
{
    "python_version": "3.11",
    "dependencies": ["./requirements.txt"],
    "graphs": {
        "main": "./app.py:graph",
        "assistant": "./assistant.py:assistant_graph"
    },
    "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "LANGSMITH_API_KEY": "${LANGSMITH_API_KEY}"
    }
}
```

### Server Deployment
```python
# app.py
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

def create_graph():
    checkpointer = PostgresSaver.from_conn_string(
        os.environ["DATABASE_URL"]
    )

    graph = StateGraph(State, checkpointer=checkpointer)
    # ... build graph
    return graph.compile()

# Export for LangGraph Platform
graph = create_graph()
```

### Client Usage
```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:8000")

# Create assistant
assistant = await client.assistants.create(
    graph_id="main",
    config={"temperature": 0.7}
)

# Run with streaming
thread = await client.threads.create()
async for event in client.runs.stream(
    thread_id=thread["thread_id"],
    assistant_id=assistant["assistant_id"],
    input={"messages": [{"role": "user", "content": "Hello"}]},
):
    print(event)
```

## Performance Optimizations

### Parallel Execution
```python
from langgraph.graph import StateGraph
from langgraph.pregel import Send

def dispatcher(state):
    # Send to multiple nodes in parallel
    return [
        Send("analyzer", {"data": state["data"][0]}),
        Send("analyzer", {"data": state["data"][1]}),
        Send("analyzer", {"data": state["data"][2]}),
    ]

graph.add_node("dispatcher", dispatcher)
graph.add_node("analyzer", analyzer_node)
```

### Async Support
```python
async def async_agent(state):
    # Parallel async operations
    results = await asyncio.gather(
        fetch_data(state["query"]),
        analyze_context(state["context"]),
        generate_response(state["prompt"])
    )
    return {"results": results}
```

### Caching
```python
from langgraph.cache import RedisCache

cache = RedisCache(redis_url="redis://localhost:6379")

@cache.cached(ttl=3600)
async def expensive_operation(input):
    return await process(input)
```

## Testing

### Unit Testing
```python
import pytest
from langgraph.graph import StateGraph

@pytest.fixture
def test_graph():
    graph = StateGraph(TestState)
    # Build test graph
    return graph.compile()

async def test_agent_flow(test_graph):
    result = await test_graph.ainvoke(
        {"messages": [{"role": "user", "content": "test"}]}
    )
    assert result["status"] == "completed"
```

### Integration Testing
```python
from langgraph.testing import GraphTestHarness

harness = GraphTestHarness(graph)

# Test specific paths
await harness.test_path(
    input={"query": "test"},
    expected_nodes=["agent", "tools", "agent"],
    expected_output={"result": "success"}
)
```

## Monitoring and Observability

### LangSmith Integration
```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "construction-agent"

# Automatic tracing for all graph executions
```

### Custom Metrics
```python
from langgraph.callbacks import CallbackHandler

class MetricsCallback(CallbackHandler):
    def on_node_start(self, node_name, inputs, **kwargs):
        metrics.increment(f"node.{node_name}.started")

    def on_node_end(self, node_name, outputs, **kwargs):
        metrics.increment(f"node.{node_name}.completed")
```

## Migration Guide from v0.2.63 to v0.6.7

### Step 1: Update Dependencies
```bash
pip install langgraph==0.6.7
pip install langchain-core==0.3.28
```

### Step 2: Update Imports
```python
# Old (0.2.63)
from langgraph.graph import StateGraph
from langgraph.checkpoint import MemorySaver

# New (0.6.7)
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
```

### Step 3: Update State Definition
```python
# Old
State = TypedDict("State", {
    "messages": list,
    "context": dict
})

# New
from typing import Annotated
from operator import add

class State(TypedDict):
    messages: Annotated[list, add]
    context: dict
```

### Step 4: Update Graph Compilation
```python
# Old
graph = StateGraph(State)
# ... add nodes and edges
app = graph.compile(checkpointer=checkpointer)

# New
graph = StateGraph(State, checkpointer=checkpointer)
# ... add nodes and edges
app = graph.compile()
```

## Best Practices

1. **State Design**
   - Keep state minimal and serializable
   - Use reducers for list/dict accumulation
   - Avoid storing large objects in state

2. **Error Handling**
   - Implement retry logic in nodes
   - Use try-except in critical paths
   - Add fallback nodes for failures

3. **Performance**
   - Use async nodes when possible
   - Parallelize independent operations
   - Cache expensive computations

4. **Testing**
   - Test individual nodes in isolation
   - Use test harness for integration tests
   - Mock external dependencies

5. **Deployment**
   - Use PostgreSQL for production checkpoints
   - Implement health checks
   - Monitor token usage and costs

## Resources

- [Official Documentation](https://langchain-ai.github.io/langgraph/)
- [API Reference](https://langchain-ai.github.io/langgraph/reference/)
- [GitHub Repository](https://github.com/langchain-ai/langgraph)
- [LangGraph Platform](https://langchain-ai.github.io/langgraph/cloud/)
- [Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)
- [Discord Community](https://discord.gg/langchain)