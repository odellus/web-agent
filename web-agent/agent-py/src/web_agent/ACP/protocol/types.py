"""Agent Client Protocol (ACP) type definitions.

This module defines the core types and schemas used in the ACP protocol,
following the ACP specification for agent-editor communication.
"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum


class JSONRPCVersion(BaseModel):
    """JSON-RPC version."""

    jsonrpc: Literal["2.0"] = "2.0"


class ACPErrorCode(int, Enum):
    """ACP error codes following JSON-RPC and ACP specifications."""

    # JSON-RPC standard errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # ACP specific errors
    AGENT_ERROR = -32000
    TOOL_ERROR = -32001
    PERMISSION_DENIED = -32002
    SESSION_NOT_FOUND = -32003
    SESSION_EXPIRED = -32004
    UNSUPPORTED_OPERATION = -32005


class JSONRPCError(BaseModel):
    """JSON-RPC error object."""

    code: ACPErrorCode
    message: str
    data: Optional[Dict[str, Any]] = None


class JSONRPCRequest(JSONRPCVersion):
    """JSON-RPC request object."""

    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class JSONRPCResponse(JSONRPCVersion):
    """JSON-RPC response object."""

    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[JSONRPCError] = None


class JSONRPCNotification(JSONRPCVersion):
    """JSON-RPC notification object (no response expected)."""

    method: str
    params: Optional[Dict[str, Any]] = None


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    name: str
    description: str
    type: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class ToolSchema(BaseModel):
    """Tool input schema."""

    type: Literal["object"] = "object"
    properties: Dict[str, ToolParameter]
    required: List[str] = []


class ACPTool(BaseModel):
    """ACP tool definition."""

    name: str
    description: str
    input_schema: ToolSchema


class MessageContent(BaseModel):
    """Message content item."""

    type: Literal["text", "image", "embedded_resource"]
    text: Optional[str] = None
    image_url: Optional[str] = None
    resource: Optional[Dict[str, Any]] = None


class ACPMessage(BaseModel):
    """ACP message object."""

    role: Literal["user", "assistant", "system"]
    content: List[MessageContent]


class PromptCapabilities(BaseModel):
    """Prompt capabilities."""

    image: bool = False
    embedded_context: bool = True


class FileSystemCapabilities(BaseModel):
    """File system capabilities."""

    read_text_file: bool = True
    write_text_file: bool = True
    list_directory: bool = False
    create_directory: bool = False
    delete_file: bool = False


class TerminalCapabilities(BaseModel):
    """Terminal capabilities."""

    create: bool = True
    resize: bool = True
    send_input: bool = True
    read_output: bool = True


class AgentCapabilities(BaseModel):
    """Agent capabilities."""

    prompt: PromptCapabilities = Field(default_factory=PromptCapabilities)
    fs: FileSystemCapabilities = Field(default_factory=FileSystemCapabilities)
    terminal: TerminalCapabilities = Field(default_factory=TerminalCapabilities)


class ServerInfo(BaseModel):
    """Server information."""

    name: str
    version: str


class InitializeParams(BaseModel):
    """Initialize parameters."""

    protocol_version: str = "0.4.0"
    capabilities: Optional[AgentCapabilities] = None
    client_info: Optional[ServerInfo] = None
    working_directory: Optional[str] = None


class InitializeResult(BaseModel):
    """Initialize result."""

    protocol_version: str = "0.4.0"
    capabilities: AgentCapabilities
    server_info: ServerInfo


class SessionParams(BaseModel):
    """Session creation parameters."""

    working_directory: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionResult(BaseModel):
    """Session creation result."""

    session_id: str
    capabilities: AgentCapabilities
    available_models: List[str]
    available_modes: List[str]


class PromptParams(BaseModel):
    """Prompt parameters."""

    session_id: str
    message: str
    mode: Optional[str] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolCall(BaseModel):
    """Tool call request."""

    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """Tool execution result."""

    content: List[MessageContent]
    is_error: bool = False


class PromptUpdate(BaseModel):
    """Prompt update notification."""

    session_id: str
    message: Optional[ACPMessage] = None
    tool_call: Optional[ToolCall] = None
    tool_result: Optional[ToolResult] = None
    done: bool = False
    error: Optional[str] = None


class PromptResult(BaseModel):
    """Prompt completion result."""

    message: ACPMessage
    stop_reason: Literal["user_stop", "tool_call_limit", "completion", "error"]
    usage: Optional[Dict[str, Any]] = None


# Type aliases for common patterns
ACPRequest = Union[JSONRPCRequest, JSONRPCNotification]
ACPResponse = Union[JSONRPCResponse, JSONRPCNotification]
