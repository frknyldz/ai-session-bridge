"""Sensitive content filtering."""

import re
from dataclasses import dataclass

from .session import Message, ToolCall, ToolResult

# Default patterns for sensitive content
DEFAULT_FILTER_PATTERNS = [
    # API Keys
    r"(?i)(api[_-]?key|apikey)[\"']?\s*[:=]\s*[\"']?[a-zA-Z0-9_-]{20,}",
    # Generic secrets
    r"(?i)(secret|password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?[^\s\"']{8,}",
    # Bearer tokens
    r"(?i)bearer\s+[a-zA-Z0-9_-]{20,}",
    # AWS credentials
    r"(?i)(aws_access_key_id|aws_secret_access_key)\s*=\s*[A-Z0-9]{16,}",
    # Private keys
    r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END",
    # GitHub tokens
    r"gh[pousr]_[a-zA-Z0-9]{36,}",
    # Slack tokens
    r"xox[baprs]-[a-zA-Z0-9-]+",
]


@dataclass
class FilterConfig:
    """Configuration for content filtering."""

    enabled: bool = True
    patterns: list[str] = None
    replacement: str = "[REDACTED]"

    def __post_init__(self) -> None:
        """Initialize patterns with defaults if not provided."""
        if self.patterns is None:
            self.patterns = DEFAULT_FILTER_PATTERNS.copy()


class ContentFilter:
    """Filters sensitive content from messages."""

    def __init__(self, config: FilterConfig = None):
        """
        Initialize content filter.

        Args:
            config: Filter configuration. If None, uses defaults.
        """
        self.config = config or FilterConfig()
        self.compiled_patterns: list[re.Pattern] = []

        if self.config.enabled and self.config.patterns:
            self.compiled_patterns = [re.compile(pattern) for pattern in self.config.patterns]

    def filter(self, content: str) -> str:
        """
        Filter sensitive content from a string.

        Args:
            content: Text to filter

        Returns:
            Filtered text with sensitive content redacted
        """
        if not self.config.enabled or not content:
            return content

        result = content
        for pattern in self.compiled_patterns:
            result = pattern.sub(self.config.replacement, result)

        return result

    def filter_tool_call(self, tool_call: ToolCall) -> ToolCall:
        """Filter sensitive content from a tool call."""
        return ToolCall(
            name=tool_call.name,
            arguments=self.filter(tool_call.arguments),
            id=tool_call.id,
        )

    def filter_tool_result(self, tool_result: ToolResult) -> ToolResult:
        """Filter sensitive content from a tool result."""
        return ToolResult(
            content=self.filter(tool_result.content),
            tool_call_id=tool_result.tool_call_id,
            is_error=tool_result.is_error,
        )

    def filter_message(self, message: Message) -> Message:
        """
        Filter sensitive content from a message.

        Args:
            message: Message to filter

        Returns:
            New message with filtered content
        """
        if not self.config.enabled:
            return message

        return Message(
            role=message.role,
            content=self.filter(message.content),
            timestamp=message.timestamp,
            tool_calls=[self.filter_tool_call(tc) for tc in (message.tool_calls or [])],
            tool_results=[self.filter_tool_result(tr) for tr in (message.tool_results or [])],
            metadata=message.metadata,
        )
