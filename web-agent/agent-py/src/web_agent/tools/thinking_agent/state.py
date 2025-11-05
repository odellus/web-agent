from pydantic import BaseModel, DirectoryPath
from langgraph.graph import MessagesState
from typing import Optional, List


class ThinkingAgentState(MessagesState):
    """State for thinking subagent."""

    # Current thinking state
    current_thought_number: int = 1
    total_thoughts: int = 5
    thoughts_completed: bool = False

    # Thought revision and branching
    is_revision: Optional[bool] = False
    revises_thought: Optional[int] = None
    branch_from_thought: Optional[int] = None
    branch_id: Optional[str] = None

    # Planning and context
    problem_context: Optional[str] = None
    solution_hypothesis: Optional[str] = None
    verification_needed: bool = True

    # Tool results cache
    search_results: List[str] = []
    file_contents: List[str] = []

    # Working directory for context
    working_directory: Optional[DirectoryPath] = None

    # Control flow
    next_thought_needed: bool = True
    max_thoughts: int = 25
