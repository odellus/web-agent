# copilotkit-work/trae-web/agent-py/src/tools/sequential_thinking_tool.py
from langchain_core.tools import tool
from typing import Optional


@tool
def sequential_thinking_tool(
    thought: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool,
    is_revision: Optional[bool] = None,
    revises_thought: Optional[int] = None,
    branch_from_thought: Optional[int] = None,
    branch_id: Optional[str] = None,
) -> str:
    """A detailed tool for dynamic and reflective problem-solving through thoughts.

    This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
    Each thought can build on, question, or revise previous insights as understanding deepens.

    When to use this tool:
    - Breaking down complex problems into steps
    - Planning and design with room for revision
    - Analysis that might need course correction
    - Problems where the full scope might not be clear initially
    - Problems that require a multi-step solution
    - Tasks that need to maintain context over multiple steps
    - Situations where irrelevant information needs to be filtered out

    Key features:
    - You can adjust total_thoughts up or down as you progress
    - You can question or revise previous thoughts
    - You can add more thoughts even after reaching what seemed like the end
    - You can express uncertainty and explore alternative approaches
    - Not every thought needs to build linearly - you can branch or backtrack
    - Generates a solution hypothesis
    - Verifies the hypothesis based on the Chain of Thought steps
    - Repeats the process until satisfied
    - Provides a correct answer

    Args:
        thought: Current thinking step
        thought_number: Current number in sequence
        total_thoughts: Current estimate of thoughts needed
        next_thought_needed: True if more thoughts are needed, even if at what seemed like the end
        is_revision: True if this thought revises a previous thought
        revises_thought: Number of the thought being revised (if is_revision is True)
        branch_from_thought: Number of the thought this branches from (for alternative approaches)
        branch_id: Unique identifier for this branch of thinking
    """
    output_parts = [
        f"THOUGHT [{thought_number}/{total_thoughts}]:",
        f"{thought}",
        f"Next thought needed: {next_thought_needed}",
    ]

    if is_revision:
        output_parts.append(f"Revision of thought #{revises_thought}")
    if branch_from_thought:
        output_parts.append(f"Branching from thought #{branch_from_thought}")
    if branch_id:
        output_parts.append(f"Branch ID: {branch_id}")

    return "\n".join(output_parts)
