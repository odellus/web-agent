import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import DirectoryPath
from web_agent.agent import create_custom_agent
from pathlib import Path
from web_agent.config import settings
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

langfuse = Langfuse(
    public_key=settings.langfuse_public_key.get_secret_value(),
    secret_key=settings.langfuse_secret_key.get_secret_value(),
    host=settings.langfuse_host,
)
langfuse_handler = CallbackHandler()


async def test_custom_agent():
    """Test the custom agent with reflection."""
    checkpointer = MemorySaver()
    agent = create_custom_agent(checkpointer=checkpointer)

    config = {
        "configurable": {"thread_id": "custom-test-123"},
        "recursion_limit": 50,
        "callbacks": [langfuse_handler],
    }
    initial_state = {
        "messages": [
            HumanMessage(
                # content="Create a file called test.txt with 'hello world'. Then rename it. Then edit it to say goodbye world."
                content="Use sequential thinking tool extensively and bash to review current working directory and create an AGENTS.md that describes the overall structure of the project and its purpose."
            )
        ],
        "remaining_steps": 50,
        "working_directory": Path(
            "/home/thomas/src/projects/copilotkit-work/test_workingdir"
        ),
    }

    print("=== Testing custom agent with reflection ===")
    try:
        async for chunk in agent.astream(
            initial_state, config=config, stream_mode="values"
        ):
            print(f"REMAINING_STEPS: {chunk.get('remaining_steps')}")
            print(f"LAST_MESSAGE: {chunk.get('messages', [''])[-1]}")
            # print("---")
            pass

        final_state = await agent.aget_state(config=config)
        # print(f"FINAL STATE: {final_state}")
    except Exception as e:
        print(f"Error during streaming: {e}")


if __name__ == "__main__":
    print("Running custom agent test...")
    asyncio.run(test_custom_agent())
