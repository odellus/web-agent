#!/usr/bin/env python3
"""Agent Client Protocol (ACP) Server for Zed integration.

This server implements the ACP protocol to connect the web-agent to Zed editor.
It provides a JSON-RPC 2.0 interface for tool discovery, execution, and messaging.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

from .protocol.methods import ACPMethods
from .protocol.sessions import initialize_session_manager
from .protocol.streaming import NDJSONStreamer, StreamParser
from .utils.json_rpc import JSONRPCProcessor
from web_agent.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ACPServer:
    """Agent Client Protocol Server."""

    def __init__(self):
        """Initialize the ACP server."""
        self.methods = ACPMethods()
        self.json_rpc_processor = JSONRPCProcessor()
        self.session_manager = None
        self._initialized = False

    async def initialize(self):
        """Initialize the server components."""
        if self._initialized:
            return

        try:
            # Initialize session manager
            self.session_manager = await initialize_session_manager()

            # Register JSON-RPC handlers
            self._register_handlers()

            self._initialized = True
            logger.info("ACP server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ACP server: {e}")
            raise

    def _register_handlers(self):
        """Register JSON-RPC method handlers."""
        # Register request handlers
        for method_name in [
            "initialize",
            "session/new",
            "session/prompt",
            "session/set_mode",
            "session/set_model",
            "session/cancel",
            "tools/list",
            "tools/call",
        ]:
            handler = self.methods.get_method_handler(method_name)
            if handler:
                self.json_rpc_processor.register_request_handler(method_name, handler)

    async def handle_websocket_connection(self, websocket: WebSocket):
        """Handle a WebSocket connection."""
        await websocket.accept()
        logger.info("ACP WebSocket connection established")

        # Create streamer and parser
        streamer = NDJSONStreamer(lambda data: websocket.send_text(data))
        parser = StreamParser()

        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                logger.debug(f"Received WebSocket data: {data}")

                # Parse and process messages
                async for message_data in parser.parse(data):
                    response = await self.json_rpc_processor.process_message(
                        json.dumps(message_data)
                    )
                    if response:
                        await streamer.write(json.loads(response))

        except WebSocketDisconnect:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            try:
                await streamer.write_error(
                    code=-32603,
                    message=f"Server error: {str(e)}",
                )
            except:
                pass  # Connection might already be closed

    async def handle_stdio_connection(self):
        """Handle stdio-based connection."""
        logger.info("Starting ACP stdio server")

        try:
            while True:
                # Read from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break  # EOF

                line = line.strip()
                if not line:
                    continue

                # Process message directly
                response = await self.json_rpc_processor.process_message(line)
                if response:
                    print(response, flush=True)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Stdio error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Server error: {str(e)}",
                },
            }
            print(json.dumps(error_response), flush=True)

    async def shutdown(self):
        """Shutdown the server."""
        if self.session_manager:
            await self.session_manager.stop()
        logger.info("ACP server shutdown complete")


# FastAPI app for WebSocket mode
app = FastAPI(title="Web Agent ACP Server", version="0.1.0")

# Global server instance
acp_server = ACPServer()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for ACP communication."""
    if not acp_server._initialized:
        await acp_server.initialize()
    await acp_server.handle_websocket_connection(websocket)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "web-agent-ACP",
        "description": "Agent Client Protocol server for Zed integration",
        "version": "0.1.0",
        "endpoints": {
            "websocket": "/ws",
            "health": "/health",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "web-agent-ACP",
        "initialized": acp_server._initialized,
    }


async def run_websocket_server(host: str = "0.0.0.0", port: int = 8095):
    """Run the WebSocket server."""
    if not acp_server._initialized:
        await acp_server.initialize()

    logger.info(f"Starting ACP WebSocket server on {host}:{port}")
    logger.info("WebSocket endpoint: ws://localhost:{port}/ws")

    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)
    await server.serve()


async def run_stdio_server():
    """Run the stdio server."""
    if not acp_server._initialized:
        await acp_server.initialize()

    await acp_server.handle_stdio_connection()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="ACP Server for web-agent")
    parser.add_argument(
        "--transport",
        choices=["websocket", "stdio"],
        default="websocket",
        help="Transport protocol to use",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for WebSocket server")
    parser.add_argument(
        "--port", type=int, default=8095, help="Port for WebSocket server"
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default=".",
        help="Working directory for the agent",
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

    # Run the appropriate server
    if args.transport == "websocket":
        asyncio.run(run_websocket_server(args.host, args.port))
    else:
        asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
