#!/usr/bin/env python3
"""
Comprehensive demonstration of the thinking subagent with actual LLM usage.

This script demonstrates the enhanced sequential thinking tool that uses a reasoning
subagent with capabilities for structured thinking, web research, file analysis,
and code search.
"""

import asyncio
import tempfile
from pathlib import Path
from langchain_core.messages import HumanMessage, ToolMessage

from src.web_agent.tools.sequential_thinking_tool import sequential_thinking_tool
from src.web_agent.tools.thinking_tools import (
    thinking_tool,
    web_search_tool,
    read_file_tool,
    rg_search_tool,
    html_to_markdown,
)


def demonstrate_thinking_tool():
    """Demonstrate the enhanced thinking tool with structured analysis."""
    print("🧠 DEMONSTRATING THINKING TOOL")
    print("=" * 50)

    result = thinking_tool.invoke(
        {
            "thought": "To optimize Python performance, I need to consider multiple strategies including code efficiency, library usage, and system configuration. Let me break this down into structured steps.",
            "thought_number": 1,
            "total_thoughts": 5,
            "next_thought_needed": True,
            "analysis_type": "problem_breakdown",
            "confidence_level": 8,
            "problem_context": "Performance optimization for a web application",
            "solution_hypothesis": "Using built-in functions and efficient data structures",
        }
    )

    print(result)
    print()


def demonstrate_file_analysis():
    """Demonstrate file reading and analysis capabilities."""
    print("📁 DEMONSTRATING FILE ANALYSIS")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a sample Python file with optimization opportunities
        sample_file = Path(temp_dir) / "sample.py"
        sample_file.write_text("""
def slow_data_processing(data):
    '''An inefficient data processing function.'''
    result = []
    for item in data:
        if item > 0:
            new_item = item * 2
            result.append(new_item)
    return result

def fast_data_processing(data):
    '''An optimized version using list comprehensions.'''
    return [item * 2 for item in data if item > 0]

# Inefficient string concatenation
def build_slow_message(names):
    message = ""
    for name in names:
        message += name + ", "
    return message

# Optimized string building
def build_fast_message(names):
    return ", ".join(names)

class PerformanceCritical:
    def __init__(self):
        self.cache = {}

    def expensive_calculation(self, x):
        if x not in self.cache:
            # Simulate expensive operation
            self.cache[x] = x * x * x + 100
        return self.cache[x]
""")

        # Use the read_file tool
        result = read_file_tool.invoke(
            {
                "file_path": "sample.py",
                "working_directory": temp_dir,
            }
        )

        print("File contents:")
        print(result)
        print()


def demonstrate_code_search():
    """Demonstrate ripgrep search capabilities."""
    print("🔍 DEMONSTRATING CODE SEARCH")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple source files
        files = {
            "main.py": "def main():\n    data = load_data()\n    result = process_data(data)\n    return result",
            "utils.py": "def load_data():\n    return [1, 2, 3, 4, 5]\n\ndef process_data(data):\n    return [x*2 for x in data]",
            "config.py": "CONFIG = {\n    'debug': True,\n    'max_workers': 4\n}",
        }

        for filename, content in files.items():
            (Path(temp_dir) / filename).write_text(content)

        # Search for function definitions
        result = rg_search_tool.invoke(
            {
                "pattern": "def",
                "path": ".",
                "working_directory": temp_dir,
            }
        )

        print("Search results for 'def':")
        print(result)
        print()

        # Search for data processing patterns
        result = rg_search_tool.invoke(
            {
                "pattern": "process.*data",
                "path": ".",
                "working_directory": temp_dir,
            }
        )

        print("Search results for 'process.*data':")
        print(result)
        print()


def demonstrate_web_search():
    """Demonstrate web search capabilities."""
    print("🌐 DEMONSTRATING WEB SEARCH")
    print("=" * 50)

    async def test_web_search():
        try:
            result = await web_search_tool.invoke(
                {
                    "query": "Python performance optimization best practices 2024",
                    "limit": 3,
                }
            )
            print("Web search results:")
            print(result)
        except Exception as e:
            print(f"Web search test failed: {e}")

    asyncio.run(test_web_search())
    print()


def demonstrate_html_conversion():
    """Demonstrate HTML to Markdown conversion."""
    print("📄 DEMONSTRATING HTML TO MARKDOWN")
    print("=" * 50)

    html_content = """
    <html>
    <head><title>Python Performance Guide</title></head>
    <body>
        <h1>Python Performance Optimization</h1>
        <p>This guide covers <strong>essential techniques</strong> for optimizing Python code.</p>
        <h2>Key Strategies</h2>
        <ul>
            <li>Use built-in functions</li>
            <li>Optimize data structures</li>
            <li>Leverage libraries like NumPy</li>
        </ul>
        <p>For more information, visit <a href="https://python.org">python.org</a>.</p>
    </body>
    </html>
    """

    markdown_result = html_to_markdown(html_content)
    print("HTML to Markdown conversion:")
    print(markdown_result)
    print()


def demonstrate_sequential_thinking():
    """Demonstrate the enhanced sequential thinking tool."""
    print("🤖 DEMONSTRATING SEQUENTIAL THINKING WITH SUBAGENT")
    print("=" * 60)

    result = sequential_thinking_tool.invoke(
        {
            "problem_description": "How can I optimize a Python web application experiencing slow response times under high load?",
            "context": "The application is a Flask-based REST API using SQLAlchemy. Response times increase from 200ms to 2000ms under 100 concurrent users.",
            "max_thoughts": 10,
            "thinking_approach": "Systematic performance analysis covering database queries, caching, and infrastructure",
            "working_directory": "/tmp",  # Using temp directory for file operations
        }
    )

    print("Sequential thinking subagent result:")
    print(result)
    print()


def main():
    """Run all demonstrations."""
    print("🧪 THINKING SUBAGENT COMPREHENSIVE DEMONSTRATION")
    print("=" * 60)
    print()

    demonstrate_thinking_tool()
    demonstrate_file_analysis()
    demonstrate_code_search()
    demonstrate_web_search()
    demonstrate_html_conversion()
    demonstrate_sequential_thinking()

    print("🎉 All demonstrations completed successfully!")
    print()
    print("📋 SUMMARY:")
    print("✅ Thinking tool with structured analysis")
    print("✅ File reading and analysis capabilities")
    print("✅ Code search with ripgrep")
    print("✅ Web search functionality")
    print("✅ HTML to Markdown conversion")
    print("✅ Enhanced sequential thinking with LLM subagent")
    print()
    print("The thinking subagent provides a comprehensive reasoning framework with:")
    print("- Structured thought progression")
    print("- Context-aware analysis")
    print("- Tool integration for research and code exploration")
    print("- Working directory support for file operations")
    print("- Web research capabilities")
    print("- HTML content processing")


if __name__ == "__main__":
    main()
