"""Tool adapter for ACP integration.

This module provides an adapter between the ACP protocol tool interface
and the existing web-agent tools, handling tool discovery, execution,
and result formatting.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from web_agent.tools import all_tools, tools_registry
from ..protocol.types import (
    ACPTool,
    ToolSchema,
    ToolParameter,
    ToolResult,
    MessageContent,
)
from ..protocol.sessions import get_session_manager

logger = logging.getLogger(__name__)


class ToolAdapter:
    """Adapter between ACP protocol and web-agent tools."""

    def __init__(self):
        """Initialize the tool adapter."""
        self.session_manager = get_session_manager()
        self._tool_cache = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools in ACP format.

        Returns:
            List of tool definitions in ACP format
        """
        if self._tool_cache is None:
            self._tool_cache = []
            for tool in all_tools:
                acp_tool = self._convert_tool_to_acp(tool)
                self._tool_cache.append(acp_tool.model_dump())

        return self._tool_cache

    def _convert_tool_to_acp(self, tool) -> ACPTool:
        """Convert a web-agent tool to ACP format.

        Args:
            tool: Web-agent tool instance

        Returns:
            ACP tool definition
        """
        # Get tool schema
        schema = {}
        if hasattr(tool, "args_schema") and tool.args_schema:
            schema = tool.args_schema.model_json_schema()
        else:
            # Default schema for tools without args_schema
            schema = {"type": "object", "properties": {}, "required": []}

        # Convert to ACP format
        properties = {}
        required = []

        if "properties" in schema:
            for prop_name, prop_def in schema["properties"].items():
                # Convert property definition
                param = ToolParameter(
                    name=prop_name,
                    description=prop_def.get("description", ""),
                    type=prop_def.get("type", "string"),
                    required=prop_name in schema.get("required", []),
                    default=prop_def.get("default"),
                    enum=prop_def.get("enum"),
                )
                properties[prop_name] = param

        if "required" in schema:
            required = schema["required"]

        tool_schema = ToolSchema(
            type="object",
            properties=properties,
            required=required,
        )

        return ACPTool(
            name=tool.name,
            description=tool.description,
            input_schema=tool_schema,
        )

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> ToolResult:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            session_id: Optional session ID for context

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
            RuntimeError: If tool execution fails
        """
        logger.info(f"Calling tool {tool_name} with args {arguments}")

        # Find the tool
        tool = None
        for t in all_tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        try:
            # Get session context if available
            working_directory = None
            if session_id:
                session = await self.session_manager.get_session(session_id)
                if session:
                    working_directory = session.working_directory

            # Prepare arguments with context
            prepared_args = await self._prepare_tool_arguments(
                tool, arguments, working_directory
            )

            # Execute the tool
            result = tool.invoke(prepared_args)

            # Convert result to ACP format
            return self._format_tool_result(result)

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            # Return error result
            return ToolResult(
                content=[
                    MessageContent(
                        type="text",
                        text=f"Error executing tool {tool_name}: {str(e)}",
                    )
                ],
                is_error=True,
            )

    async def _prepare_tool_arguments(
        self,
        tool,
        arguments: Dict[str, Any],
        working_directory: Optional[Path],
    ) -> Dict[str, Any]:
        """Prepare tool arguments with context.

        Args:
            tool: Tool instance
            arguments: Original arguments
            working_directory: Optional working directory

        Returns:
            Prepared arguments with context
        """
        prepared_args = arguments.copy()

        # Inject working directory for tools that need it
        if working_directory and hasattr(tool, "args"):
            # Check if tool expects working_directory parameter
            if hasattr(tool, "args_schema") and tool.args_schema:
                schema = tool.args_schema.model_json_schema()
                if "working_directory" in schema.get("properties", {}):
                    prepared_args["working_directory"] = working_directory

        # Special handling for specific tools
        if tool.name == "bash_tool":
            # Ensure bash commands run in the correct directory
            if working_directory:
                prepared_args["working_directory"] = working_directory

        elif tool.name == "edit_tool":
            # Handle file paths relative to working directory
            if "file_path" in prepared_args and working_directory:
                file_path = prepared_args["file_path"]
                if not Path(file_path).is_absolute():
                    prepared_args["file_path"] = working_directory / file_path

        return prepared_args

    def _format_tool_result(self, result: Any) -> ToolResult:
        """Format tool result for ACP.

        Args:
            result: Raw tool result

        Returns:
            Formatted tool result
        """
        # Convert result to string
        if isinstance(result, str):
            content_text = result
        elif isinstance(result, dict):
            content_text = str(result)
        elif hasattr(result, "content"):
            content_text = str(result.content)
        else:
            content_text = str(result)

        # Create message content
        content = [MessageContent(type="text", text=content_text)]

        # Determine if it's an error
        is_error = (
            content_text.startswith("Error:")
            or content_text.startswith("Exception:")
            or "failed" in content_text.lower()
        )

        return ToolResult(content=content, is_error=is_error)

    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool information or None if not found
        """
        tools = await self.list_tools()
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        return None

    def get_tool_names(self) -> List[str]:
        """Get list of available tool names.

        Returns:
            List of tool names
        """
        return [tool.name for tool in all_tools]

    async def validate_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a tool call before execution.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Validation result with 'valid' boolean and optional 'error'
        """
        # Check if tool exists
        tool = None
        for t in all_tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            return {
                "valid": False,
                "error": f"Tool '{tool_name}' not found",
            }

        # Validate arguments if tool has schema
        if hasattr(tool, "args_schema") and tool.args_schema:
            try:
                # Get schema to check required fields
                schema = tool.args_schema.model_json_schema()
                required_fields = schema.get("required", [])

                # For tools that get working_directory injected, don't require it in validation
                if tool_name == "bash_tool" and "working_directory" in required_fields:
                    # Create a copy of arguments with a dummy working_directory for validation
                    validation_args = arguments.copy()
                    if "working_directory" not in validation_args:
                        validation_args["working_directory"] = "/tmp"

                    # Try to validate arguments
                    tool.args_schema(**validation_args)
                    return {"valid": True}
                else:
                    # Try to validate arguments as-is
                    tool.args_schema(**arguments)
                    return {"valid": True}
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Invalid arguments: {str(e)}",
                }

        # No validation needed
        return {"valid": True}

    def clear_cache(self):
        """Clear the tool cache."""
        self._tool_cache = None
        logger.info("Tool cache cleared")

    def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool statistics.

        Returns:
            Dictionary with tool statistics
        """
        return {
            "total_tools": len(all_tools),
            "cached_tools": len(self._tool_cache) if self._tool_cache else 0,
            "tool_names": self.get_tool_names(),
        }
