# copilotkit-work/web-agent/agent-py/src/web_agent/tools/sequential_thinking_tool.py
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pathlib import Path

from .thinking_agent import run_thinking_agent, ThinkingAgentState


class ThinkingInput(BaseModel):
    """Input model for the sequential thinking tool."""

    problem_description: str = Field(
        ..., description="Detailed description of the problem to analyze"
    )
    context: Optional[str] = Field(
        None, description="Additional context for the problem"
    )
    max_thoughts: int = Field(
        15, description="Maximum number of thinking steps to take"
    )
    thinking_approach: Optional[str] = Field(
        None, description="Specific approach for thinking (optional)"
    )
    working_directory: Optional[str] = Field(
        None, description="Working directory for file operations"
    )


@tool
def sequential_thinking_tool(
    problem_description: str,
    context: Optional[str] = None,
    max_thoughts: int = 15,
    thinking_approach: Optional[str] = None,
    working_directory: Optional[str] = None,
) -> str:
    """Enhanced sequential thinking tool that uses a reasoning subagent.

    This tool provides sophisticated problem analysis through a dedicated thinking subagent
    with capabilities for structured reasoning, web research, file analysis, and code search.

    The thinking subagent includes:
    - Structured thinking tool for step-by-step analysis
    - Web search tool for external research and current information
    - File reading tool for examining existing code and documentation
    - Ripgrep tool for searching through code files

    When to use this tool:
    - Breaking down complex problems into manageable components
    - Planning multi-step solutions and approaches
    - Analyzing code and understanding system architecture
    - Researching solutions for technical challenges
    - Creating comprehensive analysis of issues
    - Planning debugging strategies and fixes

    Args:
        problem_description: Detailed description of the problem or task to analyze
        context: Additional context about the problem, project, or environment
        max_thoughts: Maximum number of thinking steps to take (default: 15)
        thinking_approach: Specific approach for thinking (optional)
        working_directory: Base directory for file operations (optional)
    """

    try:
        # Convert working directory string to Path if provided
        working_path = None
        if working_directory:
            working_path = Path(working_directory)

        # Add thinking approach to context if provided
        full_context = context or ""
        if thinking_approach:
            if full_context:
                full_context += f"\n\nThinking approach: {thinking_approach}"
            else:
                full_context = f"Thinking approach: {thinking_approach}"

        # Prepare initial message for the thinking agent
        initial_message = problem_description
        if full_context:
            initial_message = f"{problem_description}\n\nContext:\n{full_context}"

        # Run the thinking agent
        thinking_result = run_thinking_agent(
            initial_message=initial_message,
            problem_context=full_context,
            max_thoughts=max_thoughts,
            working_directory=working_path,
        )

        return thinking_result

    except Exception as e:
        return f"Error in thinking subagent: {str(e)}"


@tool
def quick_analysis_tool(
    problem: str,
    max_thoughts: int = 8,
    use_web_search: bool = False,
    working_directory: Optional[str] = None,
) -> str:
    """Quick analysis tool for simpler problems or time-sensitive tasks.

    Args:
        problem: Brief description of the problem to analyze
        max_thoughts: Maximum number of thinking steps (default: 8 for quick analysis)
        use_web_search: Whether to enable web search for external information
        working_directory: Base directory for file operations (optional)
    """

    # Set up quick analysis context
    context = "Quick analysis mode - focus on concise, actionable insights."

    try:
        # Convert working directory string to Path if provided
        working_path = None
        if working_directory:
            working_path = Path(working_directory)

        # Run the thinking agent with quick analysis settings
        thinking_result = run_thinking_agent(
            initial_message=f"Quick analysis: {problem}",
            problem_context=context,
            max_thoughts=max_thoughts,
            working_directory=working_path,
        )

        return thinking_result

    except Exception as e:
        return f"Error in quick analysis: {str(e)}"
