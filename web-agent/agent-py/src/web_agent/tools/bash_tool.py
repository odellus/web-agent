# copilotkit-work/trae-web/agent-py/src/tools/bash_tool.py
import subprocess
import os
from pydantic import DirectoryPath
from typing import Optional
from typing_extensions import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState


@tool
def bash_tool(
    command: str,
    working_directory: Annotated[DirectoryPath, InjectedState("working_directory")],
    restart: bool = False,
) -> str:
    """Execute shell commands synchronously.

    Features:
    - Commands run in a fresh subprocess each time
    - Simple and reliable execution
    - No persistent state to worry about

    Usage notes:
    - Avoid commands with excessive output
    - Use relative paths when possible
    - Commands like `touch`, `echo`, `mkdir` work well

    Args:
        command: The bash command to execute
        restart: Ignored - kept for compatibility
    """
    try:
        # Run the command and capture output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
            cwd=str(working_directory),  # Use injected working directory
        )

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"

        return output

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"
