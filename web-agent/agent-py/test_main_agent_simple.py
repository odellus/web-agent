"""
Simple test to give main web agent a coding task with direct code content
"""

import asyncio
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.web_agent.agent import get_agent, WebAgentState
from src.web_agent.config import settings
from langchain_core.messages import ToolMessage

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

langfuse = Langfuse(
    public_key=settings.langfuse_public_key.get_secret_value(),
    secret_key=settings.langfuse_secret_key.get_secret_value(),
    host=settings.langfuse_host,
)
langfuse_handler = CallbackHandler()


async def test_main_agent_simple():
    """Test main agent with a coding task using direct code content."""
    print("=== Testing Main Agent with Direct Code Content ===")

    # Set up checkpointer
    memory = MemorySaver()
    agent = get_agent(checkpointer=memory)

    # Create config for checkpointer
    config = {
        "configurable": {"thread_id": "simple-test-123"},
        "callbacks": [langfuse_handler],
    }

    # The code to analyze directly in the prompt

    # Create the initial state with working directory and project analysis task
    initial_state = WebAgentState(
        messages=[
            HumanMessage(
                content=f"""
Understand the project structure in the working directory and write a comprehensive summary.

Your task:
1. Use the sequential thinking tool to plan your analysis approach
2. Explore the project structure systematically
3. Identify key components and their purposes
4. Analyze the architecture and organization
5. Provide a detailed summary of what this project does and how it's structured

Working directory: /home/thomas/src/projects/copilotkit-work/test_workingdir

Start by using the sequential thinking tool to plan your analysis approach.

Finish by writing a summary of your findings in SUMMARY.md please.
                """
            )
        ],
        remaining_steps=20,  # Give it enough steps
        working_directory="/home/thomas/src/projects/copilotkit-work/test_workingdir",
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
