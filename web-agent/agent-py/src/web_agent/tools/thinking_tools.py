from typing import Optional, List
import logging
from datetime import datetime
from pathlib import Path
import subprocess
import re
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
import markdownify
from langchain_core.tools import tool
from pydantic import DirectoryPath
from langgraph.prebuilt import InjectedState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("thinking_tools.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@tool
def thinking_tool(
    thought: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool,
    problem_context: Optional[str] = None,
    solution_hypothesis: Optional[str] = None,
    is_revision: Optional[bool] = False,
    revises_thought: Optional[int] = None,
    branch_from_thought: Optional[int] = None,
    branch_id: Optional[str] = None,
    analysis_type: Optional[str] = None,
    confidence_level: Optional[int] = None,
    # Injected state from agent
    messages: Optional[List] = None,
    working_directory: Optional[DirectoryPath] = InjectedState("working_directory"),
) -> str:
    """Enhanced thinking tool for structured problem analysis and planning with LLM integration.

    This tool provides structured reasoning capabilities with context tracking,
    confidence scoring, and analysis categorization. Uses LLM when appropriate.

    Args:
        thought: Current thinking step or insight
        thought_number: Current position in thinking sequence
        total_thoughts: Estimated total thoughts needed
        next_thought_needed: Whether additional thoughts are required
        problem_context: Background information about the problem
        solution_hypothesis: Current proposed solution or approach
        is_revision: Whether this thought revises a previous insight
        revises_thought: Number of thought being revised
        branch_from_thought: Thought number this branches from
        branch_id: Unique identifier for thinking branches
        analysis_type: Category of analysis (problem_breakdown, solution_planning, verification)
        confidence_level: Confidence in current thought (1-10 scale)
        messages: Conversation history for context (injected)
        working_directory: Base directory for file operations (injected)
    """
    logger.info(f"Thinking tool called - Thought {thought_number}/{total_thoughts}")

    # Log context if available
    if messages:
        logger.info(f"Message history available: {len(messages)} messages")

    if working_directory:
        logger.info(f"Working directory: {working_directory}")

    # Use LLM for complex thinking scenarios
    if (
        analysis_type in ["complex_analysis", "strategic_planning"]
        or confidence_level is None
    ):
        return _llm_thinking_analysis(
            thought=thought,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            problem_context=problem_context,
            solution_hypothesis=solution_hypothesis,
            analysis_type=analysis_type,
            messages=messages,
            working_directory=working_directory,
        )

    # Standard structured thinking
    output_parts = [
        f"THOUGHT [{thought_number}/{total_thoughts}]:",
        f"{thought}",
        f"Next thought needed: {next_thought_needed}",
    ]

    if problem_context:
        output_parts.append(f"Context: {problem_context}")
    if solution_hypothesis:
        output_parts.append(f"Solution hypothesis: {solution_hypothesis}")
    if is_revision:
        output_parts.append(f"Revision of thought #{revises_thought}")
    if branch_from_thought:
        output_parts.append(f"Branching from thought #{branch_from_thought}")
    if branch_id:
        output_parts.append(f"Branch ID: {branch_id}")
    if analysis_type:
        output_parts.append(f"Analysis type: {analysis_type}")
    if confidence_level:
        output_parts.append(f"Confidence: {confidence_level}/10")

    result = "\n".join(output_parts)
    logger.info(f"Thinking tool generated {len(result)} characters")
    return result


def _llm_thinking_analysis(
    thought: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool,
    problem_context: Optional[str],
    solution_hypothesis: Optional[str],
    analysis_type: Optional[str],
    messages: Optional[List],
    working_directory: Optional[DirectoryPath],
) -> str:
    """Use LLM for complex thinking analysis."""

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="qwen3:latest",
        temperature=0.1,
    )

    # Build thinking prompt
    prompt_parts = [
        f"Thought {thought_number} of {total_thoughts}: {thought}",
        f"Next thought needed: {next_thought_needed}",
    ]

    if problem_context:
        prompt_parts.append(f"Context: {problem_context}")
    if solution_hypothesis:
        prompt_parts.append(f"Solution hypothesis: {solution_hypothesis}")
    if analysis_type:
        prompt_parts.append(f"Analysis type: {analysis_type}")

    if messages:
        # Add recent conversation context
        recent_messages = messages[-3:]  # Last 3 messages
        prompt_parts.append("Recent conversation context:")
        for msg in recent_messages:
            if hasattr(msg, "content"):
                prompt_parts.append(f"  - {msg.content[:100]}...")

    thinking_prompt = "\n".join(prompt_parts)

    logger.info("Using LLM for complex thinking analysis")

    try:
        response = llm.invoke(
            [
                SystemMessage(
                    content="You are an expert reasoning AI. Provide insightful analysis and improvements to the thinking process."
                ),
                HumanMessage(
                    content=f"""Enhance this thinking step with deeper analysis:

{thinking_prompt}

Please:
1. Provide additional insights and perspectives
2. Suggest next steps or alternative approaches
3. Identify potential issues or blind spots
4. Maintain the structured thinking format
"""
                ),
            ]
        )

        result = f"""LLM-ENHANCED THINKING [{thought_number}/{total_thoughts}]:
{response.content}

---
Original thought: {thought}
"""

        logger.info(f"LLM thinking analysis completed: {len(result)} characters")
        return result

    except Exception as e:
        logger.error(f"LLM thinking analysis failed: {e}")
        # Fallback to standard thinking
        return thinking_tool(
            thought=thought,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            problem_context=problem_context,
            solution_hypothesis=solution_hypothesis,
            analysis_type=analysis_type,
            confidence_level=5,  # Default confidence
            messages=messages,
            working_directory=working_directory,
        )


