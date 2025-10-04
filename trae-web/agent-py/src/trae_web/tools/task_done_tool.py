# copilotkit-work/trae-web/agent-py/src/tools/task_done_tool.py
from langchain_core.tools import tool


@tool
def task_done() -> str:
    """Signal task completion with verification requirement.

    Purpose:
    - Mark tasks as successfully completed
    - Must be called only after proper verification
    - Encourages writing test/reproduction scripts

    Important: Only call this tool after you have verified that the task is
    actually completed successfully. This should be the final step after
    all work and verification is done.
    """
    return "Task done."
