"""Agent Client Protocol (ACP) streaming utilities.

This module provides utilities for handling streaming communication
in ACP, including NDJSON formatting and message framing.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamMessage:
    """A streaming message wrapper."""

    data: Dict[str, Any]
    message_id: Optional[str] = None
    timestamp: Optional[float] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.data, separators=(",", ":"))


class NDJSONStreamer:
    """NDJSON streamer for ACP communication."""

    def __init__(self, write_callback):
        """Initialize the NDJSON streamer.

        Args:
            write_callback: Async function to write data
        """
        self.write_callback = write_callback
        self._closed = False

    async def write(self, data: Dict[str, Any], message_id: Optional[str] = None):
        """Write a JSON object to the stream.

        Args:
            data: Data to write
            message_id: Optional message ID
        """
        if self._closed:
            raise RuntimeError("Stream is closed")

        message = StreamMessage(data=data, message_id=message_id)
        await self.write_callback(message.to_json() + "\n")

    async def write_notification(self, method: str, params: Optional[Dict] = None):
        """Write a JSON-RPC notification.

        Args:
            method: Method name
            params: Method parameters
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        await self.write(notification)

    async def write_response(
        self, result: Dict[str, Any], request_id: Optional[str] = None
    ):
        """Write a JSON-RPC response.

        Args:
            result: Response result
            request_id: Request ID
        """
        response = {
            "jsonrpc": "2.0",
            "result": result,
        }
        if request_id:
            response["id"] = request_id
        await self.write(response)

    async def write_error(
        self,
        code: int,
        message: str,
        data: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ):
        """Write a JSON-RPC error response.

        Args:
            code: Error code
            message: Error message
            data: Optional error data
            request_id: Request ID
        """
        error = {
            "code": code,
            "message": message,
        }
        if data:
            error["data"] = data

        response = {
            "jsonrpc": "2.0",
            "error": error,
        }
        if request_id:
            response["id"] = request_id
        await self.write(response)

    async def close(self):
        """Close the stream."""
        self._closed = True


class StreamParser:
    """Parser for NDJSON streams."""

    def __init__(self):
        """Initialize the stream parser."""
        self.buffer = ""

    async def parse(self, data: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Parse incoming data and yield JSON objects.

        Args:
            data: Incoming data string

        Yields:
            Parsed JSON objects
        """
        self.buffer += data

        # Process complete lines
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()

            if not line:
                continue

            try:
                obj = json.loads(line)
                yield obj
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in stream: {e}")
                # Continue processing other lines
                continue

    def reset(self):
        """Reset the parser buffer."""
        self.buffer = ""


class StreamingSession:
    """Manages a streaming ACP session."""

    def __init__(self, streamer: NDJSONStreamer, session_id: str):
        """Initialize the streaming session.

        Args:
            streamer: NDJSON streamer instance
            session_id: Session identifier
        """
        self.streamer = streamer
        self.session_id = session_id
        self.active = True
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def send_update(self, update_type: str, data: Dict[str, Any]):
        """Send a session update.

        Args:
            update_type: Type of update
            data: Update data
        """
        if not self.active:
            return

        await self.streamer.write_notification(
            "session/update",
            {"session_id": self.session_id, "type": update_type, **data},
        )

    async def send_message_update(self, message: Dict[str, Any]):
        """Send a message update.

        Args:
            message: Message data
        """
        await self.send_update("message", {"message": message})

    async def send_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Send a tool call update.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
        """
        await self.send_update(
            "tool_call", {"tool_call": {"name": tool_name, "arguments": arguments}}
        )

    async def send_tool_result(self, result: Dict[str, Any]):
        """Send a tool result update.

        Args:
            result: Tool result
        """
        await self.send_update("tool_result", {"tool_result": result})

    async def send_error(self, error: str):
        """Send an error update.

        Args:
            error: Error message
        """
        await self.send_update("error", {"error": error})

    async def complete(self, final_result: Dict[str, Any]):
        """Send completion update.

        Args:
            final_result: Final result data
        """
        await self.send_update("complete", final_result)
        self.active = False

    async def cancel(self):
        """Cancel the session."""
        await self.send_update("cancelled", {})
        self.active = False


class StreamBuffer:
    """Buffer for collecting streaming data."""

    def __init__(self):
        """Initialize the stream buffer."""
        self.chunks = []
        self.complete = False
        self.error = None

    async def add_chunk(self, chunk: Any):
        """Add a chunk to the buffer.

        Args:
            chunk: Chunk data
        """
        self.chunks.append(chunk)

    async def finalize(self):
        """Mark the buffer as complete."""
        self.complete = True

    async def set_error(self, error: str):
        """Set an error on the buffer.

        Args:
            error: Error message
        """
        self.error = error
        self.complete = True

    def get_content(self) -> str:
        """Get the concatenated content.

        Returns:
            Concatenated string content
        """
        return "".join(str(chunk) for chunk in self.chunks)

    def is_complete(self) -> bool:
        """Check if the buffer is complete.

        Returns:
            True if complete, False otherwise
        """
        return self.complete

    def has_error(self) -> bool:
        """Check if the buffer has an error.

        Returns:
            True if has error, False otherwise
        """
        return self.error is not None


async def create_stdio_streamer() -> NDJSONStreamer:
    """Create an NDJSON streamer for stdio.

    Returns:
        NDJSON streamer instance
    """

    async def write_stdout(data: str):
        print(data, flush=True)

    return NDJSONStreamer(write_stdout)


async def create_websocket_streamer(websocket) -> NDJSONStreamer:
    """Create an NDJSON streamer for WebSocket.

    Args:
        websocket: WebSocket connection

    Returns:
        NDJSON streamer instance
    """

    async def write_websocket(data: str):
        await websocket.send_text(data)

    return NDJSONStreamer(write_websocket)
