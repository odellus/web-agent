# Web Agent - AI-Powered Web Development Assistant

A sophisticated AI agent system built on LangGraph that provides web development assistance through natural language commands. This project combines the power of TRAE Agent's methodology with a web-friendly interface and enhanced tooling.

## 🚀 Overview

Web Agent is an AI assistant that helps developers with web development tasks through natural language commands. It can create files, run commands, edit code, and perform complex multi-step operations while maintaining proper working directory context.

### Key Features

- **Natural Language Interface**: Interact with your development environment using plain English
- **Working Directory Awareness**: Tools operate in the correct directory context
- **TRAE-Inspired Reflection**: Sophisticated reasoning and verification steps
- **Real-time Streaming**: Watch the agent work step-by-step
- **Extensible Tool System**: Easily add new capabilities
- **Observability**: Built-in Langfuse integration for detailed tracing

## 📦 Project Structure

```
web-agent/
├── agent-py/                    # Python backend agent
│   ├── src/
│   │   └── web_agent/
│   │       ├── agent.py         # Agent creation and configuration
│   │       ├── state.py         # Agent state definition (TraeWebState)
│   │       └── tools/           # Tool implementations
│   │           ├── bash_tool.py      # Enhanced bash with injected state
│   │           ├── edit_tool.py      # File editing operations
│   │           ├── sequential_thinking_tool.py  # TRAE-style reasoning
│   │           └── task_done_tool.py  # Task completion signaling
│   ├── tests/                   # Test files
│   └── pyproject.toml          # Python project configuration
└── ui/                          # React frontend (future development)
    └── (to be implemented)
```

## 🏗️ Architecture

This project builds upon the excellent work of the [TRAE Agent](https://github.com/bytedance/trae-agent) from ByteDance, adapting its sophisticated reasoning and reflection capabilities for web development workflows.

### Core Components

1. **TraeWebState**: Extended state management with working directory support
2. **Custom LangGraph Workflow**: Implements TRAE-style reflection loops
3. **Enhanced Tools**: Bash, file editing, and reasoning tools with proper context
4. **Observability**: Langfuse integration for detailed tracing and debugging

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.10+
- [UV](https://github.com/astral-sh/uv) package manager
- Ollama (for local model inference) or OpenAI API access

### Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd copilotkit-work/web-agent/agent-py

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
uv sync

# Set up working directory
mkdir -p /home/$(whoami)/src/projects/copilotkit-work/test_workingdir

# Run tests to verify installation
uv run tests/custom_agent_test.py
```

### Configuration

Create a `.env` file for configuration:

```env
# Model configuration
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3:latest

# Working directory
DEFAULT_WORKING_DIR=/home/$(whoami)/src/projects/copilotkit-work/test_workingdir

# Observability (optional)
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_secret
```

## 🎯 Usage

### Basic Agent Interaction

```python
from web_agent.agent import create_web_agent

# Create the agent
agent = create_web_agent()

# Execute a task
result = await agent.ainvoke({
    "messages": [HumanMessage(content="Create a React component called Button")],
    "working_directory": "/path/to/your/project",
    "remaining_steps": 20
})
```

### Example Tasks

The agent can handle various web development tasks:

```bash
# Create and edit files
"Create a React component called Header with a navigation menu"

# Run development commands  
"Start the development server with npm run dev"

# Complex multi-step operations
"Set up a new Next.js project with TypeScript and Tailwind CSS"

# File operations
"Rename components/Button.js to components/Button.tsx and add TypeScript types"
```

## 🔧 Tools

### Available Tools

1. **bash_tool**: Execute shell commands with working directory context
2. **edit_tool**: Create, view, and edit files with string replacement
3. **sequential_thinking_tool**: TRAE-style reasoning and planning
4. **task_done_tool**: Signal task completion

### Custom Tool Development

Tools are implemented using LangChain's tool decorator with state injection:

```python
@tool
def custom_tool(
    param: str,
    working_directory: Annotated[DirectoryPath, InjectedState("working_directory")]
) -> str:
    """Tool description."""
    # Implementation here
    pass
```

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test files
uv run tests/custom_agent_test.py
uv run tests/bash_tool_test.py
```

## 📊 Observability

The project includes Langfuse integration for detailed tracing:

1. **Tool Calls**: Track which tools are called with what parameters
2. **Agent Reasoning**: See the agent's thought process
3. **Performance Metrics**: Monitor token usage and latency
4. **Error Tracking**: Identify and debug failures

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation for new features
- Use type hints throughout
- Ensure backward compatibility

## 🙏 Acknowledgments

This project builds upon the excellent work of:

- **[TRAE Agent](https://github.com/bytedance/trae-agent)** by ByteDance - For the sophisticated reasoning and reflection methodology
- **[LangGraph](https://github.com/langchain-ai/langgraph)** - For the powerful agent framework
- **[LangChain](https://github.com/langchain-ai/langchain)** - For tool integration and LLM abstraction
- **[Ollama](https://ollama.ai)** - For local model inference

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🐛 Bug Reports & Feature Requests

Please use the [GitHub Issues](https://github.com/your-org/web-agent/issues) to report bugs or request features.

## 📞 Support

- Documentation: [Read the Docs](https://web-agent.readthedocs.io)
- Discussions: [GitHub Discussions](https://github.com/your-org/web-agent/discussions)
- Issues: [GitHub Issues](https://github.com/your-org/web-agent/issues)

---

**Note**: This project is under active development. Features and APIs may change as we continue to improve the system.