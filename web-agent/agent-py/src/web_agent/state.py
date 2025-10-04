from typing import List, Optional, Dict, Any
from pydantic import DirectoryPath
from langgraph.graph import MessagesState
import os


class TraeWebState(MessagesState):
    """State for IDE agent with working directory support."""

    working_directory: DirectoryPath
    remaining_steps: int
