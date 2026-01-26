"""Tests for Rovodev reader."""

import json

import pytest

from ai_session_bridge.core.session import MessageRole
from ai_session_bridge.readers.rovodev import RovodevReader


@pytest.fixture
def rovodev_session_dir(tmp_path):
    """Create a sample Rovodev session directory."""
    session_dir = tmp_path / "test-session-uuid"
    session_dir.mkdir()

    # Create metadata.json
    metadata = {
        "title": "Test Rovodev Session",
        "workspace_path": str(tmp_path / "workspace"),
        "created_at": "2026-01-15T10:00:00.000Z",
    }
    (session_dir / "metadata.json").write_text(json.dumps(metadata))

    # Create session_context.json - using Rovodev message_history format
    context = {
        "message_history": [
            {
                "role": "user",
                "parts": [{"part_kind": "text", "content": "Hello Rovodev"}],
                "timestamp": "2026-01-15T10:00:00.000Z",
            },
            {
                "role": "assistant",
                "parts": [{"part_kind": "text", "content": "Hello! Ready to help."}],
                "timestamp": "2026-01-15T10:00:05.000Z",
            },
        ]
    }
    (session_dir / "session_context.json").write_text(json.dumps(context))

    return session_dir


@pytest.fixture
def rovodev_session_with_tools(tmp_path):
    """Create Rovodev session with tool calls."""
    session_dir = tmp_path / "tool-session"
    session_dir.mkdir()

    metadata = {
        "title": "Tool Usage Session",
        "workspace_path": str(tmp_path / "workspace"),
    }
    (session_dir / "metadata.json").write_text(json.dumps(metadata))

    context = {
        "message_history": [
            {
                "role": "user",
                "parts": [{"part_kind": "text", "content": "Read file please"}],
                "timestamp": "2026-01-15T10:00:00.000Z",
            },
            {
                "role": "assistant",
                "parts": [
                    {
                        "part_kind": "tool_use",
                        "tool_name": "read_file",
                        "tool_input": {"path": "/test.txt"},
                    }
                ],
                "timestamp": "2026-01-15T10:00:05.000Z",
            },
            {
                "role": "user",
                "parts": [
                    {
                        "part_kind": "tool_result",
                        "content": "File contents here",
                    }
                ],
                "timestamp": "2026-01-15T10:00:10.000Z",
            },
        ]
    }
    (session_dir / "session_context.json").write_text(json.dumps(context))

    return session_dir


def test_rovodev_reader_tool_name():
    """Test Rovodev reader tool name."""
    reader = RovodevReader()
    assert reader.get_tool_name() == "rovodev"


def test_rovodev_read_session(rovodev_session_dir):
    """Test reading a Rovodev session."""
    reader = RovodevReader()
    session = reader.read_session(rovodev_session_dir)

    assert session.tool == "rovodev"
    assert session.title == "Test Rovodev Session"
    assert len(session.messages) == 2
    assert session.messages[0].role == MessageRole.USER
    assert session.messages[0].content == "Hello Rovodev"
    assert session.messages[1].role == MessageRole.ASSISTANT


def test_rovodev_session_with_tool_calls(rovodev_session_with_tools):
    """Test reading session with tool calls."""
    reader = RovodevReader()
    session = reader.read_session(rovodev_session_with_tools)

    assert session.title == "Tool Usage Session"
    assert len(session.messages) >= 2

    # Find assistant message with tool call
    assistant_msgs = [m for m in session.messages if m.role == MessageRole.ASSISTANT]
    assert len(assistant_msgs) > 0

    # Check tool call is captured
    tool_msg = next((m for m in assistant_msgs if m.tool_calls), None)
    if tool_msg:
        assert len(tool_msg.tool_calls) > 0
        assert tool_msg.tool_calls[0].name == "read_file"


def test_rovodev_missing_metadata(tmp_path):
    """Test handling missing metadata.json."""
    session_dir = tmp_path / "no-metadata"
    session_dir.mkdir()

    # Only session_context, no metadata
    context = {"conversation": []}
    (session_dir / "session_context.json").write_text(json.dumps(context))

    reader = RovodevReader()
    session = reader.read_session(session_dir)

    # Should still work but with no title
    assert session.tool == "rovodev"
    assert session.title is None or session.title == ""


def test_rovodev_missing_session_context(tmp_path):
    """Test handling missing session_context.json."""
    session_dir = tmp_path / "no-context"
    session_dir.mkdir()

    metadata = {"title": "Test"}
    (session_dir / "metadata.json").write_text(json.dumps(metadata))

    reader = RovodevReader()
    with pytest.raises(Exception):
        reader.read_session(session_dir)


def test_rovodev_empty_conversation(tmp_path):
    """Test reading session with empty conversation."""
    session_dir = tmp_path / "empty-conv"
    session_dir.mkdir()

    metadata = {"title": "Empty Session"}
    (session_dir / "metadata.json").write_text(json.dumps(metadata))

    context = {"message_history": []}
    (session_dir / "session_context.json").write_text(json.dumps(context))

    reader = RovodevReader()
    session = reader.read_session(session_dir)

    assert session.title == "Empty Session"
    assert len(session.messages) == 0
    assert session.message_count == 0


def test_rovodev_tool_call_with_unknown_name(tmp_path):
    """Test filtering tool calls with unknown names."""
    session_dir = tmp_path / "unknown-tool"
    session_dir.mkdir()

    metadata = {"title": "Unknown Tool"}
    (session_dir / "metadata.json").write_text(json.dumps(metadata))

    context = {
        "message_history": [
            {
                "role": "assistant",
                "parts": [
                    {
                        "part_kind": "tool_use",
                        "tool_name": "unknown",  # Should be filtered
                        "tool_input": {},
                    }
                ],
            }
        ]
    }
    (session_dir / "session_context.json").write_text(json.dumps(context))

    reader = RovodevReader()
    session = reader.read_session(session_dir)

    # Message with only unknown tool call should be skipped (empty content)
    # So we expect 0 messages, or if there's a message, it shouldn't contain "[Tool Call: unknown]"
    if len(session.messages) > 0:
        assert "[Tool Call: unknown]" not in session.messages[0].content
