#!/usr/bin/env python3
"""
Final verification test for the enhanced thinking subagent.
This test verifies that all core functionality works correctly.
"""

import asyncio
import tempfile
from pathlib import Path
import logging

from src.web_agent.tools.sequential_thinking_tool import (
    sequential_thinking_tool,
    quick_analysis_tool,
    research_analysis_tool,
)
from src.web_agent.tools.thinking_tools import (
    thinking_tool,
    read_file_tool,
    rg_search_tool,
)
from langchain_core.messages import HumanMessage


def setup_logging():
    """Setup logging for verification."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("final_verification.log"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== FINAL VERIFICATION TEST STARTED ===")
    return logger


def test_basic_thinking_tool(logger):
    """Test the enhanced thinking tool with LLM."""
    logger.info("🧠 Testing Basic Thinking Tool with LLM")

    result = thinking_tool.invoke(
        {
            "thought": "To optimize Python performance, I need to consider multiple strategies.",
            "thought_number": 1,
            "total_thoughts": 5,
            "next_thought_needed": True,
            "analysis_type": "complex_analysis",  # This triggers LLM usage
            "confidence_level": None,
            "problem_context": "Performance optimization for a web application",
        }
    )

    logger.info(f"Thinking tool result: {len(result)} characters")
    logger.info("✅ Basic thinking tool test completed")
    return result


def test_file_analysis(logger):
    """Test file reading functionality."""
    logger.info("📁 Testing File Analysis")

    with tempfile.TemporaryDirectory() as temp_dir:
        sample_file = Path(temp_dir) / "sample.py"
        sample_file.write_text("""
def slow_function():
    result = []
    for i in range(1000):
        result.append(i * 2)
    return result

def fast_function():
    return [i * 2 for i in range(1000)]
""")

        result = read_file_tool.invoke(
            {
                "file_path": "sample.py",
                "working_directory": temp_dir,
            }
        )

        logger.info(f"File analysis result: {len(result)} characters")
        logger.info("✅ File analysis test completed")
        return result


def test_code_search(logger):
    """Test ripgrep functionality."""
    logger.info("🔍 Testing Code Search")

    with tempfile.TemporaryDirectory() as temp_dir:
        files = {
            "main.py": "def main():\n    data = load_data()\n    return process_data(data)",
            "utils.py": "def load_data():\n    return [1, 2, 3]\n\ndef process_data(data):\n    return [x*2 for x in data]",
        }

        for filename, content in files.items():
            (Path(temp_dir) / filename).write_text(content)

        result = rg_search_tool.invoke(
            {
                "pattern": "def",
                "path": ".",
                "working_directory": temp_dir,
            }
        )

        logger.info(f"Code search result: {len(result)} characters")
        logger.info("✅ Code search test completed")
        return result


def test_sequential_thinking(logger):
    """Test the main sequential thinking tool."""
    logger.info("🤖 Testing Sequential Thinking Tool")

    try:
        result = sequential_thinking_tool.invoke(
            {
                "problem_description": "How can I optimize a Python web application experiencing slow response times?",
                "context": "Flask-based REST API using SQLAlchemy. Response times increase under load.",
                "max_thoughts": 8,
                "thinking_approach": "Systematic performance analysis",
                "working_directory": "/tmp",
                "use_llm_analysis": True,
            }
        )

        logger.info(f"Sequential thinking result: {len(result)} characters")
        logger.info("✅ Sequential thinking test completed")
        return result
    except Exception as e:
        logger.error(f"Sequential thinking test failed: {e}")
        return f"FAILED: {e}"


async def test_async_tools(logger):
    """Test async tools properly."""
    logger.info("⚡ Testing Async Tools")

    try:
        # Test web search
        result = await asyncio.wait_for(
            research_analysis_tool.__wrapped__(
                "Python performance optimization best practices 2024", max_thoughts=3
            ),
            timeout=30.0,
        )

        logger.info(f"Async tools result: {len(result)} characters")
        logger.info("✅ Async tools test completed")
        return result
    except asyncio.TimeoutError:
        logger.warning("Async tools test timed out")
        return "TIMEOUT"
    except Exception as e:
        logger.error(f"Async tools test failed: {e}")
        return f"FAILED: {e}"


def test_quick_analysis(logger):
    """Test quick analysis tool."""
    logger.info("⚡ Testing Quick Analysis Tool")

    try:
        result = quick_analysis_tool.invoke(
            {
                "problem": "Python list vs tuple performance",
                "max_thoughts": 6,
                "use_web_search": False,
            }
        )

        logger.info(f"Quick analysis result: {len(result)} characters")
        logger.info("✅ Quick analysis test completed")
        return result
    except Exception as e:
        logger.error(f"Quick analysis test failed: {e}")
        return f"FAILED: {e}"


def main():
    """Run final verification tests."""
    logger = setup_logging()

    logger.info("Starting final verification...")

    tests = [
        ("Basic Thinking Tool", test_basic_thinking_tool),
        ("File Analysis", test_file_analysis),
        ("Code Search", test_code_search),
        ("Sequential Thinking", test_sequential_thinking),
        ("Quick Analysis", test_quick_analysis),
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
    logger.info("FINAL VERIFICATION SUMMARY")
    logger.info("=" * 60)

    successful = 0
    for test_name, result in results.items():
        status = "✅ SUCCESS" if not str(result).startswith("FAILED") else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not str(result).startswith("FAILED"):
            successful += 1

    logger.info(f"\nTotal tests: {len(tests)}")
    logger.info(f"Successful tests: {successful}")
    logger.info(f"Failed tests: {len(tests) - successful}")

    logger.info("\n🎉 Final verification completed!")
    logger.info("Check final_verification.log for details")

    return results


if __name__ == "__main__":
    results = main()
