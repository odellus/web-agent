import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import DirectoryPath
from web_agent.state import TraeWebState
from web_agent.tools import all_tools
from pathlib import Path

# TRAE Agent system prompt (simplified for testing)
TRAE_AGENT_SYSTEM_PROMPT = """You are an AI assistant that helps with software tasks.
Use tools to execute commands and edit files.
After using tools, reflect on the results before proceeding.
Call task_done when the task is complete.
"""


async def llm_call(state: TraeWebState):
    """LLM call node - invokes the model with tools."""
    llm = ChatOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="qwen3:latest",
        temperature=0.1,
    )
    model_with_tools = llm.bind_tools(all_tools)

    # Add system prompt to messages
    messages = [HumanMessage(content=TRAE_AGENT_SYSTEM_PROMPT)] + state["messages"]
    response = await model_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def reflection_node(state: TraeWebState):
    """Reflection node - analyzes tool results and provides guidance."""
    tool_messages = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]

    if not tool_messages:
        return {"messages": []}

    # Check if task_done was called - if so, no reflection needed
    task_done_calls = [msg for msg in tool_messages if msg.name == "task_done"]
    if task_done_calls:
        return {"messages": []}

    # Simple reflection logic - only reflect if there are actual tool results to analyze
    last_tool_msg = tool_messages[-1]
    if "Error" in last_tool_msg.content or "already exists" in last_tool_msg.content:
        reflection = "The last tool encountered an issue. Consider checking if the file already exists with the correct content, or try a different approach like using 'edit' command instead of 'create'."
        return {"messages": [AIMessage(content=reflection)]}
    else:
        # For successful tool executions, no reflection needed - let LLM decide next steps
        return {"messages": []}


def create_custom_agent():
    """Create custom agent with reflection capabilities."""
    workflow = StateGraph(TraeWebState)

    # Add nodes
    workflow.add_node("llm_call", llm_call)
    workflow.add_node("tool_node", ToolNode(tools=all_tools))
    workflow.add_node("reflection_node", reflection_node)

    # Define edges
    workflow.add_edge(START, "llm_call")
    workflow.add_edge("llm_call", "tool_node")
    workflow.add_edge("tool_node", "reflection_node")
    workflow.add_edge("reflection_node", "llm_call")

    # Add conditional edge to end when task is done
    def should_continue(state: TraeWebState):
        """Check if task_done was called or we should continue"""
        # Check all tool messages for task_done completion
        tool_messages = [
            msg
            for msg in state["messages"]
            if isinstance(msg, ToolMessage)
            and getattr(msg, "name", None) == "task_done"
        ]

        if tool_messages:
            print(f"DEBUG: Found task_done completion, ending workflow")
            return END

        # Also check if the last message is an LLM call that includes task_done tool call
        last_message = state["messages"][-1] if state["messages"] else None
        if hasattr(last_message, "tool_calls"):
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "task_done":
                    print(f"DEBUG: Found task_done tool call, ending workflow")
                    return END

        print(f"DEBUG: No task_done found, continuing to llm_call")
        return "llm_call"

    workflow.add_conditional_edges(
        "reflection_node", should_continue, ["llm_call", END]
    )

    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


async def test_custom_agent():
    """Test the custom agent with reflection."""
    agent = create_custom_agent()

    config = {"configurable": {"thread_id": "custom-test-123"}, "recursion_limit": 50}
    initial_state = {
        "messages": [
            HumanMessage(content="Create a file called test.txt with 'hello world'")
        ],
        "remaining_steps": 10,
        "working_directory": Path(
            "/home/thomas/src/projects/copilotkit-work/test_workingdir"
        ),
    }

    print("=== Testing custom agent with reflection ===")
    try:
        async for chunk in agent.astream(
            initial_state, config=config, stream_mode="values"
        ):
            print(f"CHUNK: {chunk}")
            print("---")

        final_state = await agent.aget_state(config=config)
        print(f"FINAL STATE: {final_state}")
    except Exception as e:
        print(f"Error during streaming: {e}")


if __name__ == "__main__":
    print("Running custom agent test...")
    asyncio.run(test_custom_agent())
