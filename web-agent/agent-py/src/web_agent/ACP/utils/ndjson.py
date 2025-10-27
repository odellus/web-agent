"""NDJSON (Newline Delimited JSON) streaming utilities.

This module provides utilities for handling NDJSON streams, which are commonly
used in ACP communication for real-time, line-by-line JSON message exchange.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Union, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NDJSONMessage:
    """A single NDJSON message."""

    data: Dict[str, Any]
    line_number: int
    raw_line: str

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.data, separators=(",", ":"))


class NDJSONEncoder:
    """Encoder for NDJSON messages."""

    def __init__(self, ensure_ascii: bool = False, separators: tuple = (",", ":")):
        """Initialize the NDJSON encoder.

        Args:
            ensure_ascii: Whether to escape non-ASCII characters
            separators: Tuple of separators for compact JSON
        """
        self.ensure_ascii = ensure_ascii
        self.separators = separators

    def encode(self, data: Dict[str, Any]) -> str:
        """Encode data to NDJSON line.

        Args:
            data: Data to encode

        Returns:
            NDJSON line string
        """
        return (
            json.dumps(data, ensure_ascii=self.ensure_ascii, separators=self.separators)
            + "\n"
        )

    def encode_batch(self, messages: list[Dict[str, Any]]) -> str:
        """Encode multiple messages to NDJSON.

        Args:
            messages: List of messages to encode

        Returns:
            NDJSON string with multiple lines
        """
        lines = []
        for message in messages:
            lines.append(self.encode(message))
        return "".join(lines)


class NDJSONDecoder:
    """Decoder for NDJSON streams."""

    def __init__(self):
        """Initialize the NDJSON decoder."""
        self.buffer = ""
        self.line_number = 0

    def decode(self, data: str) -> list[NDJSONMessage]:
        """Decode NDJSON data into messages.

        Args:
            data: Raw NDJSON data

        Returns:
            List of decoded messages
        """
        self.buffer += data
        messages = []

        # Process complete lines
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self.line_number += 1

            line = line.strip()
            if not line:
                continue

            try:
                message_data = json.loads(line)
                message = NDJSONMessage(
                    data=message_data, line_number=self.line_number, raw_line=line
                )
                messages.append(message)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON on line {self.line_number}: {e}")
                # Continue processing other lines
                continue

        return messages

    def reset(self):
        """Reset the decoder state."""
        self.buffer = ""
        self.line_number = 0


class NDJSONStreamReader:
    """Async NDJSON stream reader."""

    def __init__(self, read_callback: Callable[[], str]):
        """Initialize the stream reader.

        Args:
            read_callback: Async function to read data
        """
        self.read_callback = read_callback
        self.decoder = NDJSONDecoder()

    async def read_message(self) -> Optional[NDJSONMessage]:
        """Read a single NDJSON message.

        Returns:
            NDJSON message or None if stream ended
        """
        while True:
            # Try to decode buffered data
            messages = self.decoder.decode("")
            if messages:
                return messages[0]

            # Read more data
            try:
                data = await self.read_callback()
                if not data:
                    return None  # Stream ended
            except Exception as e:
                logger.error(f"Error reading from stream: {e}")
                return None

            # Decode new data
            messages = self.decoder.decode(data)
            if messages:
                return messages[0]

    async def read_messages(self) -> AsyncGenerator[NDJSONMessage, None]:
        """Read all messages from the stream.

        Yields:
            NDJSON messages as they arrive
        """
        while True:
            message = await self.read_message()
            if message is None:
                break
            yield message

    def reset(self):
        """Reset the reader state."""
        self.decoder.reset()


class NDJSONStreamWriter:
    """Async NDJSON stream writer."""

    def __init__(self, write_callback: Callable[[str], None]):
        """Initialize the stream writer.

        Args:
            write_callback: Async function to write data
        """
        self.write_callback = write_callback
        self.encoder = NDJSONEncoder()

    async def write_message(self, data: Dict[str, Any]):
        """Write a single NDJSON message.

        Args:
            data: Data to write
        """
        line = self.encoder.encode(data)
        await self.write_callback(line)

    async def write_messages(self, messages: list[Dict[str, Any]]):
        """Write multiple NDJSON messages.

        Args:
            messages: List of messages to write
        """
        data = self.encoder.encode_batch(messages)
        await self.write_callback(data)

    async def write_notification(self, method: str, params: Optional[Dict] = None):
        """Write a JSON-RPC notification.

        Args:
            method: Method name
            params: Method parameters
        """
        notification = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        await self.write_message(notification)

    async def write_response(
        self, result: Dict[str, Any], request_id: Optional[Union[str, int]] = None
    ):
        """Write a JSON-RPC response.

        Args:
            result: Response result
            request_id: Request ID
        """
        response = {"jsonrpc": "2.0", "result": result}
        if request_id is not None:
            response["id"] = request_id
        await self.write_message(response)

    async def write_error(
        self,
        code: int,
        message: str,
        data: Optional[Dict] = None,
        request_id: Optional[Union[str, int]] = None,
    ):
        """Write a JSON-RPC error response.

        Args:
            code: Error code
            message: Error message
            data: Optional error data
            request_id: Request ID
        """
        error = {"code": code, "message": message}
        if data:
            error["data"] = data

        response = {"jsonrpc": "2.0", "error": error}
        if request_id is not None:
            response["id"] = request_id
        await self.write_message(response)


class NDJSONStream:
    """Bidirectional NDJSON stream."""

    def __init__(
        self, read_callback: Callable[[], str], write_callback: Callable[[str], None]
    ):
        """Initialize the bidirectional stream.

        Args:
            read_callback: Async function to read data
            write_callback: Async function to write data
        """
        self.reader = NDJSONStreamReader(read_callback)
        self.writer = NDJSONStreamWriter(write_callback)

    async def send(self, data: Dict[str, Any]):
        """Send data over the stream.

        Args:
            data: Data to send
        """
        await self.writer.write_message(data)

    async def receive(self) -> Optional[NDJSONMessage]:
        """Receive data from the stream.

        Returns:
            Received message or None if stream ended
        """
        return await self.reader.read_message()

    async def send_notification(self, method: str, params: Optional[Dict] = None):
        """Send a notification.

        Args:
            method: Method name
            params: Method parameters
        """
        await self.writer.write_notification(method, params)

    async def send_response(
        self, result: Dict[str, Any], request_id: Optional[Union[str, int]] = None
    ):
        """Send a response.

        Args:
            result: Response result
            request_id: Request ID
        """
        await self.writer.write_response(result, request_id)

    async def send_error(
        self,
        code: int,
        message: str,
        data: Optional[Dict] = None,
        request_id: Optional[Union[str, int]] = None,
    ):
        """Send an error response.

        Args:
            code: Error code
            message: Error message
            data: Optional error data
            request_id: Request ID
        """
        await self.writer.write_error(code, message, data, request_id)

    def reset(self):
        """Reset the stream state."""
        self.reader.reset()


async def create_stdio_stream() -> NDJSONStream:
    """Create an NDJSON stream for stdio.

    Returns:
        NDJSON stream configured for stdio
    """

    async def read_stdio() -> str:
        """Read from stdin."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input)

    async def write_stdio(data: str):
        """Write to stdout."""
        print(data, end="", flush=True)

    return NDJSONStream(read_stdio, write_stdio)


