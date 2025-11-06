import asyncio
import logging
from datetime import datetime
from typing import Annotated, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from pydantic import DirectoryPath
from pathlib import Path

from .state import ThinkingAgentState
from ..thinking_tools import (
    thinking_tool,
    web_search_tool,
    read_file_tool,
    rg_search_tool,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("thinking_agent.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


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

If you have completed your analysis and have a comprehensive understanding/solution, you should indicate that you're finished.
"""


def is_thinking_complete(content: str) -> bool:
    """Check if thinking is complete based on content."""
    complete_indicators = [
        "no more thoughts needed",
        "analysis complete",
        "thinking complete",
        "finished analysis",
        "concluded",
        "no further analysis needed",
        "task completed",
        "solution complete",
    ]

    content_lower = content.lower()
    return any(indicator in content_lower for indicator in complete_indicators)


def llm_call(state: ThinkingAgentState):
    """LLM decides whether to call a tool or continue thinking"""
    logger.info(
        f"LLM call - Thought {state.get('current_thought_number', 1)}/{state.get('total_thoughts', 5)}"
    )

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
    logger.info(f"LLM response length: {len(resp.content)} characters")

    # Update thought tracking
    current_thought = state.get("current_thought_number", 1)
    total_thoughts = state.get("total_thoughts", 5)

    # Check if this is a thinking completion signal
    if is_thinking_complete(resp.content):
        logger.info("Thinking completed - final response generated")
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
        logger.info("Stopping - thinking completed")
        return END

    # Check max thoughts limit
    current_thought = state.get("current_thought_number", 1)
    max_thoughts = state.get("max_thoughts", 25)
    if current_thought > max_thoughts:
        logger.warning(f"Stopping - max thoughts ({max_thoughts}) reached")
        return END

    messages = state.get("messages", [])
    if not messages:
        return "llm_call"

    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        logger.info(
            f"Tool calls detected: {[tc['name'] for tc in last_message.tool_calls]}"
        )
        return "tool_node"

    # Otherwise, we continue the thinking process
    return "llm_call"


def get_thinking_agent(checkpointer=None):
    """Build the thinking agent workflow"""
    logger.info("Creating thinking agent")
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

    agent = agent_builder.compile(checkpointer=checkpointer)
    logger.info("Thinking agent created successfully")
    return agent


# Helper function to run thinking agent
async def run_thinking_agent(
    initial_message: str,
    problem_context: Optional[str] = None,
    max_thoughts: int = 15,
    working_directory: Optional[DirectoryPath] = None,
) -> str:
    """Run the thinking agent with initial message and return the final response"""
    logger.info(f"Starting thinking agent session - max thoughts: {max_thoughts}")

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

    # Use MemorySaver for checkpointer
    from langgraph.checkpoint.memory import MemorySaver

    memory = MemorySaver()
    agent = get_thinking_agent(checkpointer=memory)

    # Run agent with proper config for checkpointer
    config = {"configurable": {"thread_id": "test-thread-123"}}
    step_count = 0
    async for event in agent.astream(initial_state, config=config):
        step_count += 1
        logger.info(f"Step {step_count}")

        for node, values in event.items():
            if node == "llm_call":
                msg = values["messages"][-1]
                logger.info(f"🧠 LLM response: {msg.content[:200]}...")
            elif node == "tool_node":
                for tool_msg in values.get("messages", []):
                    if isinstance(tool_msg, ToolMessage):
                        logger.info(
                            f"🔧 Tool {tool_msg.name}: {tool_msg.content[:100]}..."
                        )

    # Return final response
    final_state = agent.get_state(config)
    if (
        final_state
        and hasattr(final_state, "values")
        and final_state.values.get("messages")
    ):
        final_content = final_state.values["messages"][-1].content
        logger.info(f"Session completed - final response length: {len(final_content)}")
        return final_content
    else:
        logger.warning("No response generated")
        return "No response generated"


# Enhanced thinking tool that uses LLM
@tool
def enhanced_thinking_tool(
    problem_description: str,
    thinking_context: str = "",
    analysis_approach: str = "general_analysis",
    max_thoughts: int = 5,
) -> str:
    """Enhanced thinking tool that uses LLM for structured reasoning.

    Args:
        problem_description: The problem to analyze
        thinking_context: Additional context for the thinking process
        analysis_approach: Type of analysis to perform
        max_thoughts: Maximum number of thinking steps
    """

    thinking_prompt = f"""Please analyze the following problem using structured thinking:

Problem: {problem_description}

Context: {thinking_context}

Analysis Approach: {analysis_approach}

Please use the thinking_tool to structure your analysis and provide insights.
Think through this systematically and use the tools available to you if needed."""

    # Create temporary state for LLM call
    temp_state = ThinkingAgentState(
        messages=[HumanMessage(content=thinking_prompt)],
        problem_context=thinking_context,
        current_thought_number=1,
        total_thoughts=max_thoughts,
        max_thoughts=max_thoughts,
    )

    # Call LLM directly
    response = llm.invoke(
        [
            SystemMessage(content="You are a structured thinking expert."),
            HumanMessage(content=thinking_prompt),
        ]
    )

    return f"""ENHANCED THINKING RESULT:
{response.content}

---
This analysis was generated using LLM-based structured thinking.
"""