@tool
async def web_search_tool(
    query: str,
    limit: int = 5,
    working_directory: Optional[DirectoryPath] = InjectedState("working_directory"),
) -> str:
    """Search the internet for information with logging.

    Args:
        query: Search query for finding information
        limit: Maximum number of results to return (default: 5)
        working_directory: Working directory for context (injected)

    Returns:
        Search results with titles, URLs, and content snippets
    """
    logger.info(f"Web search: '{query[:50]}...' (limit: {limit})")

    try:
        # Use SearXNG if available, otherwise fall back to web search
        searxng_url = "http://localhost:8082"

        async with aiohttp.ClientSession() as session:
            params = {"q": query, "format": "json"}
            async with session.get(f"{searxng_url}/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(
                        f"Search returned {len(data.get('results', []))} results"
                    )

                    results = []
                    for i, result in enumerate(data.get("results", [])[:limit]):
                        results.append(
                            f"Result {i + 1}:\n"
                            f"Title: {result.get('title', 'No title')}\n"
                            f"URL: {result.get('url', 'No URL')}\n"
                            f"Content: {result.get('content', 'No content')[:500]}...\n"
                        )

                    if not results:
                        logger.info("No search results found")
                        return "No search results found"

                    final_result = "\n".join(results)
                    logger.info(f"Web search completed: {len(final_result)} characters")
                    return final_result
                else:
                    error_msg = f"Search failed with status: {response.status}"
                    logger.error(error_msg)
                    return error_msg

    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
