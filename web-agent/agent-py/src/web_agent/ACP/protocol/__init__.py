"""Agent Client Protocol (ACP) protocol implementation.

This package contains the core ACP protocol implementation, including
type definitions, method handlers, session management, and streaming
utilities.

Modules:
- types: Type definitions and schemas for ACP protocol
- methods: ACP method implementations
- sessions: Session management and lifecycle
- streaming: Streaming utilities for real-time communication
"""

from .types import (
    ACPTool,
    ACPMessage,
    AgentCapabilities,
    InitializeParams,
    InitializeResult,
    SessionParams,
    SessionResult,
    PromptParams,
    PromptResult,
    ToolCall,
    ToolResult,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCError,
    ACPErrorCode,
)
from .methods import ACPMethods
from .sessions import SessionManager, SessionState, get_session_manager
from .streaming import (
    NDJSONStreamer,
    StreamParser,
    StreamingSession,
    StreamBuffer,
    create_stdio_streamer,
    create_websocket_streamer,
)

__all__ = [
    # Type definitions
    "ACPTool",
    "ACPMessage",
    "AgentCapabilities",
    "InitializeParams",
    "InitializeResult",
    "SessionParams",
    "SessionResult",
    "PromptParams",
    "PromptResult",
    "ToolCall",
    "ToolResult",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCNotification",
    "JSONRPCError",
    "ACPErrorCode",
    # Protocol implementation
    "ACPMethods",
    # Session management
    "SessionManager",
    "SessionState",
    "get_session_manager",
    # Streaming
    "NDJSONStreamer",
    "StreamParser",
    "StreamingSession",
    "StreamBuffer",
    "create_stdio_streamer",
    "create_websocket_streamer",
]
