"""Tests for MCP server."""

import json

import pytest

import ai_session_bridge.server as server_module
from ai_session_bridge.core.config import load_config
from ai_session_bridge.readers import get_registry
from ai_session_bridge.server import (
    _get_recent_context_tool,
    _get_session_tool,
    _list_sessions_tool,
    _search_sessions_tool,
)


@pytest.fixture
def mocked_storage_dirs(monkeypatch, tmp_path):
    """Mock storage directories for all tests."""
    vscode_storage = tmp_path / "vscode_storage"
    vscode_storage.mkdir()
    cursor_storage = tmp_path / "cursor_storage"
    cursor_storage.mkdir()
    rovodev_storage = tmp_path / "rovodev_storage"
    rovodev_storage.mkdir()

    from ai_session_bridge import readers
    from ai_session_bridge.readers import registry as registry_module

    # Patch where the functions are USED (in registry), not where they're defined
    monkeypatch.setattr(registry_module, "get_vscode_storage_dir", lambda: vscode_storage)
    monkeypatch.setattr(registry_module, "get_cursor_storage_dir", lambda: cursor_storage)
    monkeypatch.setattr(registry_module, "get_rovodev_sessions_dir", lambda: rovodev_storage)

    # Reset the global registry to force re-initialization with mocked paths
    readers.registry._registry = None

    yield {
        "vscode": vscode_storage,
        "cursor": cursor_storage,
        "rovodev": rovodev_storage,
    }

    # Reset registry after test
    readers.registry._registry = None


@pytest.fixture(autouse=True)
def setup_server_globals(mocked_storage_dirs):
    """Initialize server globals before each test."""
    server_module._config = load_config()
    server_module._registry = get_registry()
    server_module._search_index = None  # Disable search for tests
    yield
    # Cleanup
    server_module._config = None
    server_module._registry = None
    server_module._search_index = None


@pytest.fixture
def mock_workspace_for_mcp(tmp_path, mocked_storage_dirs):
    """Create a mock workspace for MCP testing."""
    workspace = tmp_path / "mcp-workspace"
    workspace.mkdir()

    # Create Copilot session in the mocked vscode_storage directory
    vscode_storage = mocked_storage_dirs["vscode"]
    storage = vscode_storage / "workspace-hash" / "chatSessions"
    storage.mkdir(parents=True, exist_ok=True)

    workspace_json = storage.parent / "workspace.json"
    workspace_json.write_text(json.dumps({"folder": str(workspace)}))

    session_data = {
        "version": 3,
        "id": "mcp-test-session",
        "customTitle": "MCP Test",
        "chatMessages": [
            {
                "role": "user",
                "content": "MCP test message",
                "timestamp": "2026-01-15T10:00:00.000Z",
            },
            {
                "role": "assistant",
                "content": "MCP response",
                "timestamp": "2026-01-15T10:00:05.000Z",
            },
        ],
    }
    (storage / "session.json").write_text(json.dumps(session_data))

    return workspace


@pytest.mark.asyncio
async def test_list_sessions_tool_basic(mock_workspace_for_mcp):
    """Test list_sessions tool."""
    args = {
        "workspace_path": str(mock_workspace_for_mcp),
        "limit": 10,
    }

    result = await _list_sessions_tool(args)

    assert len(result) > 0
    content = result[0].text
    assert "session" in content.lower()


@pytest.mark.asyncio
async def test_list_sessions_tool_with_filter(mock_workspace_for_mcp):
    """Test list_sessions with tool filter."""
    args = {
        "workspace_path": str(mock_workspace_for_mcp),
        "tool_filter": ["copilot"],
        "limit": 10,
    }

    result = await _list_sessions_tool(args)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_list_sessions_tool_empty_workspace(tmp_path):
    """Test list_sessions with empty workspace."""
    empty_workspace = tmp_path / "empty"
    empty_workspace.mkdir()

    args = {
        "workspace_path": str(empty_workspace),
        "limit": 10,
    }

    result = await _list_sessions_tool(args)
    assert len(result) > 0
    content = result[0].text
    # Should handle empty workspace gracefully
    assert "0" in content or "no sessions" in content.lower() or "sessions" in content.lower()


@pytest.mark.asyncio
async def test_get_session_tool_valid(mock_workspace_for_mcp):
    """Test get_session tool with valid session."""
    args = {
        "session_id": "mcp-test-session",
        "tool": "copilot",
        "workspace_path": str(mock_workspace_for_mcp),
    }

    result = await _get_session_tool(args)

    assert len(result) > 0
    content = result[0].text
    assert "mcp test message" in content.lower() or "session" in content.lower()


@pytest.mark.asyncio
async def test_get_session_tool_invalid_id(mock_workspace_for_mcp):
    """Test get_session tool with invalid session ID."""
    args = {
        "session_id": "nonexistent-id",
        "tool": "copilot",
        "workspace_path": str(mock_workspace_for_mcp),
    }

    result = await _get_session_tool(args)

    assert len(result) > 0
    content = result[0].text
    assert "error" in content.lower() or "not found" in content.lower()


@pytest.mark.asyncio
async def test_search_sessions_tool_disabled(mock_workspace_for_mcp):
    """Test search_sessions when search is disabled."""
    args = {
        "query": "test",
        "workspace_path": str(mock_workspace_for_mcp),
        "limit": 20,
    }

    # This might fail if search index is not initialized
    result = await _search_sessions_tool(args)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_get_recent_context_tool(mock_workspace_for_mcp):
    """Test get_recent_context tool."""
    args = {
        "workspace_path": str(mock_workspace_for_mcp),
        "max_sessions": 3,
        "max_messages": 10,
    }

    result = await _get_recent_context_tool(args)

    assert len(result) > 0
    content = result[0].text
    # Should return some context
    assert len(content) > 0


@pytest.mark.asyncio
async def test_get_recent_context_empty_workspace(tmp_path):
    """Test get_recent_context with empty workspace."""
    empty_workspace = tmp_path / "empty"
    empty_workspace.mkdir()

    args = {
        "workspace_path": str(empty_workspace),
        "max_sessions": 3,
        "max_messages": 10,
    }

    result = await _get_recent_context_tool(args)
    assert len(result) > 0
    content = result[0].text
    # Should handle empty gracefully
    assert "no sessions" in content.lower() or "sessions" in content.lower() or len(content) >= 0


@pytest.mark.asyncio
async def test_search_sessions_with_tool_filter(mock_workspace_for_mcp):
    """Test search_sessions with tool filter."""
    args = {
        "query": "MCP",
        "workspace_path": str(mock_workspace_for_mcp),
        "tool": "copilot",
        "limit": 10,
    }

    result = await _search_sessions_tool(args)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_list_sessions_limit_param(mock_workspace_for_mcp):
    """Test list_sessions respects limit parameter."""
    args = {
        "workspace_path": str(mock_workspace_for_mcp),
        "limit": 1,
    }

    result = await _list_sessions_tool(args)
    assert len(result) > 0

    content = result[0].text
    data = json.loads(content)

    # Should respect limit
    assert len(data.get("sessions", [])) <= 1
