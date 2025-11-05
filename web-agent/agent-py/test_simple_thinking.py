#!/usr/bin/env python3
"""Simple test for thinking agent that actually uses the LLM."""

from src.web_agent.tools.thinking_agent.agent import llm, llm_with_tools
from src.web_agent.tools.thinking_tools import (
    thinking_tool,
    web_search_tool,
    read_file_tool,
    rg_search_tool,
)


def test_llm_without_tools():
    """Test LLM without tools to make sure it works."""
    print("=== Testing LLM Without Tools ===")

    result = llm.invoke("How do I optimize Python performance? Keep it brief.")
    print("Response:", result.content)
    print()


def test_llm_with_tools():
    """Test LLM with tools."""
    print("=== Testing LLM With Tools ===")

    try:
        result = llm_with_tools.invoke(
            "How do I optimize Python performance? Keep it brief."
        )
        print("Response:", result.content or "EMPTY RESPONSE")
        print()
    except Exception as e:
        print("Error:", e)
        print()


def test_simple_thinking():
    """Test the thinking agent functionality."""
    print("=== Testing Simple Thinking Agent ===")

    from src.web_agent.tools.thinking_agent.state import ThinkingAgentState
    from src.web_agent.tools.thinking_agent.agent import llm_call
    from langchain_core.messages import HumanMessage

    # Create simple test state
    state = ThinkingAgentState(
        messages=[HumanMessage(content="How do I optimize Python performance?")],
        problem_context="Performance optimization question",
        current_thought_number=1,
        total_thoughts=3,
    )

    # Test the LLM call function
    result = llm_call(state)
    print("LLM Call Result:", result)
    print("Messages:", result.get("messages", []))
    print()


if __name__ == "__main__":
    test_llm_without_tools()
    test_llm_with_tools()
    test_simple_thinking()
