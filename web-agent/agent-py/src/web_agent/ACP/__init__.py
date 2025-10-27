"""Agent Client Protocol (ACP) integration for web-agent.

This package provides a complete ACP implementation for connecting the web-agent
to Zed editor through the Agent Client Protocol.

ACP is essentially the LSP for AI coding agents - a standardized protocol
that enables interoperability between different AI agents and code editors.

Architecture:
- protocol/: Core ACP protocol implementation
  - types.py: Type definitions and schemas
  - methods.py: ACP method implementations
  - sessions.py: Session management
  - streaming.py: Streaming utilities
- adapters/: Integration adapters
  - langgraph_adapter.py: LangGraph agent integration
  - tool_adapter.py: Tool system integration
- utils/: Utility modules
  - json_rpc.py: JSON-RPC 2.0 utilities
  - ndjson.py: NDJSON streaming utilities
- server.py: ACP server (WebSocket and stdio)
- client.py: ACP client (stdio for Zed)

Usage:
1. As a WebSocket server (for development/testing):
   python -m web_agent.ACP --transport websocket --port 8095

2. As a stdio client (for Zed integration):
   python -m web_agent.ACP --transport stdio --working-dir /path/to/project

3. Configure in Zed settings:
   {
     "agents": {
       "web-agent": {
         "command": ["python", "-m", "web_agent.ACP"],
         "args": ["--transport", "stdio", "--working-dir", "{workspace}"]
       }
     }
   }
"""

from .server import ACPServer
from .client import ACPClient, ACPStdioClient
from .protocol.types import (
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
)
from .protocol.sessions import SessionManager, SessionState, get_session_manager
from .adapters.langgraph_adapter import LangGraphAdapter
from .adapters.tool_adapter import ToolAdapter

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "ACPServer",
    "ACPClient",
    "ACPStdioClient",
    # Protocol types
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
    # Session management
    "SessionManager",
    "SessionState",
    "get_session_manager",
    # Adapters
    "LangGraphAdapter",
    "ToolAdapter",
]
