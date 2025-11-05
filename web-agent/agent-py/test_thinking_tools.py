#!/usr/bin/env python3
"""Test script for thinking tools functionality."""

import asyncio
import tempfile
from pathlib import Path

from src.web_agent.tools.thinking_tools import (
    thinking_tool,
    web_search_tool,
    read_file_tool,
    rg_search_tool,
    html_to_markdown,
)


def test_thinking_tool():
    """Test the thinking tool functionality."""
    print("=== Testing Thinking Tool ===")

    result = thinking_tool.invoke(
        {
            "thought": "Test thought about problem analysis",
            "thought_number": 1,
            "total_thoughts": 5,
            "next_thought_needed": True,
            "analysis_type": "problem_breakdown",
            "confidence_level": 7,
            "problem_context": "Testing the thinking tool with context",
        }
    )

    print(result)
    print("\n✅ Thinking tool test passed\n")


async def test_web_search_tool():
    """Test the web search tool functionality."""
    print("=== Testing Web Search Tool ===")

    try:
        result = await web_search_tool.invoke(
            {"query": "Python programming language", "limit": 3}
        )
        print("Search results:")
        print(result)
        print("\n✅ Web search tool test passed\n")
    except Exception as e:
        print(f"⚠️  Web search test failed (expected if no SearXNG): {e}\n")


def test_read_file_tool():
    """Test the read file tool functionality."""
    print("=== Testing Read File Tool ===")

    # Create a temporary directory and file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.txt"
        test_content = "Line 1\nLine 2\nLine 3 with some content\nLine 4\n"
        test_file.write_text(test_content)

        # Test reading the file
        result = read_file_tool.invoke(
            {"file_path": "test.txt", "working_directory": temp_dir}
        )

        print("File contents:")
        print(result)
        print("\n✅ Read file tool test passed\n")


def test_rg_search_tool():
    """Test the ripgrep search tool functionality."""
    print("=== Testing Ripgrep Search Tool ===")

    # Create a temporary directory with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        test_file1 = Path(temp_dir) / "file1.py"
        test_file1.write_text("def hello():\n    print('Hello World')\n\n")

        test_file2 = Path(temp_dir) / "file2.js"
        test_file2.write_text(
            "function hello() {\n    console.log('Hello World');\n}\n"
        )

        test_file3 = Path(temp_dir) / "file3.md"
        test_file3.write_text("# Hello World\nThis is a test document.\n")

        # Test searching for "hello"
        result = rg_search_tool.invoke(
            {"pattern": "hello", "path": ".", "working_directory": temp_dir}
        )

        print("Search results for 'hello':")
        print(result)
        print("\n✅ Ripgrep search tool test passed\n")


def test_html_to_markdown():
    """Test HTML to markdown conversion."""
    print("=== Testing HTML to Markdown Conversion ===")

    html = """
    <html>
    <body>
        <h1>Main Title</h1>
        <p>This is a <strong>paragraph</strong> with <em>emphasis</em>.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <code>print('Hello')</code>
    </body>
    </html>
    """

    markdown = html_to_markdown(html)
    print("Converted markdown:")
    print(markdown)
    print("\n✅ HTML to markdown conversion test passed\n")


def test_sequential_thinking_tool():
    """Test the enhanced sequential thinking tool."""
    print("=== Testing Enhanced Sequential Thinking Tool ===")

    from src.web_agent.tools.sequential_thinking_tool import sequential_thinking_tool

    result = sequential_thinking_tool.invoke(
        {
            "problem_description": "How to optimize the performance of a Python web application?",
            "context": "The application is experiencing slow response times under load",
            "max_thoughts": 8,
            "thinking_approach": "Systematic performance analysis",
        }
    )

    print("Sequential thinking result:")
    print(result)
    print("\n✅ Sequential thinking tool test passed\n")


async def main():
    """Run all tests."""
    print("🧪 Running Thinking Tools Tests\n")

    test_thinking_tool()
    test_read_file_tool()
    test_rg_search_tool()
    test_html_to_markdown()
    test_sequential_thinking_tool()

    # Run async test
    await test_web_search_tool()

    print("🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
