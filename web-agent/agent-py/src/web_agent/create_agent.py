import asyncio
from typing import Annotated, TypedDict
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
from langchain_core.tools.base import BaseTool
from copilotkit import CopilotKitState
from pathlib import Path
import matplotlib.pyplot as plt
from web_agent.state import WebAgentState
from web_agent.tools import task_done
from web_agent.config import settings
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langgraph.memory import MemorySaver


async def create_code_agent(
    llm: ChatOpenAI,
    prompt: str,
    tools: list[BaseTool],
    graph_state: TypedDict,
    checkpointer: AsyncPostgresSaver | MemorySaver,
):
    """Create a code agent with the given parameters."""
    assert "remaining_steps" in graph_state.__annotations__, (
        "Missing 'remaining_steps' annotation in state"
    )
    assert "messages" in graph_state.__annotations__, (
        "Missing 'messages' annotation in state"
    )
    assert "working_directory" in graph_state.__annotations__, (
        "Missing 'working_directory' annotation in state"
    )

    tools_by_name = {tool.name: tool for tool in tools}
    if "task_done" not in tools_by_name:
        print("Adding task_done tool!")
        tools.append(task_done)
        tools_by_name["task_done"] = task_done
    llm_with_tools = llm.bind_tools(tools)

    # Nodes
    async def llm_call(state):
        """LLM decides whether to call a tool or not"""
        sys_msg = SystemMessage(content=prompt)
        resp = await llm_with_tools.ainvoke([sys_msg] + state["messages"])
        remaining_steps = state["remaining_steps"] - 1
        return {
            "messages": [resp],
            "remaining_steps": remaining_steps,
        }

    # Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
    async def should_continue(state) -> Literal["tool_node", END, "llm_call"]:
        """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

        messages = state["messages"]
        task_done_messages = [
            msg
            for msg in messages
            if isinstance(msg, ToolMessage)
            and getattr(msg, "name", None) == "task_done"
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

    """Build the agent workflow"""
    agent_builder = StateGraph(graph_state)

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
