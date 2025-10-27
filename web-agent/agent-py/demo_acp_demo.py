#!/usr/bin/env python3
"""ACP Demo Script.

This script demonstrates the complete ACP integration with web-agent,
showing how it can be used with Zed editor or other ACP-compatible clients.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_agent.ACP.client import ACPStdioClient


async def demo_basic_workflow():
    """Demonstrate basic ACP workflow."""
    print("🚀 ACP Integration Demo")
    print("=" * 50)

    # Create a temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Working in: {temp_dir}")

        # Initialize ACP client
        client = ACPStdioClient(working_directory=temp_dir)

        try:
            print("\n🔌 Connecting to ACP server...")
            await client.start()

            print("\n🛠️ Available tools:")
            tools = await client.list_tools()
            for tool in tools:
                print(f"  • {tool['name']}: {tool['description']}")

            print("\n📝 Testing bash tool...")
            result = await client.call_tool(
                "bash_tool",
                {
                    "command": "echo 'Hello from ACP!' && pwd",
                },
            )
            if not result.get("is_error"):
                content = result["content"][0]["text"]
                print(f"✅ Bash output: {content.strip()}")

            print("\n📄 Testing file creation...")
            result = await client.call_tool(
                "edit_tool",
                {
                    "command": "create",
                    "file_path": "test.txt",
                    "text": "Hello from ACP integration!\nThis is a test file created via ACP.",
                },
            )
            if not result.get("is_error"):
                print("✅ File created successfully")

            print("\n👀 Testing file viewing...")
            result = await client.call_tool(
                "edit_tool",
                {
                    "command": "view",
                    "file_path": "test.txt",
                },
            )
            if not result.get("is_error"):
                content = result["content"][0]["text"]
                print(f"✅ File content:\n{content}")

            print("\n🤖 Testing agent interaction...")
            response = await client.send_message(
                "List the files in the current directory and tell me what you see."
            )
            print(f"✅ Agent response: {response}")

            print("\n🧠 Testing sequential thinking...")
            result = await client.call_tool(
                "sequential_thinking_tool",
                {
                    "thought": "I need to analyze what we've accomplished in this demo.",
                    "thought_number": 1,
                    "total_thoughts": 3,
                    "next_thought_needed": True,
                },
            )
            if not result.get("is_error"):
                print("✅ Sequential thinking initiated")

            print("\n🎯 Testing task completion...")
            result = await client.call_tool("task_done", {})
            if not result.get("is_error"):
                print("✅ Task completed successfully")

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

        finally:
            await client.stop()

    print("\n🎉 Demo completed successfully!")
    return True


async def demo_zed_integration():
    """Demonstrate Zed editor integration setup."""
    print("\n🔧 Zed Editor Integration Setup")
    print("=" * 50)

    config = {
        "agents": {
            "web-agent": {
                "command": ["python", "-m", "web_agent.ACP"],
                "args": ["--transport", "stdio", "--working-dir", "{workspace}"],
                "transport": "stdio",
                "capabilities": {
                    "fs": {"readTextFile": True, "writeTextFile": True},
                    "terminal": True,
                },
            }
        }
    }

    print("📋 Add this to your Zed settings.json:")
    print(json.dumps(config, indent=2))

    print("\n📝 Usage in Zed:")
    print("1. Open a project folder")
    print("2. Open command palette (Cmd+Shift+P on Mac, Ctrl+Shift+P on Linux/Windows)")
    print("3. Type 'Agent: web-agent' to start the agent")
    print("4. Use the agent panel to interact with the web-agent")

    print("\n🌐 WebSocket Development Mode:")
    print("For development and testing, you can run:")
    print("  python -m web_agent.ACP --transport websocket --port 8095")
    print("Then connect to ws://localhost:8095/ws")


async def demo_capabilities():
    """Demonstrate ACP capabilities."""
    print("\n⚡ ACP Capabilities Demo")
    print("=" * 50)

    capabilities = {
        "prompt": {
            "image": False,
            "embedded_context": True,
            "description": "Text-based prompts with context support",
        },
        "fs": {
            "read_text_file": True,
            "write_text_file": True,
            "list_directory": False,
            "create_directory": False,
            "delete_file": False,
            "description": "File reading and writing operations",
        },
        "terminal": {
            "create": True,
            "resize": True,
            "send_input": True,
            "read_output": True,
            "description": "Full terminal command execution",
        },
    }

    print("🔋 Supported Capabilities:")
    for category, caps in capabilities.items():
        print(f"\n{category.upper()}:")
        for cap, enabled in caps.items():
            if cap != "description":
                status = "✅" if enabled else "❌"
                print(f"  {status} {cap}")
            else:
                print(f"  📝 {caps['description']}")

    print("\n🛠️ Available Tools:")
    tools = [
        {
            "name": "bash_tool",
            "description": "Execute shell commands with working directory support",
            "example": 'bash_tool({"command": "ls -la"})',
        },
        {
            "name": "edit_tool",
            "description": "File operations (view, create, edit)",
            "example": 'edit_tool({"command": "view", "file_path": "README.md"})',
        },
        {
            "name": "sequential_thinking_tool",
            "description": "Structured problem-solving and reasoning",
            "example": 'sequential_thinking_tool({"thought": "I need to analyze this problem...", "thought_number": 1, "total_thoughts": 5})',
        },
        {
            "name": "task_done",
            "description": "Signal task completion with verification",
            "example": "task_done({})",
        },
    ]

    for tool in tools:
        print(f"\n  🔧 {tool['name']}")
        print(f"     📝 {tool['description']}")
        print(f"     💡 Example: {tool['example']}")


async def main():
    """Main demo function."""
    print("🤖 Web-Agent ACP Integration Demo")
    print("=" * 60)
    print("This demo shows how the Agent Client Protocol (ACP)")
    print("enables web-agent integration with Zed editor and other tools.")
    print()

    try:
        # Run basic workflow demo
        success = await demo_basic_workflow()
        if not success:
            print("❌ Basic workflow demo failed")
            return

        # Show Zed integration setup
        await demo_zed_integration()

        # Show capabilities
        await demo_capabilities()

        print("\n" + "=" * 60)
        print("🎊 All demos completed successfully!")
        print("\n📚 Next Steps:")
        print("1. Configure Zed with the settings shown above")
        print("2. Test with your own projects")
        print("3. Explore the agent capabilities")
        print("4. Check the documentation for advanced features")

    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
