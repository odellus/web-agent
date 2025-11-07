"""
Test to give main web agent a coding task and see if it uses thinking tool
"""

import asyncio
import tempfile
from pathlib import Path

from src.web_agent.agent import get_agent, WebAgentState
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver


async def test_main_agent_coding_task():
    """Test main agent with a coding task and see if it uses thinking tool."""
    print("=== Testing Main Agent with Coding Task ===")

    # Set up checkpointer
    memory = MemorySaver()
    agent = get_agent(checkpointer=memory)

    # Create config for checkpointer
    config = {"configurable": {"thread_id": "main-agent-test-123"}}

    # Create a temporary directory with some code to work with
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a Python file that needs optimization
        test_file = Path(temp_dir) / "data_processor.py"
        test_file.write_text('''
import time
import random

def process_data_slow(data):
    """Slow data processing implementation"""
    result = []
    for item in data:
        if item > 0:
            # Multiple operations in loop - inefficient
            temp = item * 2
            processed = temp + 10
            result.append(processed)
    return result

def process_data_fast(data):
    """Fast data processing implementation"""
    return [item * 2 + 10 for item in data if item > 0]

def benchmark():
    """Benchmark both implementations"""
    test_data = [random.randint(-5, 100) for _ in range(1000)]

    # Test slow version
    start = time.time()
    slow_result = process_data_slow(test_data)
    slow_time = time.time() - start

    # Test fast version
    start = time.time()
    fast_result = process_data_fast(test_data)
    fast_time = time.time() - start

    print(f"Slow version: {slow_time:.4f}s")
    print(f"Fast version: {fast_time:.4f}s")
    print(f"Speed improvement: {slow_time/fast_time:.2f}x")

    return slow_result, fast_result

if __name__ == "__main__":
    benchmark()
''')

        # Create the initial state with a coding task
        initial_state = WebAgentState(
            messages=[
                HumanMessage(
                    content=f"""
I need you to analyze and optimize this Python code.

Your task:
1. First, use the thinking tool to deeply analyze the performance implications of the two approaches
2. Identify specific optimization opportunities
3. Suggest improvements with detailed reasoning
4. Consider edge cases and maintainability
5. Provide specific code recommendations

The file to analyze is: {test_file}

Start by using the sequential thinking tool to plan your analysis approach.
            """
                )
            ],
            remaining_steps=20,  # Give it enough steps
        )

        print("Starting agent with coding task...")
        print("Initial message sent to agent:")
        print(initial_state["messages"][0].content)
        print("\n" + "=" * 80)

        # Run the agent
        step_count = 0
        async for event in agent.astream(initial_state, config=config):
            step_count += 1
            print(f"\\n=== STEP {step_count} ===")

            for node, values in event.items():
                if node == "llm_call":
                    msg = (
                        values.get("messages", [])[-1]
                        if values.get("messages")
                        else None
                    )
                    if msg is None:
                        continue
                    if hasattr(msg, "content") and msg.content:
                        print(f"🧠 LLM Response: {msg.content[:200]}...")
                    elif hasattr(msg, "tool_calls") and msg.tool_calls:
                        print(f"🛠️ Tool Calls: {[tc['name'] for tc in msg.tool_calls]}")
                elif node == "tool_node":
                    for tool_msg in values.get("messages", []):
                        if isinstance(tool_msg, ToolMessage):
                            tool_name = getattr(tool_msg, "name", "Unknown")
                            tool_content = getattr(tool_msg, "content", "No content")
                            print(f"🔧 Tool {tool_name}: {tool_content[:300]}...")

            # Stop after reasonable number of steps for testing
            if step_count >= 15:
                print("\\n⏹️ Stpping test after 15 steps")
                break

        print("\\n" + "=" * 80)
        print("AGENT TEST COMPLETE")


if __name__ == "__main__":
    asyncio.run(test_main_agent_coding_task())
