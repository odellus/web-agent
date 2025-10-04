# copilotkit-work/trae-web/agent-py/src/tools/__init__.py
"""Tools module for trae-web IDE agent."""

from .bash_tool import bash_tool
from .edit_tool import edit_tool
from .sequential_thinking_tool import sequential_thinking_tool
from .task_done_tool import task_done

__all__ = [
    "bash_tool",
    "edit_tool",
    "sequential_thinking_tool",
    "task_done",
]

# List of all tools for easy binding
all_tools = [
    bash_tool,
    edit_tool,
    sequential_thinking_tool,
    task_done,
]

# Tool registry mapping for easy access
tools_registry = {
    "bash": bash_tool,
    "str_replace_based_edit_tool": edit_tool,
    "sequentialthinking": sequential_thinking_tool,
    "task_done": task_done,
}
