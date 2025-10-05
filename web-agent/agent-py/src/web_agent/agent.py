import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from pydantic import DirectoryPath
from web_agent.state import WebAgentState

from web_agent.tools import all_tools
from pathlib import Path


llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="qwen3:latest",
    temperature=0.1,
)
model_with_tools = llm.bind_tools(all_tools)

# TRAE Agent system prompt (simplified for testing)
TRAE_AGENT_SYSTEM_PROMPT = """You are an expert AI software engineering agent.

File Path Rule: All tools that take a `file_path` as an argument require an **absolute path**. You MUST construct the full, absolute path by combining the `[Project root path]` provided in the user's message with the file's path inside the project.

For example, if the project root is `/home/user/my_project` and you need to edit `src/main.py`, the correct `file_path` argument is `/home/user/my_project/src/main.py`. Do NOT use relative paths like `src/main.py`.

Your primary goal is to resolve a given GitHub issue by navigating the provided codebase, identifying the root cause of the bug, implementing a robust fix, and ensuring your changes are safe and well-tested.

Follow these steps methodically:

1.  Understand the Problem:
    - Begin by carefully reading the user's problem description to fully grasp the issue.
    - Identify the core components and expected behavior.

2.  Explore and Locate:
    - Use the available tools to explore the codebase.
    - Locate the most relevant files (source code, tests, examples) related to the bug report.

3.  Reproduce the Bug (Crucial Step):
    - Before making any changes, you **must** create a script or a test case that reliably reproduces the bug. This will be your baseline for verification.
    - Analyze the output of your reproduction script to confirm your understanding of the bug's manifestation.

4.  Debug and Diagnose:
    - Inspect the relevant code sections you identified.
    - If necessary, create debugging scripts with print statements or use other methods to trace the execution flow and pinpoint the exact root cause of the bug.

5.  Develop and Implement a Fix:
    - Once you have identified the root cause, develop a precise and targeted code modification to fix it.
    - Use the provided file editing tools to apply your patch. Aim for minimal, clean changes.

6.  Verify and Test Rigorously:
    - Verify the Fix: Run your initial reproduction script to confirm that the bug is resolved.
    - Prevent Regressions: Execute the existing test suite for the modified files and related components to ensure your fix has not introduced any new bugs.
    - Write New Tests: Create new, specific test cases (e.g., using `pytest`) that cover the original bug scenario. This is essential to prevent the bug from recurring in the future. Add these tests to the codebase.
    - Consider Edge Cases: Think about and test potential edge cases related to your changes.

7.  Summarize Your Work:
    - Conclude your trajectory with a clear and concise summary. Explain the nature of the bug, the logic of your fix, and the steps you took to verify its correctness and safety.

**Guiding Principle:** Act like a senior software engineer. Prioritize correctness, safety, and high-quality, test-driven development.

# GUIDE FOR HOW TO USE "sequential_thinking" TOOL:
- Your thinking should be thorough and so it's fine if it's very long. Set total_thoughts to at least 5, but setting it up to 25 is fine as well. You'll need more total thoughts when you are considering multiple possible solutions or root causes for an issue.
- Use this tool as much as you find necessary to improve the quality of your answers.
- You can run bash commands (like tests, a reproduction script, or 'grep'/'find' to find relevant context) in between thoughts.
- The sequential_thinking tool can help you break down complex problems, analyze issues step-by-step, and ensure a thorough approach to problem-solving.
- Don't hesitate to use it multiple times throughout your thought process to enhance the depth and accuracy of your solutions.

If you are sure the issue has been solved, you should call the `task_done` to finish the task.
"""


async def llm_call(state: WebAgentState):
    """LLM call node - invokes the model with tools."""

    # Add system prompt to messages
    messages = [SystemMessage(content=TRAE_AGENT_SYSTEM_PROMPT)] + state["messages"]
    response = await model_with_tools.ainvoke(messages)
    remaining_steps = state.get("remaining_steps", 0)
    return {"messages": [response], "remaining_steps": remaining_steps - 1}


async def reflection_node(state: WebAgentState):
    """Reflection node - analyzes tool results and provides guidance."""
    tool_messages = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
    print(tool_messages)
    # Nothing to reflect on, passing empty list to messages adds nothing to
    # the conversation history, so we can safely ignore it.
    if not tool_messages:
        return {"messages": []}

    # Check if task_done was called - if so, no reflection needed
    task_done_calls = [msg for msg in tool_messages if msg.name == "task_done"]
    if task_done_calls:
        return {"messages": []}

    # Simple reflection logic - only reflect if there are actual tool results to analyze
    last_tool_msg = tool_messages[-1]
    if "Error" in last_tool_msg.content or "STDERR" in last_tool_msg.content:
        reflection = last_tool_msg.content
        return {"messages": [AIMessage(content=reflection)]}
    else:
        # For successful tool executions, no reflection needed - let LLM decide next steps
        return {"messages": []}


async def should_continue(state: WebAgentState):
    """Check if task_done was called or we should continue"""

    remaining_steps = state.get("remaining_steps", 0)
    if remaining_steps <= 0:
        return END

    # Check all tool messages for task_done completion
    tool_messages = [
        msg
        for msg in state["messages"]
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "task_done"
    ]

    if tool_messages:
        print(f"DEBUG: Found task_done completion, ending workflow")
        return END

    # Also check if the last message is an LLM call that includes task_done tool call
    last_message = state["messages"][-1] if state["messages"] else None
    if hasattr(last_message, "tool_calls"):
        for tool_call in last_message.tool_calls:
            print(tool_call["name"])
            if tool_call["name"] == "task_done":
                print(f"DEBUG: Found task_done tool call, ending workflow")
                return END

    print(f"DEBUG: No task_done found, continuing to llm_call")
    return "llm_call"


def create_custom_agent(checkpointer):
    """Create custom agent with reflection capabilities."""
    workflow = StateGraph(WebAgentState)

    # Add nodes
    workflow.add_node("llm_call", llm_call)
    workflow.add_node(
        "tool_node",
        ToolNode(
            tools=all_tools,
        ),
    )
    workflow.add_node("reflection_node", reflection_node)

    # Define edges
    workflow.add_edge(START, "llm_call")
    workflow.add_edge("llm_call", "tool_node")
    workflow.add_edge("tool_node", "reflection_node")
    # workflow.add_edge("reflection_node", "llm_call")

    # Add conditional edge to end when task is done

    workflow.add_conditional_edges(
        "reflection_node", should_continue, ["llm_call", END]
    )

    # Compile with memory
    return workflow.compile(checkpointer=checkpointer)
