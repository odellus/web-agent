#!/usr/bin/env python3
"""
Enhanced sequential thinking tool that uses a reasoning subagent with actual LLM capabilities.

This tool provides sophisticated problem analysis through a dedicated thinking subagent
with capabilities for structured reasoning, web research, file analysis, and code search.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field, DirectoryPath
from pathlib import Path

from .thinking_agent import run_thinking_agent, ThinkingAgentState
from .thinking_tools import all_tools as thinking_agent_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("sequential_thinking.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ThinkingInput(BaseModel):
    """Input model for the enhanced sequential thinking tool."""

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
        None,
        description="Specific approach for thinking (problem_breakdown, solution_planning, research_analysis)",
    )
    working_directory: Optional[str] = Field(
        None, description="Working directory for file operations"
    )
    use_llm_analysis: bool = Field(
        True, description="Whether to use LLM for enhanced analysis"
    )


@tool
def sequential_thinking_tool(
    problem_description: str,
    context: Optional[str] = None,
    max_thoughts: int = 15,
    thinking_approach: Optional[str] = None,
    working_directory: Optional[str] = None,
    use_llm_analysis: bool = True,
) -> str:
    """Enhanced sequential thinking tool that uses a reasoning subagent with LLM capabilities.

    This tool provides sophisticated problem analysis through a dedicated thinking subagent
    with capabilities for structured reasoning, web research, file analysis, and code search.

    When to use this tool:
    - Breaking down complex problems into manageable components
    - Planning multi-step solutions and approaches
    - Analyzing code and understanding system architecture
    - Researching solutions for technical challenges
    - Creating comprehensive analysis of issues
    - Planning debugging strategies and fixes

    Key improvements over basic sequential thinking:
    - Actual LLM integration for reasoning and analysis
    - Web research capabilities for external information
    - File analysis and code search tools
    - Working directory support for file operations
    - Structured thought tracking and analysis
    - Comprehensive logging for debugging and review

    Args:
        problem_description: Detailed description of the problem or task to analyze
        context: Additional context about the problem, project, or environment
        max_thoughts: Maximum number of thinking steps to take (default: 15)
        thinking_approach: Specific approach for thinking (optional)
        working_directory: Base directory for file operations (optional)
        use_llm_analysis: Whether to use LLM for enhanced analysis (default: True)
    """
    logger.info(
        f"Sequential thinking tool called - Problem: {problem_description[:50]}..."
    )
    logger.info(f"Max thoughts: {max_thoughts}, Approach: {thinking_approach}")

    try:
        # Convert working directory string to Path if provided
        working_path = None
        if working_directory:
            working_path = Path(working_directory)
            logger.info(f"Working directory: {working_path}")

        # Add thinking approach to context if provided
        full_context = context or ""
        if thinking_approach:
            if full_context:
                full_context += f"\n\nThinking approach: {thinking_approach}"
            else:
                full_context = f"Thinking approach: {thinking_approach}"
            logger.info(f"Thinking approach: {thinking_approach}")

        # Prepare initial message for the thinking agent
        initial_message = problem_description
        if full_context:
            initial_message = f"{problem_description}\n\nContext:\n{full_context}"

        logger.info("Starting thinking agent session")

        # Run the thinking agent using asyncio.run() - this will create a new event loop
        # since we're called from a sync context (LangChain tool)
        thinking_result = asyncio.run(
            run_thinking_agent(
                initial_message=initial_message,
                problem_context=full_context,
                max_thoughts=max_thoughts,
                working_directory=working_path,
            )
        )

        logger.info(
            f"Thinking agent session completed - Result length: {len(thinking_result)}"
        )

        return thinking_result

    except Exception as e:
        logger.error(f"Error in thinking subagent: {str(e)}")
        return f"Error in thinking subagent: {str(e)}"


@tool
def quick_analysis_tool(
    problem: str,
    max_thoughts: int = 8,
    use_web_search: bool = False,
    working_directory: Optional[str] = None,
) -> str:
    """Quick analysis tool for simpler problems or time-sensitive tasks.

    This tool provides rapid analysis using the thinking subagent with optimized settings.

    Args:
        problem: Brief description of the problem to analyze
        max_thoughts: Maximum number of thinking steps (default: 8 for quick analysis)
        use_web_search: Whether to enable web search for external information
        working_directory: Base directory for file operations (optional)
    """
    logger.info(f"Quick analysis tool called - Problem: {problem[:50]}...")

    # Set up quick analysis context
    context = "Quick analysis mode - focus on concise, actionable insights."

    try:
        # Convert working directory string to Path if provided
        working_path = None
        if working_directory:
            working_path = Path(working_directory)

        logger.info("Starting quick analysis session")

        # Run the thinking agent using asyncio.run() - this will create a new event loop
        # since we're called from a sync context (LangChain tool)
        thinking_result = asyncio.run(
            run_thinking_agent(
                initial_message=f"Quick analysis: {problem}",
                problem_context=context,
                max_thoughts=max_thoughts,
                working_directory=working_path,
            )
        )

        logger.info("Quick analysis session completed")
        return thinking_result
    except Exception as e:
        logger.error(f"Error in quick analysis: {str(e)}")
        return f"Error in quick analysis: {str(e)}"
    except Exception as e:
        logger.error(f"Error in quick analysis: {str(e)}")
        return f"Error in quick analysis: {str(e)}"


@tool
def research_analysis_tool(
    research_question: str,
    search_query: Optional[str] = None,
    max_thoughts: int = 12,
    working_directory: Optional[str] = None,
) -> str:
    """Research-focused analysis tool for external information gathering.

    This tool combines the thinking subagent with web research capabilities to provide
    comprehensive analysis based on external sources.

    Args:
        research_question: The research question to investigate
        search_query: Optional specific search query (if None, uses research_question)
        max_thoughts: Maximum number of thinking steps (default: 12 for research)
        working_directory: Base directory for file operations (optional)
    """
    logger.info(
        f"Research analysis tool called - Question: {research_question[:50]}..."
    )

    # Prepare research context
    search_term = search_query or research_question
    context = f"Research analysis mode - Investigating: {search_term}. Use web search to gather external information."

    try:
        # Convert working directory string to Path if provided
        working_path = None
        if working_directory:
            working_path = Path(working_directory)

        logger.info("Starting research analysis session")

        # Run the thinking agent with research settings
        thinking_result = asyncio.run(
            run_thinking_agent(
                initial_message=f"Research analysis: {research_question}\n\nPlease search for information using web_search_tool and provide a comprehensive analysis.",
                problem_context=context,
                max_thoughts=max_thoughts,
                working_directory=working_path,
            )
        )

        logger.info("Research analysis session completed")
        return thinking_result
    except Exception as e:
        logger.error(f"Error in research analysis: {str(e)}")
        return f"Error in research analysis: {str(e)}"


# List of all enhanced thinking tools
all_thinking_tools = [
    sequential_thinking_tool,
    quick_analysis_tool,
    research_analysis_tool,
]
