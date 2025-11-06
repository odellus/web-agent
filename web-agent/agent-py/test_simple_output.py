#!/usr/bin/env python3
"""Simple test that just prints the actual fucking output without any hacks."""

import asyncio
import tempfile
from pathlib import Path

from web_agent.tools.thinking_tools import (
    thinking_tool,
    read_file_tool,
    rg_search_tool,
)


def test_thinking_tool():
    """Test thinking tool and print actual output."""
    print("=== Testing Thinking Tool ===")

    result = thinking_tool.invoke(
        {
            "thought": "Analyze Python performance optimization strategies",
            "thought_number": 1,
            "total_thoughts": 5,
            "next_thought_needed": True,
            "analysis_type": "complex_analysis",
            "confidence_level": None,
            "problem_context": "Python web application performance optimization",
        }
    )

    print("ACTUAL OUTPUT:")
    print(repr(result))
    print("\nFORMATTED OUTPUT:")
    print(result)
    print("\n" + "=" * 50 + "\n")


def test_file_analysis():
    """Test file analysis and print actual output."""
    print("=== Testing File Analysis ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("""
def slow_function():
    result = []
    for i in range(1000):
        result.append(i * 2)
    return result

def fast_function():
    return [i * 2 for i in range(1000)]
""")

        result = read_file_tool.invoke(
            {"file_path": "test.py", "working_directory": temp_dir}
        )

        print("ACTUAL OUTPUT:")
        print(repr(result))
        print("\nFORMATTED OUTPUT:")
        print(result)
        print("\n" + "=" * 50 + "\n")


def test_code_search():
    """Test code search and print actual output."""
    print("=== Testing Code Search ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_files = {
            "file1.py": "def function_one(): return 1\ndef function_two(): return 2",
            "file2.js": "function function_three() { return 3; }",
        }

        for filename, content in test_files.items():
            (Path(temp_dir) / filename).write_text(content)

        result = rg_search_tool.invoke(
            {"pattern": "def", "path": ".", "working_directory": temp_dir}
        )

        print("ACTUAL OUTPUT:")
        print(repr(result))
        print("\nFORMATTED OUTPUT:")
        print(result)
        print("\n" + "=" * 50 + "\n")


def main():
    """Run all tests and print actual outputs."""
    print("STARTING SIMPLE OUTPUT TEST - NO FUCKING HACKS")
    print("=" * 60)

    test_thinking_tool()
    test_file_analysis()
    test_code_search()

    print("TESTS COMPLETE")


if __name__ == "__main__":
    main()
