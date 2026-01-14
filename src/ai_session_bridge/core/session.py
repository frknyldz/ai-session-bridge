"""Core models and data structures for AI Session Bridge."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Represents a tool/function call made by the assistant."""

    name: str
    arguments: str
    id: str | None = None


@dataclass
class ToolResult:
    """Result from a tool execution."""

    content: str
    tool_call_id: str | None = None
    is_error: bool = False


@dataclass
class Message:
    """A single message in a conversation."""

    role: MessageRole
    content: str
    timestamp: datetime
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Session:
    """A complete AI conversation session."""

    id: str
    tool: str  # copilot, cursor, rovodev
    workspace_path: str
    messages: list[Message]
    created_at: datetime
    updated_at: datetime
    metadata: dict = field(default_factory=dict)
    title: str | None = None

    @property
    def message_count(self) -> int:
        """Get the number of messages in this session."""
        return len(self.messages)

    @property
    def preview(self) -> str:
        """Get a preview of the first user message."""
        for msg in self.messages:
            if msg.role == MessageRole.USER and msg.content.strip():
                # Return first 200 chars
                content = msg.content.strip()
                return content[:200] + "..." if len(content) > 200 else content
        return ""


@dataclass
class SessionSummary:
    """Lightweight session info for listing without loading full content."""

    id: str
    tool: str
    workspace_path: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    preview: str
    file_path: str
    title: str | None = None
