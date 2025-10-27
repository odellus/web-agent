"""Utilities for ACP implementation.

This package contains utility modules that support the ACP implementation,
including JSON-RPC processing and NDJSON streaming.

Modules:
- json_rpc: JSON-RPC 2.0 protocol utilities
- ndjson: NDJSON streaming utilities
"""

from .json_rpc import (
    JSONRPCProcessor,
    create_json_rpc_error,
    create_json_rpc_response,
    create_json_rpc_notification,
    is_json_rpc_request,
    is_json_rpc_notification,
)
from .ndjson import (
    NDJSONEncoder,
    NDJSONDecoder,
    NDJSONStreamReader,
    NDJSONStreamWriter,
    NDJSONStream,
    create_stdio_stream,
    create_websocket_stream,
    validate_ndjson_line,
    parse_ndjson_chunk,
    format_ndjson_message,
)

__all__ = [
    # JSON-RPC utilities
    "JSONRPCProcessor",
    "create_json_rpc_error",
    "create_json_rpc_response",
    "create_json_rpc_notification",
    "is_json_rpc_request",
    "is_json_rpc_notification",
    # NDJSON utilities
    "NDJSONEncoder",
    "NDJSONDecoder",
    "NDJSONStreamReader",
    "NDJSONStreamWriter",
    "NDJSONStream",
    "create_stdio_stream",
    "create_websocket_stream",
    "validate_ndjson_line",
    "parse_ndjson_chunk",
    "format_ndjson_message",
]
