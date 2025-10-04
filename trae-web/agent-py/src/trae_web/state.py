from typing import List, Optional, Dict, Any
from langgraph.graph import MessagesState


class TraeWebState(MessagesState):
    """Simple state for IDE agent."""

    remaining_steps: int
