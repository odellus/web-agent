"""LangGraph adapter for ACP integration.

This module provides an adapter between the ACP protocol and the existing
LangGraph agent, handling session management, prompt processing, and
tool execution.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI

from web_agent.agent import get_agent
from web_agent.state import WebAgentState
from web_agent.tools import all_tools
from ..protocol.types import (
    PromptResult,
    ACPMessage,
    MessageContent,
    ToolResult,
    ToolCall,
)
from ..protocol.sessions import get_session_manager

logger = logging.getLogger(__name__)


class LangGraphAdapter:
    """Adapter between ACP protocol and LangGraph agent."""

    def __init__(self):
        """Initialize the LangGraph adapter."""
        self.agent = None
        self.checkpointer = None
        self.llm = None
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_manager = get_session_manager()
        self._initialized = False

    async def initialize(self):
        """Initialize the LangGraph agent and components."""
        if self._initialized:
            return

        try:
            # Initialize LLM
            self.llm = ChatOpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",
                model="qwen3:latest",
                temperature=0.1,
            )

            # Initialize checkpointer (using MemorySaver for now)
            from langgraph.checkpoint.memory import MemorySaver

            self.checkpointer = MemorySaver()

            # Initialize agent
            self.agent = get_agent(self.checkpointer)

            self._initialized = True
            logger.info("LangGraph adapter initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize LangGraph adapter: {e}")
            raise

    async def create_session(
        self,
        session_id: str,
        working_directory: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new LangGraph session.

        Args:
            session_id: Unique session identifier
            working_directory: Working directory for the session
            metadata: Optional session metadata

        Returns:
            Session state dictionary
        """
        if not self._initialized:
            await self.initialize()

        # Create initial state
        initial_state = WebAgentState(
            messages=[],
            remaining_steps=50,
            working_directory=working_directory,
        )

        # Store session state
        self.sessions[session_id] = {
            "state": initial_state,
            "working_directory": working_directory,
            "metadata": metadata or {},
            "config": {"configurable": {"thread_id": session_id}},
        }

        logger.info(f"Created LangGraph session {session_id}")
        return self.sessions[session_id]

    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of a session.

        Args:
            session_id: Session identifier

        Returns:
            Session state or None if not found
        """
        return self.sessions.get(session_id)

    async def update_session_state(
        self, session_id: str, state_updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update the state of a session.

        Args:
            session_id: Session identifier
            state_updates: State updates to apply

        Returns:
            Updated session state or None if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return None

        # Update state
        if "state" in state_updates:
            session["state"].update(state_updates["state"])

        # Update other fields
        for key, value in state_updates.items():
            if key != "state":
                session[key] = value

        return session

    async def process_prompt(
        self,
        session_id: str,
        message: str,
        mode: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a prompt through the LangGraph agent.

        Args:
            session_id: Session identifier
            message: User message
            mode: Optional mode (execute, plan, safe)
            model: Optional model name

        Yields:
            Streaming updates during processing
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not self._initialized:
            await self.initialize()

        try:
            # Create human message
            human_message = HumanMessage(content=message)
            session["state"]["messages"].append(human_message)

            # Update session mode if provided
            if mode:
                session["mode"] = mode

            # Update model if provided
            if model:
                session["model"] = model

            # Stream agent execution
            async for chunk in self.agent.astream(
                session["state"],
                config=session["config"],
                stream_mode="values",
            ):
                # Update session state
                if "messages" in chunk:
                    session["state"]["messages"] = chunk["messages"]
                if "remaining_steps" in chunk:
                    session["state"]["remaining_steps"] = chunk["remaining_steps"]

                # Yield update
                yield {
                    "type": "state_update",
                    "session_id": session_id,
                    "state": chunk,
                }

                # Check for tool calls
                messages = chunk.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if isinstance(last_message, AIMessage) and hasattr(
                        last_message, "tool_calls"
                    ):
                        for tool_call in last_message.tool_calls:
                            yield {
                                "type": "tool_call",
                                "session_id": session_id,
                                "tool_call": {
                                    "id": tool_call["id"],
                                    "name": tool_call["name"],
                                    "arguments": tool_call["args"],
                                },
                            }

                    # Check for tool results
                    elif isinstance(last_message, ToolMessage):
                        yield {
                            "type": "tool_result",
                            "session_id": session_id,
                            "tool_result": {
                                "tool_call_id": getattr(
                                    last_message, "tool_call_id", ""
                                ),
                                "content": last_message.content,
                            },
                        }

        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            yield {
                "type": "error",
                "session_id": session_id,
                "error": str(e),
            }

    async def get_prompt_result(self, session_id: str) -> PromptResult:
        """Get the final result of prompt processing.

        Args:
            session_id: Session identifier

        Returns:
            Prompt result with response message
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get current state from agent
        try:
            current_state = await self.agent.aget_state(config=session["config"])
            messages = current_state.values.get("messages", [])

            # Find the last AI message
            last_ai_message = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    last_ai_message = msg
                    break

            if not last_ai_message:
                # Create a default response
                content = "No response generated"
                stop_reason = "completion"
            else:
                content = last_ai_message.content or ""
                stop_reason = "completion"

            # Create ACP message
            acp_message = ACPMessage(
                role="assistant",
                content=[MessageContent(type="text", text=content)],
            )

            return PromptResult(
                message=acp_message,
                stop_reason=stop_reason,
                usage={
                    "total_messages": len(messages),
                    "remaining_steps": session["state"].get("remaining_steps", 0),
                },
            )

        except Exception as e:
            logger.error(f"Error getting prompt result: {e}")
            # Return error result
            acp_message = ACPMessage(
                role="assistant",
                content=[MessageContent(type="text", text=f"Error: {str(e)}")],
            )
            return PromptResult(
                message=acp_message,
                stop_reason="error",
            )

    async def set_mode(self, session_id: str, mode: str):
        """Set the mode for a session.

        Args:
            session_id: Session identifier
            mode: Mode to set (execute, plan, safe)
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session["mode"] = mode
        logger.info(f"Set mode {mode} for session {session_id}")

    async def set_model(self, session_id: str, model: str):
        """Set the model for a session.

        Args:
            session_id: Session identifier
            model: Model name to set
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session["model"] = model
        logger.info(f"Set model {model} for session {session_id}")

    async def cancel_session(self, session_id: str):
        """Cancel an ongoing session operation.

        Args:
            session_id: Session identifier
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # In a real implementation, we would interrupt the agent execution
        # For now, we'll just mark the session as cancelled
        session["cancelled"] = True
        logger.info(f"Cancelled session {session_id}")

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        session = self.sessions.pop(session_id, None)
        if session:
            logger.info(f"Deleted LangGraph session {session_id}")
            return True
        return False

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics.

        Returns:
            Dictionary with session statistics
        """
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(
                [s for s in self.sessions.values() if not s.get("cancelled", False)]
            ),
            "initialized": self._initialized,
        }
