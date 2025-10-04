copilotkit-work/web-agent/agent-py/tests/test_working_directory.py
```python
"""Test enhanced bash tool with working directory injection."""

import os
import tempfile
import asyncio
from pathlib import Path
from langchain_core.messages import HumanMessage
from web_agent.tools.bash_tool import bash_tool
from web_agent.state import TraeWebState


async def test_bash_tool_with_working_directory():
    """Test that bash tool respects injected working directory."""

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing in temporary directory: {temp_dir}")

        # Test command that creates a file
        test_command = "echo 'test content' > test_file.txt"

        # Call bash tool directly with working directory injection
        result = bash_tool.invoke({
            "command": test_command,
            "working_directory": temp_dir,
            "restart": False
        })

        print(f"Bash tool result: {result}")

        # Check if file was created in the correct directory
        expected_file = Path(temp_dir) / "test_file.txt"
        if expected_file.exists():
            print("✓ File created in correct working directory")
            content = expected_file.read_text()
            print(f"File content: {content}")
        else:
            print("✗ File not found in expected location")

        # Test listing files in the working directory
        list_result = bash_tool.invoke({
            "command": "ls -la",
            "working_directory": temp_dir,
            "restart": False
        })

        print(f"Directory listing: {list_result}")


async def test_state_with_working_directory():
    """Test that TraeWebState can store working directory."""

    test_dir = "/home/user/test_project"
    state = TraeWebState(
        messages=[HumanMessage(content="test")],
        remaining_steps=5,
        working_directory=test_dir
    )

    print(f"State working directory: {state['working_directory']}")
    assert state["working_directory"] == test_dir
    print("✓ Working directory stored in state correctly")


async def test_multiple_commands_same_directory():
    """Test multiple commands in the same working directory."""

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nTesting multiple commands in: {temp_dir}")

        # Create a file
        create_result = bash_tool.invoke({
            "command": "touch first_file.txt",
            "working_directory": temp_dir,
            "restart": False
        })

        # List files
        list_result = bash_tool.invoke({
            "command": "ls",
            "working_directory": temp_dir,
            "restart": False
        })

        print(f"Create result: {create_result}")
        print(f"List result: {list_result}")

        # Verify files exist
        files = list(Path(temp_dir).iterdir())
        print(f"Files in directory: {[f.name for f in files]}")


async def main():
    """Run all working directory tests."""
    print("=== Testing Working Directory Injection ===\n")

    await test_state_with_working_directory()
    print()

    await test_bash_tool_with_working_directory()
    print()

    await test_multiple_commands_same_directory()
    print("\n=== All tests completed ===")


if __name__ == "__main__":
    asyncio.run(main())
