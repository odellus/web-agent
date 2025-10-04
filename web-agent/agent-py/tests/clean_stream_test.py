"""Clean streaming test - no truncation, no sync tests, just full async streaming."""

import asyncio
from langchain_core.messages import HumanMessage
from web_agent.agent import create_ide_agent


async def test_clean_streaming():
    """Test agent streaming with full output - no truncation."""
    agent = create_ide_agent()

    config = {"configurable": {"thread_id": "test-thread-123"}}
    message = (
        """run echo 'Hello, world' > hello_world.txt and verify it worked please"""
    )
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "remaining_steps": 5,
    }

    print("=== Streaming with 'values' mode ===")
    try:
        async for chunk in agent.astream(
            initial_state, config=config, stream_mode="values"
        ):
            print(f"CHUNK: {chunk}")
            print("---")

        s = await agent.aget_state(config=config)
        print(f"STATE: {s}")
    except Exception as e:
        print(f"Error: {e}")

    # print("\n=== Streaming with 'updates' mode ===")
    # try:
    #     async for chunk in agent.astream(
    #         initial_state, config=config, stream_mode="messages"
    #     ):
    #         print(f"CHUNK: {chunk}")
    #         print("---")
    # except Exception as e:
    #     print(f"Error: {e}")


if __name__ == "__main__":
    print("Testing clean streaming...")
    asyncio.run(test_clean_streaming())
