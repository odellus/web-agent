from pydantic import DirectoryPath, BaseModel
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from copilotkit import CopilotKitState
from pathlib import Path
import matplotlib.pyplot as plt
from web_agent.agent import TRAE_AGENT_SYSTEM_PROMPT, llm
from web_agent.state import WebAgentState
from web_agent.tools import all_tools
from web_agent.config import settings
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

langfuse = Langfuse(
    public_key=settings.langfuse_public_key.get_secret_value(),
    secret_key=settings.langfuse_secret_key.get_secret_value(),
    host=settings.langfuse_host,
)
langfuse_handler = CallbackHandler()

tools_by_name = {tool.name: tool for tool in all_tools}
llm_with_tools = llm.bind_tools(all_tools)


# Nodes
def llm_call(state: WebAgentState):
    """LLM decides whether to call a tool or not"""
    remaining_steps = state["remaining_steps"] - 1
    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    SystemMessage(
                        content=TRAE_AGENT_SYSTEM_PROMPT,
                    )
                ]
                + state["messages"]
            )
        ],
        "remaining_steps": remaining_steps,
    }


# def tool_node(state: WebAgentState):
#     """Performs the tool call"""

#     result = []
#     for tool_call in state["messages"][-1].tool_calls:
#         tool = tools_by_name[tool_call["name"]]
#         observation = tool.invoke(tool_call["args"])
#         result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
#     return {"messages": result}


# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: WebAgentState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    task_done_messages = [
        msg
        for msg in messages
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "task_done"
    ]
    if task_done_messages:
        return END

    if state["remaining_steps"] <= 0:
        return END

    last_message = messages[-1]
    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"
    # Otherwise, we stop (reply to the user)
    return END


# Build workflow
agent_builder = StateGraph(WebAgentState)

# Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", ToolNode(tools=all_tools))

# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
agent_builder.add_edge("tool_node", "llm_call")

# Compile the agent
agent = agent_builder.compile()

# Show the agent
# from IPython.display import Image, display

# plt.imshow(agent.get_graph(xray=True).draw_mermaid_png())

# Invoke
#
config = {
    "configurable": {"thread_id": "custom-test-124"},
    "recursion_limit": 50,
    "callbacks": [langfuse_handler],
}
initial_state = {
    "messages": [
        HumanMessage(
            # content="Create a file called test.txt with 'hello world'. Then rename it. Then edit it to say goodbye world."
            content="Use sequential thinking tool extensively and bash to review current working directory and create an TODO.md that describes the overall structure of the project and its purpose and what should be done next. Think carefully.."
        )
    ],
    "remaining_steps": 50,
    "working_directory": Path(
        "/home/thomas/src/projects/copilotkit-work/test_workingdir"
    ),
}
messages = agent.invoke(initial_state, config=config)
for m in messages["messages"]:
    m.pretty_print()
