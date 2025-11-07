import asyncio
from typing import Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from pydantic import DirectoryPath
from web_agent.state import WebAgentState

from web_agent.tools import all_tools
from pathlib import Path
from pydantic import DirectoryPath, BaseModel
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from copilotkit import CopilotKitState
from pathlib import Path
import matplotlib.pyplot as plt
from web_agent.state import WebAgentState
from web_agent.tools import all_tools
from web_agent.config import settings
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

llm = ChatOpenAI(
    base_url="http://192.168.1.175:1234/v1",
    api_key="lm-studio",
    model="glm-4.5-air@q4_k_m",
    temperature=0.1,
)


model_with_tools = llm.bind_tools(all_tools)

# Agent system prompt
AGENT_SYSTEM_PROMPT = """You are an expert AI software engineering agent.

File Path Rule: All tools that take a `file_path` as an argument require an **relative path**.

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


llm_with_tools = llm.bind_tools(all_tools)


# Nodes
def llm_call(state: WebAgentState):
    """LLM decides whether to call a tool or not"""
    sys_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
    resp = llm_with_tools.invoke([sys_msg] + state["messages"])
    remaining_steps = state["remaining_steps"] - 1
    return {
        "messages": [resp],
        "remaining_steps": remaining_steps,
    }


# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: WebAgentState) -> Literal["tool_node", END, "llm_call"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    task_done_messages = [
        msg
        for msg in messages
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "task_done"
    ]
    if task_done_messages:
        return END

    if state["remaining_steps"] <= 0:
        return END

    last_message = messages[-1]
    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"
    # Otherwise, we keep it going because this is trae-agent style. we either have to run out of step or call task_done to quit.
    return "llm_call"


def get_agent(checkpointer):
    """Build the agent workflow"""
    agent_builder = StateGraph(WebAgentState)

    # Add nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", ToolNode(tools=all_tools))

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call", should_continue, ["llm_call", "tool_node", END]
    )
    agent_builder.add_edge("tool_node", "llm_call")
    return agent_builder.compile(checkpointer=checkpointer)
