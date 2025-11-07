"""
Simple test to give main web agent a coding task with direct code content
"""

import asyncio
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.web_agent.agent import get_agent, WebAgentState
from langchain_core.messages import ToolMessage


async def test_main_agent_simple():
    """Test main agent with a coding task using direct code content."""
    print("=== Testing Main Agent with Direct Code Content ===")

    # Set up checkpointer
    memory = MemorySaver()
    agent = get_agent(checkpointer=memory)

    # Create config for checkpointer
    config = {"configurable": {"thread_id": "simple-test-123"}}

    # The code to analyze directly in the prompt
    code_content = '''
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
'''

    # Create the initial state with a coding task and direct code content
    initial_state = WebAgentState(
        messages=[
            HumanMessage(
                content=f"""
Analyze and optimize this Python code:

```python
{code_content}
```

Your task:
1. Use the sequential thinking tool to deeply analyze the performance implications
2. Identify specific optimization opportunities
3. Suggest improvements with detailed reasoning
4. Consider edge cases and maintainability
5. Provide specific code recommendations

Start by using the sequential thinking tool to plan your analysis approach.
                """
            )
        ],
        remaining_steps=20,  # Give it enough steps
    )

    print("Starting agent with coding task...")
    print("Initial message sent to agent (first 500 chars):")
    print(initial_state["messages"][0].content[:500] + "...")
    print("\n" + "=" * 80)

    # Run the agent
    step_count = 0
    tool_calls_count = 0
    thinking_tool_used = False

    async for event in agent.astream(initial_state, config=config):
        step_count += 1
        print(f"\n=== STEP {step_count} ===")

        for node, values in event.items():
            if node == "llm_call":
                msg = values.get("messages", [])[-1] if values.get("messages") else None
                if msg is None:
                    continue

                if hasattr(msg, "content") and msg.content:
                    print(f"🧠 LLM Response: {msg.content[:200]}...")
                elif hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_names = [tc["name"] for tc in msg.tool_calls]
                    print(f"🛠️ Tool Calls: {tool_names}")
                    tool_calls_count += 1
                    if "sequential_thinking_tool" in tool_names:
                        thinking_tool_used = True
            elif node == "tool_node":
                for tool_msg in values.get("messages", []):
                    if isinstance(tool_msg, ToolMessage):
                        tool_name = getattr(tool_msg, "name", "Unknown")
                        tool_content = getattr(tool_msg, "content", "No content")
                        print(f"🔧 Tool {tool_name}: {tool_content[:300]}...")
                        if tool_name == "sequential_thinking_tool":
                            thinking_tool_used = True

        # Stop after reasonable number of steps for testing
        if step_count >= 12:
            print(f"\n⏹️ Stopping test after {step_count} steps")
            break

    print("\n" + "=" * 80)
    print("AGENT TEST COMPLETE")
    print(f"Total steps: {step_count}")
    print(f"Tool calls made: {tool_calls_count}")
    print(f"Thinking tool used: {'YES' if thinking_tool_used else 'NO'}")

    if thinking_tool_used:
        print("✅ SUCCESS: Agent chose to use the thinking tool!")
    else:
        print("❌ The agent did not use the thinking tool")


if __name__ == "__main__":
    asyncio.run(test_main_agent_simple())
