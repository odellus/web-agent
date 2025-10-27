# Web Agent Development Guide

## Project Structure

```
web-agent/
├── agent-py/                    # Python backend agent
│   ├── src/
│   │   └── web_agent/
│   │       ├── agent/
│   │       │   ├── service.py   # Main agent service
│   │       │   └── nodes.py     # Graph nodes (llm_call, reflection)
│   │       ├── tools/
│   │       │   ├── bash_tool.py # Enhanced bash with injected state
│   │       │   ├── edit_tool.py
│   │       │   └── __init__.py
│   │       ├── state.py         # TraeWebState with working_directory
│   │       └── __init__.py
│   ├── tests/
│   └── pyproject.toml
└── ui/                          # React frontend (future)
```

## How to Run

```bash
cd web-agent/agent-py
. .venv/bin/activate
uv run <command>
```

## Current Status

### ✅ Completed
- Basic LangGraph agent with streaming
- Tool integration (bash, edit, sequential_thinking, task_done)
- State management with MessagesState
- Working directory concept in state

### ❌ Current Issues
- Qwen 8B model lacks sophisticated reasoning
- Bash tool uses `os.getcwd()` instead of injected state
- No TRAE-style reflection step
- Agent gets confused by empty tool responses
- No working directory injection into tools

## TO DO

### 1. Custom LangGraph Agent Implementation

**Problem**: LangGraph's `create_react_agent` is generic and lacks TRAE's reflection capabilities.

**Solution**: Build custom agent with TRAE-style reflection using LangGraph primitives.

#### Architecture
```python
# Service Layer (service.py)
class WebAgentService:
    """Thin wrapper around compiled LangGraph"""
    def __init__(self):
        self.checkpointer = MemorySaver()
        self.langfuse_handler = CallbackHandler()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(TraeWebState)
        workflow.add_node("llm_call", llm_call)
        workflow.add_node("tool_node", ToolNode(tools=all_tools))
        workflow.add_node("reflection_node", reflection_node)

        # Edges: START -> llm_call -> tool_node -> reflection_node -> llm_call
        return workflow.compile(checkpointer=self.checkpointer)
```

#### Graph Flow
```
START -> llm_call -> [tool_node | END] -> reflection_node -> llm_call -> ...
```

### 2. Working Directory Injection

**Problem**: Bash tool uses `os.getcwd()` which doesn't respect agent's working directory context.

**Solution**: Use LangChain's `InjectedState` to inject working directory into tools.

#### Enhanced Bash Tool
```python
@tool
def bash_tool(
    command: str,
    working_directory: Annotated[str, InjectedState("working_directory")],
    restart: bool = False,
) -> str:
    """Execute shell commands with injected working directory context."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=working_directory,  # Use injected state!
        )
        return result.stdout or (f"STDERR:\n{result.stderr}" if result.stderr else "")
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"
```

#### Enhanced State
```python
class TraeWebState(MessagesState):
    """State for IDE agent with working directory support."""
    working_directory: str = "/home/user/project"
    remaining_steps: int = 5
```

### 3. TRAE-Style Reflection

**Problem**: Standard ReAct agents lack sophisticated reflection on tool results.

**Solution**: Add reflection node that analyzes tool execution and provides guidance.

#### Reflection Node
```python
async def reflection_node(state: TraeWebState):
    """TRAE-style reflection on tool results"""
    tool_results = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
    if not tool_results:
        return {"messages": []}

    # Analyze tool results for errors or issues
    errors = [result for result in tool_results if "Error:" in result.content]

    if errors:
        reflection = "Some tools encountered errors. Consider alternative approaches or fixing parameters."
    else:
        reflection = "Tool execution completed successfully. Please review results and continue if needed."

    return {"messages": [AIMessage(content=reflection)]}
```

### 4. Enhanced Tool Integration

**Problem**: Tools need access to working directory and better error handling.

**Solution**: Use a custom `ToolNode` with custom error handling and state injection.

#### ToolNode Configuration
```python
# Won't be exactly this but something like maybe?
# maybe not
tool_node = ToolNode(
    tools=all_tools,
    handle_tool_errors=lambda e: f"Tool error: {str(e)}. Please try again."
)
```

