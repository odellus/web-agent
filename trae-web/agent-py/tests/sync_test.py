"""Test agent invocation."""

import asyncio
from langchain_core.messages import HumanMessage
from trae_web.agent import create_ide_agent


async def test_agent_invoke():
    """Test that agent can be invoked."""
    agent = create_ide_agent()

    # Provide config with thread_id
    config = {"configurable": {"thread_id": "test-thread-123"}}

    # Simple test message
    initial_state = {
        "messages": [
            HumanMessage(
                content="please create a file called HAHAHA.md and write in it a joke"
            )
        ],
        "remaining_steps": 5,
    }

    try:
        # Test both sync and async
        print("=== Testing Synchronous Invocation ===")
        result = agent.invoke(initial_state, config=config)
        print("✓ Synchronous agent invoke works")
        print(f"Result message count: {len(result['messages'])}")

        # Print the last message content
        if result["messages"]:
            last_message = result["messages"][-1]
            print(f"Last message: {last_message.content[:200]}...")

        print("\n=== Testing Asynchronous Invocation ===")
        result = await agent.ainvoke(initial_state, config=config)
        print("✓ Asynchronous agent invoke works")
        print(f"Result message count: {len(result['messages'])}")

        # Print the last message content
        if result["messages"]:
            last_message = result["messages"][-1]
            print(f"Last message: {last_message.content[:200]}...")

        return result
    except Exception as e:
        print(f"✗ Agent invoke failed: {e}")
        raise


if __name__ == "__main__":
    print("Testing trae-web agent invocation...")
    asyncio.run(test_agent_invoke())
    print("\n✅ All tests passed!")
