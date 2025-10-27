"""Agent Client Protocol (ACP) method implementations.

This module implements the core ACP methods that handle agent-editor communication.
Each method follows the ACP specification and provides proper error handling.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from .types import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    ACPErrorCode,
    InitializeParams,
    InitializeResult,
    SessionParams,
    SessionResult,
    PromptParams,
    PromptResult,
    PromptUpdate,
    ToolCall,
    ToolResult,
    AgentCapabilities,
    ServerInfo,
    ACPMessage,
    MessageContent,
)
from ..adapters.langgraph_adapter import LangGraphAdapter
from ..adapters.tool_adapter import ToolAdapter

logger = logging.getLogger(__name__)


class ACPMethods:
    """ACP method implementations."""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.langgraph_adapter = LangGraphAdapter()
        self.tool_adapter = ToolAdapter()
        self.server_info = ServerInfo(
            name="web-agent-ACP",
            version="0.1.0",
        )
        self.capabilities = AgentCapabilities()

    async def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the ACP connection.

        Args:
            params: Initialization parameters including capabilities and client info

        Returns:
            Server capabilities and information
        """
        try:
            logger.info("Initializing ACP connection")

            # Parse initialization parameters
            init_params = InitializeParams(**params)

            # Initialize the LangGraph adapter
            await self.langgraph_adapter.initialize()

            # Return server capabilities
            result = InitializeResult(
                protocol_version="0.4.0",
                capabilities=self.capabilities,
                server_info=self.server_info,
            )

            logger.info("ACP connection initialized successfully")
            return result.model_dump()

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.INTERNAL_ERROR,
                message=f"Initialization failed: {str(e)}",
            )

    async def session_new(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session.

        Args:
            params: Session parameters including working directory

        Returns:
            Session information including ID and capabilities
        """
        try:
            logger.info("Creating new ACP session")

            # Parse session parameters
            session_params = SessionParams(**params)

            # Generate unique session ID
            session_id = str(uuid.uuid4())

            # Create session state
            working_dir = Path(session_params.working_directory or ".")

            # Initialize LangGraph session
            agent_state = await self.langgraph_adapter.create_session(
                session_id=session_id,
                working_directory=working_dir,
                metadata=session_params.metadata,
            )

            # Store session
            self.sessions[session_id] = {
                "state": agent_state,
                "working_directory": working_dir,
                "metadata": session_params.metadata or {},
                "created_at": asyncio.get_event_loop().time(),
            }

            # Get available models and modes
            available_models = ["qwen3:latest", "gpt-4", "claude-3-sonnet"]
            available_modes = ["execute", "plan", "safe"]

            result = SessionResult(
                session_id=session_id,
                capabilities=self.capabilities,
                available_models=available_models,
                available_modes=available_modes,
            )

            logger.info(f"Created session {session_id}")
            return result.model_dump()

        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.INTERNAL_ERROR,
                message=f"Session creation failed: {str(e)}",
            )

    async def session_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process a prompt in a session.

        Args:
            params: Prompt parameters including session ID and message

        Returns:
            Prompt result with response message
        """
        try:
            # Parse prompt parameters
            prompt_params = PromptParams(**params)
            session_id = prompt_params.session_id

            logger.info(f"Processing prompt in session {session_id}")

            # Validate session
            if session_id not in self.sessions:
                raise JSONRPCError(
                    code=ACPErrorCode.SESSION_NOT_FOUND,
                    message=f"Session {session_id} not found",
                )

            session = self.sessions[session_id]

            # Process prompt through LangGraph adapter
            async for update in self.langgraph_adapter.process_prompt(
                session_id=session_id,
                message=prompt_params.message,
                mode=prompt_params.mode,
                model=prompt_params.model,
            ):
                # This would be used for streaming updates
                # For now, we'll collect the final result
                pass

            # Get final result
            result = await self.langgraph_adapter.get_prompt_result(session_id)

            logger.info(f"Prompt processed successfully for session {session_id}")
            return result.model_dump()

        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"Prompt processing failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.AGENT_ERROR,
                message=f"Prompt processing failed: {str(e)}",
            )

    async def session_set_mode(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set the mode for a session.

        Args:
            params: Parameters including session ID and mode

        Returns:
            Success confirmation
        """
        try:
            session_id = params["session_id"]
            mode = params["mode"]

            logger.info(f"Setting mode {mode} for session {session_id}")

            # Validate session
            if session_id not in self.sessions:
                raise JSONRPCError(
                    code=ACPErrorCode.SESSION_NOT_FOUND,
                    message=f"Session {session_id} not found",
                )

            # Set mode through adapter
            await self.langgraph_adapter.set_mode(session_id, mode)

            return {"success": True, "mode": mode}

        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"Mode setting failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.INTERNAL_ERROR,
                message=f"Mode setting failed: {str(e)}",
            )

    async def session_set_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set the model for a session.

        Args:
            params: Parameters including session ID and model

        Returns:
            Success confirmation
        """
        try:
            session_id = params["session_id"]
            model = params["model"]

            logger.info(f"Setting model {model} for session {session_id}")

            # Validate session
            if session_id not in self.sessions:
                raise JSONRPCError(
                    code=ACPErrorCode.SESSION_NOT_FOUND,
                    message=f"Session {session_id} not found",
                )

            # Set model through adapter
            await self.langgraph_adapter.set_model(session_id, model)

            return {"success": True, "model": model}

        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"Model setting failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.INTERNAL_ERROR,
                message=f"Model setting failed: {str(e)}",
            )

    async def tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools.

        Args:
            params: Optional parameters (currently unused)

        Returns:
            List of available tools
        """
        try:
            logger.info("Listing available tools")

            # Get tools from adapter
            tools = await self.tool_adapter.list_tools()

            return {"tools": tools}

        except Exception as e:
            logger.error(f"Tool listing failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.INTERNAL_ERROR,
                message=f"Tool listing failed: {str(e)}",
            )

    async def tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call.

        Args:
            params: Parameters including tool name and arguments

        Returns:
            Tool execution result
        """
        try:
            tool_name = params["name"]
            arguments = params.get("arguments", {})
            session_id = params.get("session_id")

            logger.info(f"Calling tool {tool_name} with args {arguments}")

            # Execute tool through adapter
            result = await self.tool_adapter.call_tool(
                tool_name=tool_name,
                arguments=arguments,
                session_id=session_id,
            )

            logger.info(f"Tool {tool_name} executed successfully")
            return result.model_dump()

        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.TOOL_ERROR, message=f"Tool execution failed: {str(e)}"
            )

    async def session_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel an ongoing session operation.

        Args:
            params: Parameters including session ID

        Returns:
            Success confirmation
        """
        try:
            session_id = params["session_id"]

            logger.info(f"Cancelling operations in session {session_id}")

            # Validate session
            if session_id not in self.sessions:
                raise JSONRPCError(
                    code=ACPErrorCode.SESSION_NOT_FOUND,
                    message=f"Session {session_id} not found",
                )

            # Cancel through adapter
            await self.langgraph_adapter.cancel_session(session_id)

            return {"success": True}

        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"Session cancellation failed: {e}")
            raise JSONRPCError(
                code=ACPErrorCode.INTERNAL_ERROR,
                message=f"Session cancellation failed: {str(e)}",
            )

    def get_method_handler(self, method_name: str):
        """Get the handler for a specific ACP method.

        Args:
            method_name: Name of the ACP method

        Returns:
            Async handler function or None if not found
        """
        method_map = {
            "initialize": self.initialize,
            "session/new": self.session_new,
            "session/prompt": self.session_prompt,
            "session/set_mode": self.session_set_mode,
            "session/set_model": self.session_set_model,
            "session/cancel": self.session_cancel,
            "tools/list": self.tools_list,
            "tools/call": self.tools_call,
        }

        return method_map.get(method_name)
