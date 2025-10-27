#!/usr/bin/env python3
"""Agent Client Protocol (ACP) Client for stdio transport.

This client provides a stdio-based interface for ACP communication,
suitable for integration with Zed editor's stdio transport.
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .utils.ndjson import NDJSONStream, create_stdio_stream
from .utils.json_rpc import JSONRPCProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ACPClient:
    """Agent Client Protocol client using stdio transport."""

    def __init__(self):
        """Initialize the ACP client."""
        self.stream: Optional[NDJSONStream] = None
        self.json_rpc_processor = JSONRPCProcessor()
        self.request_id = 0
        self.pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._running = False

    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    async def connect(self):
        """Connect to the ACP server."""
        if self.stream:
            return  # Already connected

        self.stream = await create_stdio_stream()
        self._running = True

        # Start message processing task
        asyncio.create_task(self._process_messages())

        logger.info("Connected to ACP server")

    async def disconnect(self):
        """Disconnect from the ACP server."""
        self._running = False
        if self.stream:
            # Cancel any pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.cancel()
            self.pending_requests.clear()

        logger.info("Disconnected from ACP server")

    async def _process_messages(self):
        """Process incoming messages."""
        if not self.stream:
            return

        try:
            async for message in self.stream.reader.read_messages():
                await self._handle_message(message)
        except Exception as e:
            logger.error(f"Error processing messages: {e}")

    async def _handle_message(self, message):
        """Handle an incoming message."""
        try:
            # Check if this is a response to a pending request
            if hasattr(message, "data") and "id" in message.data:
                request_id = message.data["id"]
                if request_id in self.pending_requests:
                    future = self.pending_requests.pop(request_id)
                    if not future.done():
                        if "error" in message.data:
                            future.set_exception(
                                Exception(f"RPC Error: {message.data['error']}")
                            )
                        else:
                            future.set_result(message.data.get("result", {}))
                    return

            # Handle notifications
            if hasattr(message, "data") and "method" in message.data:
                method = message.data["method"]
                params = message.data.get("params", {})
                logger.info(f"Received notification: {method} with params: {params}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def send_request(
        self, method: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for response."""
        if not self.stream:
            raise RuntimeError("Not connected to ACP server")

        request_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id,
        }

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            # Send request
            await self.stream.send(request)
            logger.info(f"Sent request: {method} (id: {request_id})")

            # Wait for response
            result = await asyncio.wait_for(future, timeout=30.0)
            return result

        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise Exception(f"Request timeout for {method}")
        except Exception as e:
            self.pending_requests.pop(request_id, None)
            raise e

    async def initialize(
        self, working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize the ACP connection."""
        params = {}
        if working_directory:
            params["workingDirectory"] = working_directory

        return await self.send_request("initialize", params)

    async def session_new(
        self,
        working_directory: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new session."""
        params = {}
        if working_directory:
            params["working_directory"] = working_directory
        if metadata:
            params["metadata"] = metadata

        return await self.send_request("session/new", params)

    async def session_prompt(
        self,
        session_id: str,
        message: str,
        mode: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a prompt to a session."""
        params = {
            "session_id": session_id,
            "message": message,
        }
        if mode:
            params["mode"] = mode
        if model:
            params["model"] = model

        return await self.send_request("session/prompt", params)

    async def session_set_mode(self, session_id: str, mode: str) -> Dict[str, Any]:
        """Set the mode for a session."""
        params = {
            "session_id": session_id,
            "mode": mode,
        }
        return await self.send_request("session/set_mode", params)

    async def session_set_model(self, session_id: str, model: str) -> Dict[str, Any]:
        """Set the model for a session."""
        params = {
            "session_id": session_id,
            "model": model,
        }
        return await self.send_request("session/set_model", params)

    async def session_cancel(self, session_id: str) -> Dict[str, Any]:
        """Cancel operations in a session."""
        params = {"session_id": session_id}
        return await self.send_request("session/cancel", params)

    async def tools_list(self) -> Dict[str, Any]:
        """List available tools."""
        return await self.send_request("tools/list")

    async def tools_call(
        self, name: str, arguments: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Call a specific tool."""
        params = {
            "name": name,
            "arguments": arguments,
        }
        if session_id:
            params["session_id"] = session_id

        return await self.send_request("tools/call", params)


class ACPStdioClient:
    """High-level stdio client for Zed integration."""

    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the stdio client.

        Args:
            working_directory: Working directory for the agent
        """
        self.client = ACPClient()
        self.working_directory = working_directory
        self.session_id: Optional[str] = None

    async def start(self):
        """Start the client and initialize connection."""
        await self.client.connect()

        # Initialize ACP connection
        init_result = await self.client.initialize(self.working_directory)
        logger.info(f"Initialized ACP: {init_result}")

        # Create session
        session_result = await self.client.session_new(
            working_directory=self.working_directory
        )
        self.session_id = session_result["session_id"]
        logger.info(f"Created session: {self.session_id}")

    async def stop(self):
        """Stop the client."""
        await self.client.disconnect()

    async def send_message(self, message: str) -> str:
        """Send a message and get response.

        Args:
            message: Message to send

        Returns:
            Response text
        """
        if not self.session_id:
            raise RuntimeError("No active session")

        result = await self.client.session_prompt(self.session_id, message)
        message_obj = result.get("message", {})
        content = message_obj.get("content", [])

        # Extract text from content
        response_text = ""
        for item in content:
            if item.get("type") == "text":
                response_text += item.get("text", "")

        return response_text

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        return await self.client.tools_call(name, arguments, self.session_id)

    async def list_tools(self) -> list[Dict[str, Any]]:
        """List available tools.

        Returns:
            List of tool definitions
        """
        result = await self.client.tools_list()
        return result.get("tools", [])


async def interactive_mode():
    """Run the client in interactive mode."""
    client = ACPStdioClient()

    try:
        await client.start()

        print("ACP Client Interactive Mode")
        print("Type 'quit' to exit, 'tools' to list tools")
        print()

        while True:
            try:
                # Read user input
                user_input = input("You: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                elif user_input.lower() == "tools":
                    tools = await client.list_tools()
                    print("Available tools:")
                    for tool in tools:
                        print(f"  - {tool['name']}: {tool['description']}")
                    print()
                    continue
                elif not user_input:
                    continue

                # Send message and get response
                print("Agent: ", end="", flush=True)
                response = await client.send_message(user_input)
                print(response)
                print()

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                print()

    finally:
        await client.stop()


async def main():
    """Main client function."""
    parser = argparse.ArgumentParser(description="ACP Client for web-agent")
    parser.add_argument(
        "--mode",
        choices=["interactive", "test", "stdio"],
        default="stdio",
        help="Client mode to run in",
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default=".",
        help="Working directory for the agent",
    )
    parser.add_argument(
        "--test-message",
        type=str,
        help="Test message to send (in test mode)",
    )

    args = parser.parse_args()

    # Change to working directory
    if args.working_dir:
        work_dir = Path(args.working_dir).resolve()
        if work_dir.exists():
            import os

            os.chdir(work_dir)
            logger.info(f"Changed working directory to {work_dir}")
        else:
            logger.error(f"Working directory does not exist: {work_dir}")
            sys.exit(1)

    if args.mode == "interactive":
        await interactive_mode()

    elif args.mode == "test":
        if not args.test_message:
            print("Error: --test-message required in test mode")
            sys.exit(1)

        client = ACPStdioClient(args.working_dir)
        try:
            await client.start()
            response = await client.send_message(args.test_message)
            print(f"Response: {response}")
        finally:
            await client.stop()

    elif args.mode == "stdio":
        # Run as stdio server (for Zed integration)
        client = ACPStdioClient(args.working_dir)
        await client.start()

        try:
            # Read commands from stdin and execute them
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse as JSON command
                    command = json.loads(line)
                    cmd_type = command.get("type")

                    if cmd_type == "message":
                        message = command.get("text", "")
                        response = await client.send_message(message)
                        print(json.dumps({"type": "response", "text": response}))

                    elif cmd_type == "tool_call":
                        name = command.get("name")
                        arguments = command.get("arguments", {})
                        result = await client.call_tool(name, arguments)
                        print(json.dumps({"type": "tool_result", "result": result}))

                    elif cmd_type == "quit":
                        break

                    else:
                        print(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": f"Unknown command: {cmd_type}",
                                }
                            )
                        )

                except json.JSONDecodeError:
                    print(
                        json.dumps({"type": "error", "message": "Invalid JSON command"})
                    )
                except Exception as e:
                    print(json.dumps({"type": "error", "message": str(e)}))

        finally:
            await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
