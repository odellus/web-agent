#!/usr/bin/env python3
"""Main entry point for the ACP module.

This module provides the main entry point for running the ACP server
in different modes (WebSocket or stdio) for integration with Zed editor.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .server import ACPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Agent Client Protocol (ACP) Server for web-agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as WebSocket server (for development/testing)
  python -m web_agent.ACP --transport websocket --port 8095

  # Run as stdio server (for Zed integration)
  python -m web_agent.ACP --transport stdio --working-dir /path/to/project

  # Configure in Zed settings:
  {
    "agents": {
      "web-agent": {
        "command": ["python", "-m", "web_agent.ACP"],
        "args": ["--transport", "stdio", "--working-dir", "{workspace}"]
      }
    }
  }
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["websocket", "stdio"],
        default="websocket",
        help="Transport protocol to use (default: websocket)",
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address for WebSocket server (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8095,
        help="Port for WebSocket server (default: 8095)",
    )

    parser.add_argument(
        "--working-dir",
        type=str,
        default=".",
        help="Working directory for the agent (default: current directory)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--session-timeout",
        type=int,
        default=3600,
        help="Session timeout in seconds (default: 3600)",
    )

    parser.add_argument(
        "--max-sessions",
        type=int,
        default=100,
        help="Maximum concurrent sessions (default: 100)",
    )

    return parser


async def run_websocket_server(args):
    """Run the WebSocket server."""
    from .server import run_websocket_server

    logger.info(f"Starting ACP WebSocket server on {args.host}:{args.port}")
    logger.info(f"Working directory: {Path(args.working_dir).resolve()}")
    logger.info(f"WebSocket endpoint: ws://{args.host}:{args.port}/ws")

    try:
        await run_websocket_server(args.host, args.port)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"WebSocket server error: {e}")
        sys.exit(1)


async def run_stdio_server(args):
    """Run the stdio server."""
    from .server import run_stdio_server

    logger.info(f"Starting ACP stdio server")
    logger.info(f"Working directory: {Path(args.working_dir).resolve()}")

    try:
        await run_stdio_server()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Stdio server error: {e}")
        sys.exit(1)


def validate_working_directory(working_dir: str) -> Path:
    """Validate and return the working directory path."""
    work_dir = Path(working_dir).resolve()

    if not work_dir.exists():
        logger.error(f"Working directory does not exist: {work_dir}")
        sys.exit(1)

    if not work_dir.is_dir():
        logger.error(f"Working path is not a directory: {work_dir}")
        sys.exit(1)

    return work_dir


def setup_logging(level: str):
    """Setup logging configuration."""
    logging.getLogger().setLevel(getattr(logging, level.upper()))

    # Reduce noise from some libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


async def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Validate and change to working directory
    work_dir = validate_working_directory(args.working_dir)
    import os

    os.chdir(work_dir)

    logger.info(f"ACP Server starting with transport: {args.transport}")
    logger.info(f"Working directory: {work_dir}")
    logger.info(f"Session timeout: {args.session_timeout}s")
    logger.info(f"Max sessions: {args.max_sessions}")

    # Run the appropriate server
    if args.transport == "websocket":
        await run_websocket_server(args)
    else:
        await run_stdio_server(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("ACP server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
