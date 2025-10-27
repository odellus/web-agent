import subprocess
import json


@tool
def ast_grep_search(pattern: str, path: str = ".", language: str = "python") -> str:
    """Run structural code search using ast-grep patterns.

    Args:
        pattern: ast-grep pattern (e.g., "requests.get($ARG)")
        path: Directory to search (default: current directory)
        language: Programming language (default: python)

    Returns:
        JSON string with matches and context
    """

    cmd = ["ast-grep", "scan", "--pattern", pattern, "--lang", language, "--json", path]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout
    else:
        return f"Error: {result.stderr}"
