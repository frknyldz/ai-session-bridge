"""Tests for content filtering."""

from datetime import datetime

from ai_session_bridge.core.filter import ContentFilter, FilterConfig
from ai_session_bridge.core.session import Message, MessageRole


def test_filter_api_key():
    """Test filtering API keys."""
    config = FilterConfig(enabled=True)
    filter = ContentFilter(config)

    text = 'api_key = "sk_test_abc123def456ghi789jkl"'
    filtered = filter.filter(text)

    assert "[REDACTED]" in filtered
    assert "sk_test_abc123def456ghi789jkl" not in filtered


def test_filter_bearer_token():
    """Test filtering bearer tokens."""
    config = FilterConfig(enabled=True)
    filter = ContentFilter(config)

    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    filtered = filter.filter(text)

    assert "[REDACTED]" in filtered
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in filtered


def test_filter_disabled():
    """Test that filtering can be disabled."""
    config = FilterConfig(enabled=False)
    filter = ContentFilter(config)

    text = 'api_key = "secret123"'
    filtered = filter.filter(text)

    assert filtered == text
    assert "[REDACTED]" not in filtered


def test_filter_message():
    """Test filtering a message."""
    config = FilterConfig(enabled=True)
    filter = ContentFilter(config)

    msg = Message(
        role=MessageRole.USER,
        content='Here is my api_key = "sk_test_abc123def456ghi789jkl"',
        timestamp=datetime.now(),
    )

    filtered = filter.filter_message(msg)

    assert "[REDACTED]" in filtered.content
    assert "sk_test_abc123def456ghi789jkl" not in filtered.content
    assert filtered.role == msg.role
    assert filtered.timestamp == msg.timestamp


def test_custom_patterns():
    """Test custom filter patterns."""
    config = FilterConfig(enabled=True, patterns=[r"email:\s*\S+@\S+"], replacement="[EMAIL]")
    filter = ContentFilter(config)

    text = "Contact me at email: user@example.com"
    filtered = filter.filter(text)

    assert "[EMAIL]" in filtered
    assert "user@example.com" not in filtered
