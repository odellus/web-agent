from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class ReasoningStep(BaseModel):
    """A single step in the reasoning process - comes BEFORE status decisions"""

    analysis: str = Field(description="Detailed analysis of the current situation")
    considerations: List[str] = Field(
        default_factory=list, description="Key factors being considered"
    )
    alternatives: List[str] = Field(
        default_factory=list, description="Alternative approaches considered"
    )


class CompletionSignal(BaseModel):
    """Structured completion signal with reasoning FIRST"""

    reasoning: ReasoningStep = Field(
        description="Analysis and reasoning about the current state"
    )
    status: Literal["completed", "in_progress", "stalled", "needs_input"] = Field(
        description="Current status based on the reasoning"
    )
    next_action: Optional[str] = Field(
        default=None, description="Suggested next action if needed"
    )


class ToolCallRecord(BaseModel):
    """Record of a tool call and its result"""

    tool_name: str = Field(description="Name of the tool called")
    arguments: Dict[str, Any] = Field(description="Arguments passed to the tool")
    result: str = Field(description="Result of the tool execution")
    success: bool = Field(description="Whether the tool call was successful")


class AgentState(BaseModel):
    """Main state model for the IDE agent with reasoning-first structure"""

    # Core task information
    task: str = Field(description="The current task being executed")
    current_step: int = Field(default=0, description="Current step number in execution")

    # Reasoning and status (reasoning comes FIRST)
    reasoning: Optional[ReasoningStep] = Field(
        default=None, description="Current reasoning analysis"
    )
    status: Literal["running", "completed", "error", "stalled", "needs_input"] = Field(
        default="running", description="Current execution status"
    )

    # Thought process
    thoughts: List[str] = Field(
        default_factory=list, description="Sequence of thoughts during execution"
    )
    current_thought: Optional[str] = Field(
        default=None, description="Current active thought"
    )

    # Tool interactions
    tool_calls: List[ToolCallRecord] = Field(
        default_factory=list, description="History of tool calls"
    )
    pending_tool_call: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool call awaiting execution"
    )

    # Results and output
    final_result: Optional[str] = Field(
        default=None, description="Final result when task is completed"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )

    # LangGraph required fields
    messages: List[BaseMessage] = Field(
        default_factory=list, description="Chat message history"
    )

    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )


class StateUpdate(BaseModel):
    """Update package for modifying agent state"""

    reasoning: Optional[ReasoningStep] = Field(
        default=None, description="Updated reasoning analysis"
    )
    status: Optional[
        Literal["running", "completed", "error", "stalled", "needs_input"]
    ] = Field(default=None, description="Updated status")
    current_thought: Optional[str] = Field(
        default=None, description="Updated current thought"
    )
    tool_result: Optional[ToolCallRecord] = Field(
        default=None, description="Result of the latest tool call"
    )
    final_result: Optional[str] = Field(
        default=None, description="Final result if task completed"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
