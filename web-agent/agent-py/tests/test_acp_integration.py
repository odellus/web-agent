#!/usr/bin/env python3
"""ACP Integration Test.

This test verifies that the ACP implementation works correctly with
the web-agent system for Zed editor integration.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from web_agent.ACP.protocol.types import (
    ACPTool,
    ACPMessage,
    InitializeParams,
    SessionParams,
    PromptParams,
)
from web_agent.ACP.protocol.methods import ACPMethods
from web_agent.ACP.adapters.langgraph_adapter import LangGraphAdapter
from web_agent.ACP.adapters.tool_adapter import ToolAdapter
from web_agent.ACP.utils.json_rpc import JSONRPCProcessor


class TestACPIntegration:
    """Test ACP integration components."""

    def __init__(self):
        self.methods = ACPMethods()
        self.tool_adapter = ToolAdapter()
        self.langgraph_adapter = LangGraphAdapter()
        self.json_rpc_processor = JSONRPCProcessor()

    async def test_initialization(self):
        """Test ACP initialization."""
        print("Testing ACP initialization...")

        # Test initialize method
        params = {
            "protocol_version": "0.4.0",
            "capabilities": {
                "prompt": {"image": False, "embedded_context": True},
                "fs": {"read_text_file": True, "write_text_file": True},
                "terminal": {"create": True, "resize": True},
            },
        }

        result = await self.methods.initialize(params)

        # Verify response structure
        assert "protocol_version" in result
        assert "capabilities" in result
        assert "server_info" in result
        assert result["protocol_version"] == "0.4.0"

        print("✓ Initialization test passed")

    async def test_session_creation(self):
        """Test session creation."""
        print("Testing session creation...")

        with tempfile.TemporaryDirectory() as temp_dir:
            params = {
                "working_directory": temp_dir,
                "metadata": {"test": True},
            }

            result = await self.methods.session_new(params)

            # Verify session structure
            assert "session_id" in result
            assert "capabilities" in result
            assert "available_models" in result
            assert "available_modes" in result

            session_id = result["session_id"]
            print(f"✓ Created session: {session_id}")

            return session_id

    async def test_tools_listing(self):
        """Test tools listing."""
        print("Testing tools listing...")

        result = await self.methods.tools_list({})

        # Verify tools structure
        assert "tools" in result
        tools = result["tools"]
        assert len(tools) > 0

        # Check for expected tools
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "bash_tool",
            "edit_tool",
            "sequential_thinking_tool",
            "task_done",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"

        print(f"✓ Found {len(tools)} tools: {tool_names}")

    async def test_tool_execution(self):
        """Test tool execution."""
        print("Testing tool execution...")

        # Test bash tool
        result = await self.methods.tools_call(
            {
                "name": "bash_tool",
                "arguments": {
                    "command": "echo 'Hello from ACP!'",
                    "working_directory": "/tmp",
                },
            }
        )

        # Verify tool result
        assert "content" in result
        assert "is_error" in result
        assert not result["is_error"]

        content = result["content"][0]["text"]
        assert "Hello from ACP!" in content

        print("✓ Tool execution test passed")

    async def test_json_rpc_processing(self):
        """Test JSON-RPC message processing."""
        print("Testing JSON-RPC processing...")

        # Register a test handler
        test_handler = AsyncMock(return_value={"test": "success"})
        self.json_rpc_processor.register_request_handler("test", test_handler)

        # Test valid request
        request = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"param": "value"},
            "id": 1,
        }

        response_str = await self.json_rpc_processor.process_message(
            json.dumps(request)
        )
        response = json.loads(response_str)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["test"] == "success"

        print("✓ JSON-RPC processing test passed")

    async def test_tool_adapter(self):
        """Test tool adapter functionality."""
        print("Testing tool adapter...")

        # List tools
        tools = await self.tool_adapter.list_tools()
        assert len(tools) > 0

        # Get tool info
        bash_tool_info = await self.tool_adapter.get_tool_info("bash_tool")
        assert bash_tool_info is not None
        assert bash_tool_info["name"] == "bash_tool"

        # Validate tool call
        validation = await self.tool_adapter.validate_tool_call(
            "bash_tool", {"command": "echo test"}
        )
        assert validation["valid"] is True

        # Validate invalid call
        validation = await self.tool_adapter.validate_tool_call(
            "bash_tool",
            {},  # Missing required 'command'
        )
        assert validation["valid"] is False

        print("✓ Tool adapter test passed")

    async def test_complete_workflow(self):
        """Test complete ACP workflow."""
        print("Testing complete workflow...")

        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Initialize
            init_result = await self.methods.initialize({})
            assert init_result["protocol_version"] == "0.4.0"

            # 2. Create session
            session_result = await self.methods.session_new(
                {
                    "working_directory": temp_dir,
                }
            )
            session_id = session_result["session_id"]

            # 3. List tools
            tools_result = await self.methods.tools_list({})
            assert len(tools_result["tools"]) > 0

            # 4. Execute tool
            tool_result = await self.methods.tools_call(
                {
                    "name": "bash_tool",
                    "arguments": {
                        "command": f"echo 'Working in {temp_dir}'",
                        "working_directory": temp_dir,
                    },
                    "session_id": session_id,
                }
            )
            assert not tool_result["is_error"]

            print("✓ Complete workflow test passed")

    async def run_all_tests(self):
        """Run all tests."""
        print("Starting ACP Integration Tests")
        print("=" * 50)

        try:
            await self.test_initialization()
            await self.test_tools_listing()
            await self.test_tool_adapter()
            await self.test_json_rpc_processing()
            await self.test_session_creation()
            await self.test_tool_execution()
            await self.test_complete_workflow()

            print("=" * 50)
            print("✅ All tests passed!")
            return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return False


async def main():
    """Main test runner."""
    test = TestACPIntegration()
    success = await test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