async def create_websocket_stream(websocket) -> NDJSONStream:
    """Create an NDJSON stream for WebSocket.

    Args:
        websocket: WebSocket connection

    Returns:
        NDJSON stream configured for WebSocket
    """

    async def read_websocket() -> str:
        """Read from WebSocket."""
        return await websocket.receive_text()

    async def write_websocket(data: str):
        """Write to WebSocket."""
        await websocket.send_text(data)

    return NDJSONStream(read_websocket, write_websocket)


def validate_ndjson_line(line: str) -> bool:
    """Validate if a line is valid NDJSON.

    Args:
        line: Line to validate

    Returns:
        True if valid NDJSON, False otherwise
    """
    line = line.strip()
    if not line:
        return False

    try:
        json.loads(line)
        return True
    except json.JSONDecodeError:
        return False


def parse_ndjson_chunk(data: str) -> list[Dict[str, Any]]:
    """Parse a chunk of NDJSON data.

    Args:
        data: NDJSON data chunk

    Returns:
        List of parsed JSON objects
    """
    decoder = NDJSONDecoder()
    messages = decoder.decode(data)
    return [msg.data for msg in messages]


def format_ndjson_message(data: Dict[str, Any]) -> str:
    """Format a dictionary as NDJSON.

    Args:
        data: Data to format

    Returns:
        NDJSON formatted string
    """
    encoder = NDJSONEncoder()
    return encoder.encode(data)
