"""Pytest configuration and fixtures."""

from datetime import datetime

import pytest

from ai_session_bridge.core.session import Message, MessageRole, Session


@pytest.fixture
def sample_message():
    """Create a sample message."""
    return Message(
        role=MessageRole.USER,
        content="Hello, how can I help with testing?",
        timestamp=datetime.now(),
    )


@pytest.fixture
def sample_session():
    """Create a sample session."""
    return Session(
        id="test-session-123",
        tool="copilot",
        workspace_path="/test/workspace",
        messages=[
            Message(
                role=MessageRole.USER,
                content="How do I test this?",
                timestamp=datetime.now(),
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="You can use pytest for testing.",
                timestamp=datetime.now(),
            ),
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return workspace
