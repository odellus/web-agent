"""
Test sequential thinking tool output without any hacks
"""

import tempfile
from pathlib import Path

from web_agent.tools.sequential_thinking_tool import sequential_thinking_tool


def test_sequential_thinking():
    """Test sequential thinking tool and print actual output."""
    print("=== Testing Sequential Thinking Tool ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file for the agent to analyze
        test_file = Path(temp_dir) / "performance_test.py"
        test_file.write_text('''
import time

def slow_data_processing(data):
    """Traditional for loop - potentially slower"""
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def fast_data_processing(data):
    """List comprehension - potentially faster"""
    return [item * 2 for item in data if item > 0]

def analyze_performance():
    """Compare performance differences"""
    test_data = list(range(1000))

    # Test slow approach
    start = time.time()
    slow_result = slow_data_processing(test_data)
    slow_time = time.time() - start

    # Test fast approach
    start = time.time()
    fast_result = fast_data_processing(test_data)
    fast_time = time.time() - start

    print(f"Slow approach: {slow_time:.4f}s")
    print(f"Fast approach: {fast_time:.4f}s")
    print(f"Speed improvement: {slow_time/fast_time:.2f}x")

    return slow_result, fast_result
''')

        result = sequential_thinking_tool.invoke(
            {
                "problem_description": "Analyze the Python code performance and optimization opportunities",
                "context": "This code compares list comprehensions vs traditional for loops. Analyze the performance implications and suggest improvements.",
                "max_thoughts": 8,
                "thinking_approach": "Performance analysis and optimization recommendations",
                "working_directory": temp_dir,
                "use_llm_analysis": True,
            }
        )

        print("ACTUAL OUTPUT:")
        print(repr(result))
        print("\nFORMATTED OUTPUT:")
        print(result)
        print("\n" + "=" * 60)


def test_file_analysis():
    """Test file analysis through sequential thinking."""
    print("=== Testing File Analysis ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_code.py"
        test_file.write_text('''
def inefficient_function():
    """Inefficient implementation"""
    result = []
    for i in range(1000):
        if i % 2 == 0:
            result.append(i * 2)
    return result

def efficient_function():
    """Efficient implementation"""
    return [i * 2 for i in range(1000) if i % 2 == 0]
''')

        result = sequential_thinking_tool.invoke(
            {
                "problem_description": "Analyze this Python code for performance bottlenecks and optimizations",
                "context": "Compare the efficiency of the two functions and identify optimization opportunities.",
                "max_thoughts": 6,
                "thinking_approach": "Code performance analysis",
                "working_directory": temp_dir,
                "use_llm_analysis": True,
            }
        )

        print("ACTUAL OUTPUT:")
        print(repr(result))
        print("\nFORMATTED OUTPUT:")
        print(result)


if __name__ == "__main__":
    print("STARTING SEQUENTIAL THINKING TEST - NO FUCKING HACKS")
    print("=" * 70)

    test_sequential_thinking()
    test_file_analysis()

    print("TESTS COMPLETE")
