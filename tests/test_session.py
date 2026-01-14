"""Tests for session models."""

from datetime import datetime

from ai_session_bridge.core.session import (
    Message,
    MessageRole,
    Session,
    ToolCall,
    ToolResult,
)


def test_message_creation(sample_message):
    """Test creating a message."""
    assert sample_message.role == MessageRole.USER
    assert "testing" in sample_message.content
    assert isinstance(sample_message.timestamp, datetime)


def test_session_message_count(sample_session):
    """Test session message count."""
    assert sample_session.message_count == 2


def test_session_preview(sample_session):
    """Test session preview generation."""
    preview = sample_session.preview
    assert "test" in preview.lower()
    assert len(preview) <= 203  # 200 + "..."


def test_tool_call():
    """Test tool call creation."""
    tool_call = ToolCall(
        name="read_file",
        arguments='{"path": "/test/file.py"}',
        id="call_123",
    )

    assert tool_call.name == "read_file"
    assert "path" in tool_call.arguments


def test_tool_result():
    """Test tool result creation."""
    result = ToolResult(
        content="File contents here",
        tool_call_id="call_123",
        is_error=False,
    )

    assert result.content == "File contents here"
    assert not result.is_error


def test_message_with_tool_calls():
    """Test message with tool calls."""
    msg = Message(
        role=MessageRole.ASSISTANT,
        content="Let me read that file",
        timestamp=datetime.now(),
        tool_calls=[
            ToolCall(
                name="read_file",
                arguments='{"path": "/test/file.py"}',
            )
        ],
    )

    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].name == "read_file"


def test_session_with_metadata():
    """Test session with metadata."""
    session = Session(
        id="test-123",
        tool="copilot",
        workspace_path="/test",
        messages=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={"custom_field": "value"},
    )

    assert session.metadata["custom_field"] == "value"
    assert session.message_count == 0
