#!/usr/bin/env python3
"""
Comprehensive test of the enhanced thinking subagent with logging and LLM integration.
"""

import asyncio
import tempfile
from pathlib import Path
import logging

from src.web_agent.tools.sequential_thinking_tool import (
    sequential_thinking_tool,
    quick_analysis_tool,
    research_analysis_tool,
    code_analysis_tool,
)
from src.web_agent.tools.thinking_tools import (
    thinking_tool,
    web_search_tool,
    read_file_tool,
    rg_search_tool,
)
from src.web_agent.tools.thinking_agent import run_thinking_agent, ThinkingAgentState
from langchain_core.messages import HumanMessage


def setup_logging():
    """Setup comprehensive logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("comprehensive_test.log"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== COMPREHENSIVE THINKING AGENT TEST STARTED ===")
    return logger


def test_thinking_tool_with_llm(logger):
    """Test the enhanced thinking tool with LLM integration."""
    logger.info("🧠 Testing Enhanced Thinking Tool with LLM")

    result = thinking_tool.invoke(
        {
            "thought": "To optimize Python performance, I need to consider multiple strategies including code efficiency, library usage, and system configuration.",
            "thought_number": 1,
            "total_thoughts": 5,
            "next_thought_needed": True,
            "analysis_type": "complex_analysis",  # This triggers LLM usage
            "confidence_level": None,
            "problem_context": "Performance optimization for a web application",
        }
    )

    logger.info(f"Thinking tool result length: {len(result)} characters")
    logger.info("✅ Thinking tool test completed")
    return result


def test_file_analysis_with_logging(logger):
    """Test file analysis with comprehensive logging."""
    logger.info("📁 Testing File Analysis with Logging")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample Python file
        sample_file = Path(temp_dir) / "sample.py"
        sample_file.write_text("""
def slow_data_processing(data):
    result = []
    for item in data:
        if item > 0:
            new_item = item * 2
            result.append(new_item)
    return result

def fast_data_processing(data):
    return [item * 2 for item in data if item > 0]
""")

        result = read_file_tool.invoke(
            {
                "file_path": "sample.py",
                "working_directory": temp_dir,
            }
        )

        logger.info(f"File read result length: {len(result)} characters")
        logger.info("✅ File analysis test completed")
        return result


def test_code_search_with_logging(logger):
    """Test code search with logging."""
    logger.info("🔍 Testing Code Search with Logging")

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

        logger.info(f"RG search result length: {len(result)} characters")
        logger.info("✅ Code search test completed")
        return result


def test_sequential_thinking_with_llm(logger):
    """Test the enhanced sequential thinking tool with LLM."""
    logger.info("🤖 Testing Sequential Thinking with LLM Subagent")

    result = sequential_thinking_tool.invoke(
        {
            "problem_description": "How can I optimize a Python web application experiencing slow response times under high load?",
            "context": "The application is a Flask-based REST API using SQLAlchemy. Response times increase from 200ms to 2000ms under 100 concurrent users.",
            "max_thoughts": 8,
            "thinking_approach": "Systematic performance analysis covering database queries, caching, and infrastructure",
            "working_directory": "/tmp",
            "use_llm_analysis": True,
        }
    )

    logger.info(f"Sequential thinking result length: {len(result)} characters")
    logger.info("✅ Sequential thinking test completed")
    return result


def test_quick_analysis(logger):
    """Test quick analysis tool."""
    logger.info("⚡ Testing Quick Analysis Tool")

    result = quick_analysis_tool.invoke(
        {
            "problem": "Python list vs tuple performance",
            "max_thoughts": 6,
            "use_web_search": False,
        }
    )

    logger.info(f"Quick analysis result length: {len(result)} characters")
    logger.info("✅ Quick analysis test completed")
    return result


def test_research_analysis(logger):
    """Test research analysis tool."""
    logger.info("🔬 Testing Research Analysis Tool")

    result = research_analysis_tool.invoke(
        {
            "research_question": "What are the best practices for Python performance optimization in 2024?",
            "search_query": "Python performance optimization best practices 2024",
            "max_thoughts": 10,
        }
    )

    logger.info(f"Research analysis result length: {len(result)} characters")
    logger.info("✅ Research analysis test completed")
    return result


def test_code_analysis(logger):
    """Test code analysis tool."""
    logger.info("💻 Testing Code Analysis Tool")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "test_performance.py"
        test_file.write_text("""
import time

def slow_function():
    result = []
    for i in range(1000):
        result.append(i * 2)
    return result

def fast_function():
    return [i * 2 for i in range(1000)]

def inefficient_string_concat(names):
    message = ""
    for name in names:
        message += name + ", "
    return message
""")

        result = code_analysis_tool.invoke(
            {
                "file_path": "test_performance.py",
                "analysis_type": "performance_analysis",
                "max_thoughts": 8,
                "working_directory": temp_dir,
            }
        )

        logger.info(f"Code analysis result length: {len(result)} characters")
        logger.info("✅ Code analysis test completed")
        return result


def test_direct_thinking_agent(logger):
    """Test the thinking agent directly."""
    logger.info("🧠 Testing Direct Thinking Agent")

    async def run_direct_agent():
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
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

            # Run thinking agent directly
            result = await run_thinking_agent(
                initial_message="Analyze this Python code for performance optimizations. Use the tools to examine the code structure.",
                problem_context="Code performance analysis",
                max_thoughts=5,
                working_directory=temp_dir,
            )

            logger.info(f"Direct agent result length: {len(result)} characters")
            return result

    try:
        result = asyncio.run(run_direct_agent())
        logger.info("✅ Direct thinking agent test completed")
        return result
    except Exception as e:
        logger.error(f"Direct agent test failed: {e}")
        return f"Direct agent test failed: {e}"


def main():
    """Run all comprehensive tests."""
    logger = setup_logging()

    logger.info("Starting comprehensive test suite...")

    tests = [
        ("Enhanced Thinking Tool", test_thinking_tool_with_llm),
        ("File Analysis", test_file_analysis_with_logging),
        ("Code Search", test_code_search_with_logging),
        ("Sequential Thinking", test_sequential_thinking_with_llm),
        ("Quick Analysis", test_quick_analysis),
        ("Research Analysis", test_research_analysis),
        ("Code Analysis", test_code_analysis),
        ("Direct Thinking Agent", test_direct_thinking_agent),
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'=' * 60}")

        try:
            result = test_func(logger)
            results[test_name] = result
            logger.info(f"✅ {test_name} - SUCCESS")
        except Exception as e:
            logger.error(f"❌ {test_name} - FAILED: {e}")
            results[test_name] = f"FAILED: {e}"

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("COMPREHENSIVE TEST SUMMARY")
    logger.info("=" * 60)

    for test_name, result in results.items():
        status = (
            "✅ SUCCESS"
            if isinstance(result, str) and not result.startswith("FAILED")
            else "❌ FAILED"
        )
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nTotal tests: {len(tests)}")
    successful_tests = sum(
        1 for r in results.values() if isinstance(r, str) and not r.startswith("FAILED")
    )
    logger.info(f"Successful tests: {successful_tests}")
    logger.info(f"Failed tests: {len(tests) - successful_tests}")

    logger.info("\n🎉 Comprehensive test suite completed!")
    logger.info("Check the log files for detailed information:")
    logger.info("- comprehensive_test.log")
    logger.info("- thinking_agent.log")
    logger.info("- thinking_tools.log")
    logger.info("- sequential_thinking.log")

    return results


if __name__ == "__main__":
    results = main()