### 4.1 Create our own ToolNode using source code for ToolNode
We want to build our wonn Custom ToolNode using the examples given in [Worflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) because we're going to be using Command and interrupt for [HITL](https://docs.langchain.com/oss/python/langgraph/add-human-in-the-loop)


### 5. System Prompt Integration

**Problem**: Agent lacks TRAE's sophisticated system prompt and methodology.

**Solution**: Inject working directory into TRAE system prompt.

#### Enhanced LLM Call
```python
async def llm_call(state: TraeWebState):
    """LLM with injected working directory context"""
    system_prompt = f"""{TRAE_AGENT_SYSTEM_PROMPT}

Current working directory: {state['working_directory']}

Follow these steps methodically:
1. Understand the user's request
2. Use tools to execute the task
3. Verify results
4. Call task_done when complete"""

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await model_with_tools.ainvoke(messages)
    return {"messages": [response]}
```

### 6. Langfuse Integration

**Problem**: No observability or tracing for debugging agent behavior.

**Solution**: Integrate Langfuse for detailed tracing.

#### Langfuse Setup
```python
from langfuse.langchain import CallbackHandler

class WebAgentService:
    def __init__(self):
        self.langfuse_handler = CallbackHandler()
        # ... rest of initialization

    async def chat(self, message: str, thread_id: str = "default"):
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler]
        }
        # ... execution logic
```

### 7. Model Considerations

**Problem**: Qwen 8B lacks reasoning for complex tasks.

**Solution**: Plan for model scaling and testing.

#### Model Strategy
- **Current**: Qwen 8B for development
- **Next**: Test with Claude 3.5 Sonnet or GPT-4
- **Long-term**: Fine-tune on collected trajectory data

### 8. Testing Infrastructure

**Problem**: Limited testing for complex agent workflows.

**Solution**: Comprehensive test suite with trajectory validation.

#### Test Categories
- **Unit Tests**: Individual tool functionality
- **Integration Tests**: Agent workflow end-to-end
- **Regression Tests**: Known working trajectories
- **Performance Tests**: Token usage and latency

## Implementation Priority

### Phase 1: Core Infrastructure (Week 1)
1. ✅ Basic custom agent structure
2. ✅ Working directory injection
3. ✅ Enhanced bash tool
4. ✅ Basic reflection node

### Phase 2: Advanced Features (Week 2)
1. ✅ Langfuse integration
2. ✅ Enhanced error handling
3. ✅ System prompt optimization
4. ✅ ToolNode configuration

### Phase 3: Testing & Optimization (Week 3)
1. ✅ Comprehensive test suite
2. ✅ Model comparison testing
3. ✅ Performance optimization
4. ✅ Documentation completion

## Key Insights

### Architecture Decisions
1. **Custom over Prebuilt**: Building custom agent gives us TRAE's reflection capabilities
2. **State Injection**: `InjectedState` is cleaner than passing parameters manually
3. **Service Layer**: Thin wrapper separates concerns and enables clean API
4. **ToolNode**: Built-in parallel execution and error handling

### Technical Patterns
1. **Reflection Loop**: LLM → Tools → Reflection → LLM (vs standard LLM → Tools → LLM)
2. **Working Directory**: Injected into state and tools, not exposed to LLM
3. **Error Handling**: Graceful degradation with informative error messages
4. **Observability**: Langfuse provides detailed tracing for debugging

### Performance Considerations
1. **Model Scaling**: 8B models limited for complex reasoning
2. **Token Efficiency**: System prompt optimization crucial
3. **Parallel Execution**: ToolNode enables concurrent tool calls
4. **Caching**: Checkpointing enables conversation persistence

## Next Steps

1. **Implement custom agent** with reflection capabilities
2. **Add working directory injection** to bash tool
3. **Integrate Langfuse** for observability
4. **Test with larger models** for better reasoning
5. **Collect trajectory data** for future training
6. **Build React frontend** for web interface

## Success Metrics

- ✅ Agent can execute bash commands in correct working directory
- ✅ Reflection step improves task completion rate
- ✅ Langfuse tracing provides actionable insights
- ✅ System scales to multiple concurrent users
- ✅ Frontend provides seamless IDE-like experience

---

*Last Updated: 2025-10-04*
*Status: Planning Phase - Ready for Implementation*
