from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.checkpoint.memory import MemorySaver
from copilotkit import CopilotKitState

from trae_web.tools import all_tools


def create_ide_agent(
    model: str = "hf.co/unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q4_K_M",
    temperature: float = 0.1,
):
    """Create an IDE agent with trae-agent tools converted to LangChain"""

    # Initialize LLM
    llm = ChatOpenAI(
        base_url="http://192.168.1.186:11434/v1",
        api_key="ollama",
        model=model,
        temperature=temperature,
    )

    # System prompt for IDE agent
    system_prompt = """You are an expert software engineering assistant specialized in IDE operations.

Available Tools:
- bash: Execute shell commands in persistent bash session
- str_replace_based_edit_tool: File and directory manipulation
- sequentialthinking: Structured problem-solving through sequential thoughts
- task_done: Signal task completion after verification

Guidelines:
1. Always reason before making decisions - use sequentialthinking for complex problems
2. Use absolute paths for file operations
3. Verify work thoroughly before calling task_done
4. Handle errors gracefully and provide clear feedback
5. Break down complex tasks into manageable steps"""

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("placeholder", "{messages}")]
    )

    # Bind tools to LLM
    assistant_runnable = prompt | llm.bind_tools(all_tools)

    # Define the function that will be called to run the assistant
    def assistant_node(state: CopilotKitState):
        result = assistant_runnable.invoke(state)
        return {"messages": state["messages"] + [result]}

    # Create graph
    builder = StateGraph(CopilotKitState)

    # Add nodes
    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", ToolNode(all_tools))

    # Define edges
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")

    # Compile with memory
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


# Create default agent instance
ide_agent = create_ide_agent()
