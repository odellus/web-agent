copilotkit-work/web-agent/agent-py/tests/test_wd_injection.py
```python
"""Simple test for working directory injection."""

import os
import tempfile
from pathlib import Path
from web_agent.state import TraeWebState
from web_agent.tools.bash_tool import bash_tool

def test_bash_tool_with_injected_directory():
    """Test bash tool respects injected working directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing in: {temp_dir}")

        # Test creating file in temp directory
        result = bash_tool.invoke({
            "command": "echo 'test content' > test_file.txt",
            "working_directory": temp_dir
        })

        print(f"Command result: {result}")

        # Verify file was created in correct location
        test_file = Path(temp_dir) / "test_file.txt"
        if test_file.exists():
            content = test_file.read_text()
            print(f"✓ File created successfully: {content}")
            return True
        else:
            print("✗ File not found in expected location")
            return False

def test_state_working_directory():
    """Test TraeWebState can store working directory."""
    test_path = "/home/user/test_project"
    state = TraeWebState(
        messages=[],
        remaining_steps=5,
        working_directory=test_path
    )

    if state.working_directory == test_path:
        print(f"✓ State working directory: {state.working_directory}")
        return True
    else:
        print(f"✗ Expected {test_path}, got {state.working_directory}")
        return False

if __name__ == "__main__":
    print("=== Testing Working Directory Injection ===\n")

    success1 = test_state_working_directory()
    print()

    success2 = test_bash_tool_with_injected_directory()
    print()

    if success1 and success2:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
