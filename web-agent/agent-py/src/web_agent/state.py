from pydantic import DirectoryPath, BaseModel
from langgraph.graph import MessagesState
from copilotkit import CopilotKitState
import os


class WebAgentState(CopilotKitState):
    """State for IDE agent with working directory support."""

    working_directory: DirectoryPath
    remaining_steps: int