async def fetch_tool(
    url: str,
    working_directory: Optional[DirectoryPath] = InjectedState("working_directory"),
) -> str:
    """Fetch content from a URL and convert to markdown with logging.

    Args:
        url: URL to fetch content from
        working_directory: Working directory for context (injected)

    Returns:
        Markdown content from the webpage
    """
    logger.info(f"Fetching URL: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    logger.info(f"Fetched {len(html_content)} characters of HTML")

                    # Simple HTML to Markdown conversion
                    markdown_content = html_to_markdown(html_content)
                    logger.info(
                        f"Converted to markdown: {len(markdown_content)} characters"
                    )
                    return markdown_content
                else:
                    error_msg = f"Failed to fetch URL: {response.status}"
                    logger.error(error_msg)
                    return error_msg

    except Exception as e:
        error_msg = f"Fetch error: {str(e)}"
        logger.error(error_msg)
        return error_msg


def html_to_markdown(html: str) -> str:
    """Simple HTML to Markdown converter with logging."""
    logger.info("Converting HTML to Markdown")

    # Remove script and style tags
    html = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?>.*?</style>", "", html, flags=re.DOTALL)

    # Basic HTML to Markdown conversion
    html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1", html, flags=re.DOTALL)
    html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1", html, flags=re.DOTALL)
    html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1", html, flags=re.DOTALL)
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", html, flags=re.DOTALL)
    html = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", html, flags=re.DOTALL)
    html = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", html, flags=re.DOTALL)
    html = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", html, flags=re.DOTALL)
    html = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", html, flags=re.DOTALL)
    html = re.sub(
        r'<a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL)
    html = re.sub(r"<pre[^>]*>(.*?)</pre>", r"```\1```", html, flags=re.DOTALL)
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", "", html)  # Remove remaining HTML tags

    # Clean up whitespace
    html = re.sub(r"\n\s*\n\s*\n", "\n\n", html)
    html = re.sub(r"^\s+|\s+$", "", html, flags=re.MULTILINE)
    html = html.strip()

    logger.info("HTML to Markdown conversion completed")
    return html


@tool
def read_file_tool(
    file_path: str,
    working_directory: Optional[DirectoryPath] = InjectedState("working_directory"),
) -> str:
    """Read file contents with working directory support and logging.

    Args:
        file_path: Path to the file to read (relative to working directory)
        working_directory: Base directory for resolving relative paths (injected)

    Returns:
        File contents with line numbers
    """
    logger.info(f"Reading file: {file_path}")

    try:
        # Resolve path relative to working directory
        if working_directory:
            path_obj = Path(working_directory) / file_path
        else:
            path_obj = Path(file_path)

        if not path_obj.exists():
            error_msg = f"File not found: {path_obj}"
            logger.error(error_msg)
            return error_msg

        if not path_obj.is_file():
            error_msg = f"Path is not a file: {path_obj}"
            logger.error(error_msg)
            return error_msg

        content = path_obj.read_text()
        lines = content.split("\n")

        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            numbered_lines.append(f"{i:4d} | {line}")

        result = "\n".join(numbered_lines)
        logger.info(
            f"File read successfully: {len(content)} characters, {len(lines)} lines"
        )
        return result

    except Exception as e:
        error_msg = f"Error reading file: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def rg_search_tool(
    pattern: str,
    path: str = ".",
    working_directory: Optional[DirectoryPath] = InjectedState("working_directory"),
) -> str:
    """Search code using ripgrep (rg) for fast pattern matching with logging.

    Args:
        pattern: Pattern to search for (regex supported)
        path: Directory to search in (default: current directory)
        working_directory: Base directory for resolving relative paths (injected)

    Returns:
        Search results with file paths and matching lines
    """
    logger.info(f"Ripgrep search: pattern='{pattern}', path='{path}'")

    try:
        # Resolve path relative to working directory
        if working_directory:
            search_path = Path(working_directory) / path
        else:
            search_path = Path(path)

        if not search_path.exists():
            error_msg = f"Search path not found: {search_path}"
            logger.error(error_msg)
            return error_msg

        # Build rg command
        cmd = [
            "rg",
            "--line-number",
            "--column",
            "--context",
            "2",
            pattern,
            str(search_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            if result.stdout:
                final_result = f"Search results:\n\n{result.stdout}"
                logger.info(
                    f"Search successful: found {result.stdout.count(chr(10))} lines"
                )
                return final_result
            else:
                logger.info("Search completed: no matches found")
                return "No matches found"
        else:
            error_msg = f"Search failed: {result.stderr}"
            logger.error(error_msg)
            return error_msg

    except subprocess.TimeoutExpired:
        error_msg = "Search timed out (pattern may be too broad or complex)"
        logger.error(error_msg)
        return error_msg
    except FileNotFoundError:
        error_msg = "ripgrep (rg) not found - please install it"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        logger.error(error_msg)
        return error_msg


# List of all thinking tools
all_tools = [
    thinking_tool,
    web_search_tool,
    fetch_tool,
    read_file_tool,
    rg_search_tool,
]
