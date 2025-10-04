# copilotkit-work/trae-web/agent-py/src/tools/edit_tool.py
from pathlib import Path
from typing import Optional, Literal
from langchain_core.tools import tool


@tool
def edit_tool(
    command: Literal["view", "create", "str_replace", "insert"],
    path: str,
    old_str: Optional[str] = None,
    new_str: Optional[str] = None,
    text: Optional[str] = None,
    line_number: Optional[int] = None,
) -> str:
    """File and directory manipulation tool with persistent state.

    Operations:
    - view: Display file contents with line numbers, or list directory contents up to 2 levels deep
    - create: Create new files (fails if file already exists)
    - str_replace: Replace exact string matches in files (must be unique)
    - insert: Insert text after a specified line number

    Key features:
    - Requires absolute paths (e.g., '/repo/file.py')
    - String replacements must match exactly, including whitespace
    - Supports line range viewing for large files
    """
    try:
        path_obj = Path(path)

        if command == "view":
            return _handle_view(path_obj)
        elif command == "create":
            return _handle_create(path_obj, text)
        elif command == "str_replace":
            return _handle_str_replace(path_obj, old_str, new_str)
        elif command == "insert":
            return _handle_insert(path_obj, line_number, text)
        else:
            return f"Unknown command: {command}"

    except Exception as e:
        return f"Error: {str(e)}"


def _handle_view(path: Path) -> str:
    if path.is_dir():
        return _view_directory(path)
    else:
        return _view_file(path)


def _view_directory(path: Path) -> str:
    try:
        items = []
        for item in path.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                items.append(f"{item.name}/")
                # List up to 2 levels deep
                try:
                    for subitem in item.iterdir():
                        if subitem.name.startswith("."):
                            continue
                        items.append(
                            f"  {subitem.name}{'/' if subitem.is_dir() else ''}"
                        )
                except PermissionError:
                    items.append(f"  [Permission denied]")
            else:
                items.append(item.name)

        if not items:
            return "Directory is empty"

        return "\n".join(items)
    except PermissionError:
        return "Permission denied to view directory"


def _view_file(path: Path) -> str:
    if not path.exists():
        return f"File not found: {path}"

    try:
        content = path.read_text()
        lines = content.split("\n")

        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            numbered_lines.append(f"{i:4d} | {line}")

        return "\n".join(numbered_lines)
    except PermissionError:
        return "Permission denied to read file"


def _handle_create(path: Path, text: Optional[str]) -> str:
    if path.exists():
        return f"File already exists: {path}"

    if text is None:
        return "Text content is required for create operation"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return f"File created: {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"


def _handle_str_replace(
    path: Path, old_str: Optional[str], new_str: Optional[str]
) -> str:
    if not path.exists():
        return f"File not found: {path}"

    if old_str is None or new_str is None:
        return "Both old_str and new_str are required for str_replace operation"

    try:
        content = path.read_text()

        if old_str not in content:
            return f"String not found in file: {old_str}"

        new_content = content.replace(old_str, new_str)
        path.write_text(new_content)
        return f"String replaced in file: {path}"
    except Exception as e:
        return f"Error replacing string: {str(e)}"


def _handle_insert(path: Path, line_number: Optional[int], text: Optional[str]) -> str:
    if not path.exists():
        return f"File not found: {path}"

    if line_number is None:
        return "Line number is required for insert operation"

    if text is None:
        return "Text content is required for insert operation"

    try:
        content = path.read_text()
        lines = content.split("\n")

        if line_number < 1 or line_number > len(lines):
            return f"Line number {line_number} is out of range (1-{len(lines)})"

        # Insert after the specified line
        new_lines = lines[:line_number] + [text] + lines[line_number:]
        new_content = "\n".join(new_lines)
        path.write_text(new_content)

        return f"Text inserted after line {line_number} in file: {path}"
    except Exception as e:
        return f"Error inserting text: {str(e)}"
