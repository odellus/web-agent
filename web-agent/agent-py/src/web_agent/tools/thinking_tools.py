from typing import Optional, List
from langchain_core.tools import tool
from pydantic import DirectoryPath
from pathlib import Path
import subprocess
import re
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
import markdownify


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
) -> str:
    """Enhanced thinking tool for structured problem analysis and planning.

    This tool provides structured reasoning capabilities with context tracking,
    confidence scoring, and analysis categorization.

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
    """
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

    return "\n".join(output_parts)


@tool
async def web_search_tool(query: str, limit: int = 5) -> str:
    """Search the internet for information.

    Args:
        query: Search query for finding information
        limit: Maximum number of results to return (default: 5)

    Returns:
        Search results with titles, URLs, and content snippets
    """
    try:
        # Use SearXNG if available, otherwise fall back to web search
        searxng_url = "http://localhost:8082"

        async with aiohttp.ClientSession() as session:
            params = {"q": query, "format": "json"}
            async with session.get(f"{searxng_url}/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    results = []
                    for i, result in enumerate(data.get("results", [])[:limit]):
                        results.append(
                            f"Result {i + 1}:\n"
                            f"Title: {result.get('title', 'No title')}\n"
                            f"URL: {result.get('url', 'No URL')}\n"
                            f"Content: {result.get('content', 'No content')[:500]}...\n"
                        )

                    if not results:
                        return "No search results found"

                    return "\n".join(results)
                else:
                    return f"Search failed with status: {response.status}"

    except Exception as e:
        return f"Search error: {str(e)}"


@tool
async def fetch_tool(url: str) -> str:
    """Fetch content from a URL and convert to markdown.

    Args:
        url: URL to fetch content from

    Returns:
        Markdown content from the webpage
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()

                    # Simple HTML to Markdown conversion
                    markdown_content = html_to_markdown(html_content)
                    return markdown_content
                else:
                    return f"Failed to fetch URL: {response.status}"

    except Exception as e:
        return f"Fetch error: {str(e)}"


def html_to_markdown(html: str) -> str:
    """Simple HTML to Markdown converter."""
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

    return html


@tool
def read_file_tool(
    file_path: str, working_directory: Optional[DirectoryPath] = None
) -> str:
    """Read file contents with working directory support.

    Args:
        file_path: Path to the file to read (relative to working directory)
        working_directory: Base directory for resolving relative paths

    Returns:
        File contents with line numbers
    """
    try:
        # Resolve path relative to working directory
        if working_directory:
            path_obj = Path(working_directory) / file_path
        else:
            path_obj = Path(file_path)

        if not path_obj.exists():
            return f"File not found: {path_obj}"

        if not path_obj.is_file():
            return f"Path is not a file: {path_obj}"

        content = path_obj.read_text()
        lines = content.split("\n")

        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            numbered_lines.append(f"{i:4d} | {line}")

        return "\n".join(numbered_lines)

    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def rg_search_tool(
    pattern: str, path: str = ".", working_directory: Optional[DirectoryPath] = None
) -> str:
    """Search code using ripgrep (rg) for fast pattern matching.

    Args:
        pattern: Pattern to search for (regex supported)
        path: Directory to search in (default: current directory)
        working_directory: Base directory for resolving relative paths

    Returns:
        Search results with file paths and matching lines
    """
    try:
        # Resolve path relative to working directory
        if working_directory:
            search_path = Path(working_directory) / path
        else:
            search_path = Path(path)

        if not search_path.exists():
            return f"Search path not found: {search_path}"

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
                return f"Search results:\n\n{result.stdout}"
            else:
                return "No matches found"
        else:
            return f"Search failed: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Search timed out (pattern may be too broad or complex)"
    except FileNotFoundError:
        return "ripgrep (rg) not found - please install it"
    except Exception as e:
        return f"Search error: {str(e)}"


# List of all thinking tools
all_tools = [
    thinking_tool,
    web_search_tool,
    fetch_tool,
    read_file_tool,
    rg_search_tool,
]
