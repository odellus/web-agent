import asyncio
from typing import Annotated, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from pydantic import DirectoryPath
from pathlib import Path

from .state import ThinkingAgentState
from ..thinking_tools import (
    thinking_tool,
    web_search_tool,
    read_file_tool,
    rg_search_tool,
)


# LLM configuration
llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="qwen3:latest",
    temperature=0.1,
)

# Bind tools to LLM
llm_with_tools = llm.bind_tools(
    [thinking_tool, web_search_tool, read_file_tool, rg_search_tool]
)


# Thinking agent system prompt
THINKING_AGENT_SYSTEM_PROMPT = """You are an expert reasoning and planning AI assistant.

Your role is to break down complex problems through structured thinking and provide comprehensive analysis.

Core capabilities:
1. Structured thinking with sequential reasoning using thinking_tool
2. Web research using web_search_tool for external information
3. File analysis using read_file_tool for examining code and documentation
4. Code searching using rg_search_tool for finding patterns in the codebase

When to use each capability:
- Use thinking_tool for problem breakdown, planning, and structured reasoning
- Use web_search_tool for external research, current information, or unknown topics
- Use read_file_tool for analyzing existing files, code, or documentation
- Use rg_search_tool for searching through code files to find patterns, functions, or specific implementations

Thinking methodology:
1. Start by understanding the problem presented in the initial message
2. Use thinking_tool to break down the problem into components
3. Plan what information you need (web research, file analysis, code search)
4. Use tools to gather information when necessary
5. Synthesize findings and continue thinking process
6. Generate solution hypotheses and verify them
7. Conclude when analysis is complete

Important guidelines:
- Be thorough and methodical in your approach
- Use thinking_tool regularly to structure your reasoning
- Don't hesitate to use tools to gather information
- Maintain clear structure in your analysis
- Verify assumptions and conclusions
- Adapt your approach based on new information

If you have completed your analysis and have a comprehensive understanding/solution, you should indicate that no more thoughts are needed.
"""


def llm_call(state: ThinkingAgentState):
    """LLM decides whether to call a tool or continue thinking"""
    # Prepare messages with system prompt
    messages = [SystemMessage(content=THINKING_AGENT_SYSTEM_PROMPT)]

    # Add any existing context
    if state.get("problem_context"):
        messages.append(
            SystemMessage(content=f"Problem Context: {state['problem_context']}")
        )

    # Add conversation history
    messages.extend(state.get("messages", []))

    resp = llm_with_tools.invoke(messages)

    # Update thought tracking
    current_thought = state.get("current_thought_number", 1)
    total_thoughts = state.get("total_thoughts", 5)

    # Check if this is a thinking completion signal
    if (
        "no more thoughts" in resp.content.lower()
        or "analysis complete" in resp.content.lower()
    ):
        return {
            "messages": [resp],
            "thoughts_completed": True,
            "next_thought_needed": False,
        }

    return {
        "messages": [resp],
        "current_thought_number": current_thought + 1,
        "next_thought_needed": True,
    }


def should_continue(state: ThinkingAgentState) -> Literal["tool_node", END, "llm_call"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    # Check if thinking is complete
    if state.get("thoughts_completed", False):
        return END

    # Check max thoughts limit
    current_thought = state.get("current_thought_number", 1)
    max_thoughts = state.get("max_thoughts", 25)
    if current_thought > max_thoughts:
        return END

    messages = state.get("messages", [])
    if not messages:
        return "llm_call"

    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we continue the thinking process
    return "llm_call"


def get_thinking_agent(checkpointer=None):
    """Build the thinking agent workflow"""
    agent_builder = StateGraph(ThinkingAgentState)

    # Add nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node(
        "tool_node",
        ToolNode(
            tools=[thinking_tool, web_search_tool, read_file_tool, rg_search_tool]
        ),
    )

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call", should_continue, ["tool_node", "llm_call", END]
    )
    agent_builder.add_edge("tool_node", "llm_call")

    return agent_builder.compile(checkpointer=checkpointer)


# Helper function to run thinking agent
async def run_thinking_agent(
    initial_message: str,
    problem_context: Optional[str] = None,
    max_thoughts: int = 15,
    working_directory: Optional[DirectoryPath] = None,
    checkpointer=None,
) -> str:
    """Run the thinking agent with initial message and return the final response"""

    # Initialize state
    initial_state = ThinkingAgentState(
        messages=[HumanMessage(content=initial_message)],
        problem_context=problem_context,
        current_thought_number=1,
        total_thoughts=max_thoughts,
        max_thoughts=max_thoughts,
        working_directory=working_directory,
        next_thought_needed=True,
        thoughts_completed=False,
    )

    # Get agent
    agent = get_thinking_agent(checkpointer)

    # Run agent
    async for event in agent.astream(initial_state):
        for node, values in event.items():
            if node == "llm_call":
                print(f"🧠 Thinking step: {values['messages'][-1].content[:100]}...")
            elif node == "tool_node":
                for tool_msg in values.get("messages", []):
                    if isinstance(tool_msg, ToolMessage):
                        print(f"🔧 Tool used: {tool_msg.name}")

    # Return final response
    final_state = agent.get_state(agent.config)
    if final_state.messages:
        return final_state.messages[-1].content
    return "No response generated"
