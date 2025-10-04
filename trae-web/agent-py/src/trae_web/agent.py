from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from trae_web.tools import all_tools
from trae_web.state import TraeWebState


def create_ide_agent(
    model: str = "qwen3:latest",
    temperature: float = 0.1,
):
    """Create an IDE agent using LangGraph's prebuilt react agent"""

    # Initialize LLM with system message
    llm = ChatOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model=model,
        temperature=temperature,
    )

    # Bind tools to LLM
    model_with_tools = llm.bind_tools(all_tools)

    # Compile with memory
    memory = MemorySaver()

    # Create react agent with custom state
    agent = create_react_agent(
        model=model_with_tools,
        tools=all_tools,
        state_schema=TraeWebState,
        checkpointer=memory,
    )

    return agent


# Create default agent instance
ide_agent = create_ide_agent()
