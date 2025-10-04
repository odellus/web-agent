"""Basic tests for trae-web agent functionality."""

from langchain_core.messages import HumanMessage

from trae_web.agent import create_ide_agent
from trae_web.state import TraeWebState


def test_agent_creation():
    """Test that the agent can be created without errors."""
    agent = create_ide_agent()
    assert agent is not None
    print("✓ Agent creation works")


def test_state_initialization():
    """Test that TraeWebState has required fields."""
    # Test that we can create a state with required fields
    state = TraeWebState(messages=[HumanMessage(content="test")], remaining_steps=10)
    assert state["messages"] == [HumanMessage(content="test")]
    assert state["remaining_steps"] == 10
    print("✓ State initialization works")


def test_tools_import():
    """Test that tools can be imported."""
    from trae_web.tools import all_tools

    assert len(all_tools) > 0
    tool_names = [tool.name for tool in all_tools]
    expected_tools = ["bash_tool", "edit_tool", "sequential_thinking_tool", "task_done"]
    for expected in expected_tools:
        assert any(expected in name for name in tool_names)
    print(f"✓ Tools import works: {tool_names}")


def test_simple_agent_invoke():
    """Test that agent can handle a simple invocation."""
    agent = create_ide_agent()

    # Simple test message
    initial_state = {
        "messages": [HumanMessage(content="Hello, can you help me?")],
        "remaining_steps": 5,
    }

    config = {"configurable": {"thread_id": "test-thread-123"}}

    try:
        # This should not raise an exception
        result = agent.invoke(initial_state, config=config)
        assert "messages" in result
        print("✓ Simple agent invoke works")
        print(f"Result message count: {len(result['messages'])}")
    except Exception as e:
        print(f"✗ Agent invoke failed: {e}")
        raise


if __name__ == "__main__":
    print("Running trae-web agent tests...")
    test_agent_creation()
    test_state_initialization()
    test_tools_import()
    test_simple_agent_invoke()
    print("\n✅ All tests passed!")
