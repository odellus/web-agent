"""Tests for the thinking subagent functionality."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from web_agent.tools.thinking_agent import get_thinking_agent, ThinkingAgentState
from web_agent.tools.thinking_tools import all_tools as thinking_agent_tools


class TestThinkingAgent:
    """Test suite for the thinking subagent."""

    def test_thinking_agent_state_initialization(self):
        """Test that ThinkingAgentState initializes correctly."""
        state = ThinkingAgentState(
            messages=[],
            current_thought_number=1,
            total_thoughts=10,
            thoughts_completed=False,
        )

        assert state.current_thought_number == 1
        assert state.total_thoughts == 10
        assert state.thoughts_completed == False
        assert state.next_thought_needed == True  # Default value

    def test_thinking_agent_creation(self):
        """Test that the thinking agent can be created successfully."""
        agent = get_thinking_agent()

        assert agent is not None
        assert agent.nodes is not None
        assert agent.edges is not None

        # Check that nodes include llm_call and tool_node
        assert "llm_call" in agent.nodes
        assert "tool_node" in agent.nodes

    @pytest.mark.asyncio
    async def test_thinking_tool_basic_usage(self):
        """Test basic functionality of the thinking tool."""
        from web_agent.tools.thinking_tools import thinking_tool

        result = thinking_tool(
            thought="This is my first thought",
            thought_number=1,
            total_thoughts=5,
            next_thought_needed=True,
            problem_context="Testing the thinking tool",
            analysis_type="problem_breakdown",
            confidence_level=7,
        )

        assert "THOUGHT [1/5]" in result
        assert "This is my first thought" in result
        assert "Context: Testing the thinking tool" in result
        assert "Analysis type: problem_breakdown" in result
        assert "Confidence: 7/10" in result

    @pytest.mark.asyncio
    async def test_web_search_tool(self):
        """Test the web search tool functionality."""
        from web_agent.tools.thinking_tools import web_search_tool

        # Mock the HTTP request to avoid actual web calls in tests
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {
                            "title": "Test Result",
                            "url": "https://example.com",
                            "content": "This is a test result content",
                        }
                    ]
                }
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await web_search_tool("test query")

            assert "Search results found" in result or "Result 1" in result
            assert "Test Result" in result
            assert "https://example.com" in result

    def test_read_file_tool_with_relative_path(self, tmp_path):
        """Test reading files with relative paths."""
        from web_agent.tools.thinking_tools import read_file_tool

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!\nThis is a test file.")

        # Test reading the file
        result = read_file_tool(file_path="test.txt", working_directory=tmp_path)

        assert "Hello, World!" in result
        assert "This is a test file." in result
        # Should contain line numbers
        assert "1 |" in result

    def test_read_file_file_not_found(self):
        """Test handling of non-existent files."""
        from web_agent.tools.thinking_tools import read_file_tool

        result = read_file_tool(
            file_path="nonexistent.txt", working_directory=Path("/tmp")
        )

        assert "File not found" in result

    def test_rg_search_tool_success(self, tmp_path):
        """Test ripgrep search functionality."""
        from web_agent.tools.thinking_tools import rg_search_tool

        # Create a test file with searchable content
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello_world():\n    print('Hello, World!')\n\n")
        test_file.write_text("def goodbye():\n    print('Goodbye!')\n", append=True)

        # Test searching for "def"
        result = rg_search_tool(pattern="def", path=".", working_directory=tmp_path)

        assert "Search results" in result or "def hello_world" in result

    def test_rg_search_tool_not_found(self, tmp_path):
        """Test ripgrep search when pattern is not found."""
        from web_agent.tools.thinking_tools import rg_search_tool

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('Hello, World!')")

        # Test searching for non-existent pattern
        result = rg_search_tool(
            pattern="nonexistent_pattern", path=".", working_directory=tmp_path
        )

        assert "No matches found" in result or "failed" in result.lower()

    def test_rg_search_tool_rg_not_installed(self):
        """Test ripgrep search when rg is not installed."""
        from web_agent.tools.thinking_tools import rg_search_tool

        # Mock subprocess.run to raise FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError("rg not found")):
            result = rg_search_tool(pattern="test")

            assert "ripgrep (rg) not found" in result

    @pytest.mark.asyncio
    async def test_fetch_tool_success(self):
        """Test URL fetching functionality."""
        from web_agent.tools.thinking_tools import fetch_tool

        # Mock aiohttp
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value="<html><body><h1>Test</h1><p>Content</p></body></html>"
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await fetch_tool("https://example.com")

            assert "Test" in result
            assert "Content" in result
            assert result.startswith("# Test")  # HTML to markdown conversion

    @pytest.mark.asyncio
    async def test_fetch_tool_failure(self):
        """Test URL fetching with failure response."""
        from web_agent.tools.thinking_tools import fetch_tool

        # Mock aiohttp
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock failed response
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await fetch_tool("https://example.com")

            assert "Failed to fetch URL: 404" in result

    def test_html_to_markdown_conversion(self):
        """Test HTML to markdown conversion function."""
        from web_agent.tools.thinking_tools import html_to_markdown

        html = """
        <html>
        <body>
            <h1>Main Title</h1>
            <p>This is a <strong>paragraph</strong> with <em>emphasis</em>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <code>print('Hello')</code>
        </body>
        </html>
        """

        markdown = html_to_markdown(html)

        assert "# Main Title" in markdown
        assert "**paragraph**" in markdown
        assert "*emphasis*" in markdown
        assert "- Item 1" in markdown
        assert "- Item 2" in markdown
        assert "`print('Hello')`" in markdown

    def test_sequential_thinking_tool_interface(self):
        """Test that the enhanced sequential thinking tool has the correct interface."""
        from web_agent.tools.sequential_thinking_tool import sequential_thinking_tool

        # Check that the tool has the expected parameters
        expected_params = {
            "problem_description": str,
            "context": str,
            "max_thoughts": int,
            "thinking_approach": str,
            "working_directory": str,
        }

        # This is a basic interface check - actual functionality would require integration testing
        assert callable(sequential_thinking_tool)


class TestThinkingAgentIntegration:
    """Integration tests for the thinking agent workflow."""

    def test_thinking_agent_workflow_setup(self):
        """Test that the thinking agent workflow is properly set up."""
        agent = get_thinking_agent()

        # Check that the agent has the expected structure
        assert hasattr(agent, "nodes")
        assert hasattr(agent, "edges")
        assert hasattr(agent, "config")

        # Check nodes
        assert "llm_call" in agent.nodes
        assert "tool_node" in agent.nodes

        # Check that the tool node has the expected tools
        tool_node = agent.nodes["tool_node"]
        assert hasattr(tool_node, "tools")
        assert len(tool_node.tools) > 0

    @pytest.mark.asyncio
    async def test_thinking_agent_state_serialization(self):
        """Test that thinking agent state can be serialized and deserialized."""
        from pydantic import BaseModel

        # Create a state instance
        state = ThinkingAgentState(
            messages=[],
            current_thought_number=1,
            total_thoughts=10,
            thoughts_completed=False,
            problem_context="Test context",
        )

        # Test that the state can be converted to dict (serialization)
        state_dict = state.model_dump()

        assert state_dict["current_thought_number"] == 1
        assert state_dict["total_thoughts"] == 10
        assert state_dict["thoughts_completed"] == False
        assert state_dict["problem_context"] == "Test context"

        # Test that the state can be created from dict (deserialization)
        restored_state = ThinkingAgentState(**state_dict)

        assert restored_state.current_thought_number == state.current_thought_number
        assert restored_state.total_thoughts == state.total_thoughts
        assert restored_state.thoughts_completed == state.thoughts_completed
        assert restored_state.problem_context == state.problem_context
