#!/usr/bin/env python3
"""Comprehensive test showing thinking agent workflow with tool usage."""

import asyncio
import tempfile
from pathlib import Path

from src.web_agent.tools.thinking_agent.agent import (
    get_thinking_agent,
    ThinkingAgentState,
)
from src.web_agent.tools.thinking_tools import all_tools as thinking_agent_tools
from langchain_core.messages import HumanMessage


def test_complete_thinking_workflow():
    """Test the complete thinking agent workflow."""
    print("=== Testing Complete Thinking Agent Workflow ===")

    # Create a temporary directory for file operations
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        test_file = Path(temp_dir) / "performance_guide.py"
        test_file.write_text("""def slow_function():
    result = []
    for i in range(1000):
        result.append(i * 2)
    return result

def fast_function():
    return [i * 2 for i in range(1000)]""")

        # Create the thinking agent
        agent = get_thinking_agent()

        # Create initial state
        initial_state = ThinkingAgentState(
            messages=[
                HumanMessage(
                    content="I need to analyze this Python code and provide optimization recommendations. The goal is to understand performance bottlenecks and suggest improvements.\n\nPlease:\n1. Use the read_file tool to examine the code in detail\n2. Use the rg_search tool to find any patterns or issues\n3. Use the thinking tool to structure your analysis\n4. Provide concrete optimization recommendations"
                )
            ],
            problem_context="Python performance optimization analysis",
            current_thought_number=1,
            total_thoughts=10,
            max_thoughts=15,
            next_thought_needed=True,
            thoughts_completed=False,
            working_directory=temp_dir,
        )

        print("Starting thinking agent workflow...")
        print(f"Working directory: {temp_dir}")
        print()

        # Run the agent step by step to see the workflow
        step_count = 0
        for event in agent.astream(initial_state):
            step_count += 1
            print(f"Step {step_count}:")

            for node_name, node_data in event.items():
                if node_name == "llm_call":
                    # Show LLM response
                    if node_data.get("messages"):
                        last_msg = node_data["messages"][-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            print(f"  LLM Response: {last_msg.content[:200]}...")
                        elif hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            print(
                                f"  Tool calls: {[tc['name'] for tc in last_msg.tool_calls]}"
                            )

                elif node_name == "tool_node":
                    # Show tool results
                    if node_data.get("messages"):
                        for tool_msg in node_data["messages"]:
                            if hasattr(tool_msg, "name") and hasattr(
                                tool_msg, "content"
                            ):
                                print(
                                    f"  Tool {tool_msg.name}: {tool_msg.content[:150]}..."
                                )

            print()

            # Stop after reasonable steps for demonstration
            if step_count >= 8:
                print("Stopping workflow for demonstration...")
                break

        # Get final state
        final_state = agent.get_state(agent.config)
        print("=== FINAL STATE ===")
        print(f"Total steps taken: {step_count}")
        print(f"Thoughts completed: {final_state.get('thoughts_completed', False)}")
        print(f"Current thought: {final_state.get('current_thought_number', 0)}")

        if final_state.get("messages"):
            print("Final response:")
            final_msg = final_state["messages"][-1]
            if hasattr(final_msg, "content") and final_msg.content:
                print(final_msg.content)
            else:
                print("No final content generated")


def test_individual_tools():
    """Test individual tools to verify they work."""
    print("\n=== Testing Individual Tools ===")

    from src.web_agent.tools.thinking_tools import (
        thinking_tool,
        read_file_tool,
        rg_search_tool,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("""
def hello_world():
    print("Hello, World!")
    return "success"

def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total

def optimize_this():
    # This function needs optimization
    result = []
    for i in range(1000):
        result.append(i * 2)
    return sum(result)
""")

        print("1. Testing thinking tool:")
        thinking_result = thinking_tool.invoke(
            {
                "thought": "Analyzing Python performance optimization opportunities",
                "thought_number": 1,
                "total_thoughts": 5,
                "next_thought_needed": True,
                "analysis_type": "code_analysis",
                "confidence_level": 8,
            }
        )
        print(f"   Result: {thinking_result[:100]}...")

        print("\n2. Testing read file tool:")
        read_result = read_file_tool.invoke(
            {
                "file_path": "test.py",
                "working_directory": temp_dir,
            }
        )
        print(f"   First few lines: {read_result.split(chr(10))[:3]}")

        print("\n3. Testing rg search tool:")
        rg_result = rg_search_tool.invoke(
            {
                "pattern": "def",
                "path": ".",
                "working_directory": temp_dir,
            }
        )
        print(f"   Found functions: {'def' in rg_result}")


if __name__ == "__main__":
    test_individual_tools()
    test_complete_thinking_workflow()
    print("\n🎉 Workflow test completed!")
