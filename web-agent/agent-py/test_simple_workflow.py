#!/usr/bin/env python3
"""Simple test for thinking agent workflow."""

import tempfile
from pathlib import Path

from src.web_agent.tools.thinking_agent.agent import llm_call, ThinkingAgentState
from src.web_agent.tools.thinking_tools import (
    thinking_tool,
    read_file_tool,
    rg_search_tool,
)
from langchain_core.messages import HumanMessage


def test_thinking_workflow():
    """Test the thinking agent workflow step by step."""
    print("=== Testing Thinking Agent Workflow ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("""def slow_function():
    result = []
    for i in range(1000):
        result.append(i * 2)
    return result

def fast_function():
    return [i * 2 for i in range(1000)]""")

        # Create initial state
        state = ThinkingAgentState(
            messages=[
                HumanMessage(
                    content="Analyze this Python code and provide optimization recommendations. Use the tools to examine the code and structure your analysis."
                )
            ],
            problem_context="Python performance optimization",
            current_thought_number=1,
            total_thoughts=5,
            working_directory=temp_dir,
        )

        print("Starting analysis...")
        print(f"Working directory: {temp_dir}")
        print()

        # Run workflow manually
        for step in range(5):  # Limit steps for demo
            print(f"Step {step + 1}:")

            # Call LLM
            result = llm_call(state)
            state = {**state, **result}

            # Show results
            if result.get("messages"):
                last_msg = result["messages"][-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    print(f"  LLM: {last_msg.content[:100]}...")
                elif hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    tool_calls = last_msg.tool_calls
                    print(f"  Tool calls: {[tc['name'] for tc in tool_calls]}")

                    # Execute tools
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["function"]["arguments"]

                        if tool_name == "thinking_tool":
                            result = thinking_tool.invoke(tool_args)
                            print(f"    Thinking result: {result[:80]}...")
                        elif tool_name == "read_file_tool":
                            result = read_file_tool.invoke(tool_args)
                            print(
                                f"    Read file: {result.split(chr(10))[1] if result else 'No content'}"
                            )
                        elif tool_name == "rg_search_tool":
                            result = rg_search_tool.invoke(tool_args)
                            print(
                                f"    RG search: {'Found matches' if result else 'No matches'}"
                            )

            # Check if completed
            if result.get("thoughts_completed"):
                print("  Workflow completed!")
                break

            print()

            # Update state for next iteration
            if result.get("messages"):
                state["messages"].extend(result.get("messages", []))
            state["current_thought_number"] = state.get("current_thought_number", 1) + 1

        print("\n=== Final Results ===")
        if state.get("messages"):
            final_msg = state["messages"][-1]
            if hasattr(final_msg, "content") and final_msg.content:
                print("Final analysis:")
                print(final_msg.content)


if __name__ == "__main__":
    test_thinking_workflow()
    print("\n✅ Workflow test completed!")
