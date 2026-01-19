"""Tests for Cursor reader."""

import json
import sqlite3

import pytest

from ai_session_bridge.core.session import MessageRole
from ai_session_bridge.readers.cursor import CursorReader


@pytest.fixture
def cursor_db(tmp_path):
    """Create a sample Cursor SQLite database."""
    db_path = tmp_path / "state.vscdb"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create ItemTable
    cursor.execute("""
        CREATE TABLE ItemTable (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Insert workspace mapping
    workspace_data = json.dumps({"folder": str(tmp_path / "workspace")})
    cursor.execute("INSERT INTO ItemTable VALUES (?, ?)", ("workspace.json", workspace_data))

    # Insert composer data with session
    composer_data = {
        "tabs": [
            {
                "id": "tab-123",
                "type": "chat",
                "chatId": "chat-456",
                "name": "Test Chat",
            }
        ],
        "chats": {
            "chat-456": {
                "bubbles": [
                    {
                        "type": "user",
                        "text": "Hello Cursor",
                        "createdAt": 1705315200000,
                    },
                    {
                        "type": "assistant",
                        "text": "Hello! How can I help?",
                        "createdAt": 1705315205000,
                    },
                ]
            }
        },
    }
    cursor.execute(
        "INSERT INTO ItemTable VALUES (?, ?)",
        ("composer.composerData", json.dumps(composer_data)),
    )

    conn.commit()
    conn.close()

    return db_path


def test_cursor_reader_tool_name(tmp_path):
    """Test Cursor reader tool name."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    reader = CursorReader(storage_dir)
    assert reader.get_tool_name() == "cursor"


@pytest.mark.skip(reason="Cursor reader expects path#sessionId format, not direct DB path")
def test_cursor_read_session(cursor_db, tmp_path):
    """Test reading a Cursor session from SQLite."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    reader = CursorReader(storage_dir)
    session = reader.read_session(cursor_db)

    assert session.tool == "cursor"
    assert session.title == "Test Chat"
    assert len(session.messages) >= 2
    # Check first message
    user_msg = next(m for m in session.messages if m.role == MessageRole.USER)
    assert "Hello Cursor" in user_msg.content


def test_cursor_empty_db(tmp_path):
    """Test reading empty Cursor database."""
    db_path = tmp_path / "empty.vscdb"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE ItemTable (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    reader = CursorReader(storage_dir)
    # Should handle empty DB gracefully
    with pytest.raises(Exception):
        reader.read_session(db_path)


def test_cursor_missing_composer_data(tmp_path):
    """Test handling missing composer data."""
    db_path = tmp_path / "missing.vscdb"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE ItemTable (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Only workspace data, no composer
    workspace_data = json.dumps({"folder": str(tmp_path / "workspace")})
    cursor.execute("INSERT INTO ItemTable VALUES (?, ?)", ("workspace.json", workspace_data))

    conn.commit()
    conn.close()

    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    reader = CursorReader(storage_dir)
    with pytest.raises(Exception):
        reader.read_session(db_path)


@pytest.fixture
def cursor_global_db_with_composer(tmp_path):
    """Create a Cursor global storage database with composer sessions."""
    global_storage = tmp_path / "globalStorage"
    global_storage.mkdir(parents=True)
    db_path = global_storage / "state.vscdb"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create cursorDiskKV table (for composer data)
    cursor.execute("""
        CREATE TABLE cursorDiskKV (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Insert composer session data
    composer_data = {
        "composerId": "test-composer-123",
        "name": "Test Composer Session",
        "createdAt": 1705315200000,
        "lastUpdatedAt": 1705315300000,
        "fullConversationHeadersOnly": [
            {"type": 1, "bubbleId": "bubble-1"},  # User message
            {"type": 2, "bubbleId": "bubble-2"},  # Assistant message
        ],
    }
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)",
        ("composerData:test-composer-123", json.dumps(composer_data)),
    )

    # Insert bubble data
    bubble1 = {"text": "How do I create a REST API?"}
    bubble2 = {"text": "I'll help you create a REST API with FastAPI..."}
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)", ("bubbleId:test-composer-123:bubble-1", json.dumps(bubble1))
    )
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)", ("bubbleId:test-composer-123:bubble-2", json.dumps(bubble2))
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def cursor_workspace_with_composers(tmp_path):
    """Create Cursor workspace storage with composer references."""
    workspace_storage = tmp_path / "workspaceStorage" / "abc123"
    workspace_storage.mkdir(parents=True)

    # Create workspace.json
    workspace_json = {"folder": f"file://{tmp_path}/my-project"}
    with open(workspace_storage / "workspace.json", "w") as f:
        json.dump(workspace_json, f)

    # Create state.vscdb with composer.composerData
    db_path = workspace_storage / "state.vscdb"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE ItemTable (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Insert composer.composerData with allComposers list
    composer_data = {
        "allComposers": [
            {"composerId": "test-composer-123"},
            {"composerId": "test-composer-456"},
        ]
    }
    cursor.execute(
        "INSERT INTO ItemTable VALUES (?, ?)",
        ("composer.composerData", json.dumps(composer_data)),
    )

    conn.commit()
    conn.close()

    return tmp_path


def test_cursor_get_sessions_from_global_db(tmp_path, cursor_global_db_with_composer):
    """Test getting sessions from global storage."""
    storage_dir = tmp_path / "workspaceStorage"
    storage_dir.mkdir(parents=True)

    reader = CursorReader(storage_dir)
    # Access the global DB directly
    global_db = cursor_global_db_with_composer

    summaries = reader._get_sessions_from_global_db(global_db, None)

    assert len(summaries) == 1
    assert summaries[0].id == "test-composer-123"
    assert summaries[0].title == "Test Composer Session"
    assert summaries[0].message_count == 2
    assert "REST API" in summaries[0].preview


def test_cursor_get_workspace_composer_ids(cursor_workspace_with_composers):
    """Test getting composer IDs for a specific workspace."""
    storage_dir = cursor_workspace_with_composers / "workspaceStorage"
    reader = CursorReader(storage_dir)

    workspace_path = str(cursor_workspace_with_composers / "my-project")
    composer_ids, actual_path = reader._get_workspace_composer_ids(workspace_path)

    assert composer_ids is not None
    assert "test-composer-123" in composer_ids
    assert "test-composer-456" in composer_ids
    assert actual_path == workspace_path


def test_cursor_get_workspace_composer_ids_not_found(tmp_path):
    """Test workspace not found returns None."""
    storage_dir = tmp_path / "workspaceStorage"
    storage_dir.mkdir(parents=True)

    reader = CursorReader(storage_dir)
    composer_ids, actual_path = reader._get_workspace_composer_ids("/nonexistent/path")

    assert composer_ids is None
    assert actual_path is None


def test_cursor_read_composer_session(tmp_path, cursor_global_db_with_composer):
    """Test reading a full composer session."""
    storage_dir = tmp_path / "workspaceStorage"
    storage_dir.mkdir(parents=True)

    reader = CursorReader(storage_dir)

    # Use the special path format for composer sessions
    session_path = f"{cursor_global_db_with_composer}#composer#test-composer-123"
    from pathlib import Path

    session = reader.read_session(Path(session_path))

    assert session.id == "test-composer-123"
    assert session.tool == "cursor"
    assert len(session.messages) == 2
    assert "REST API" in session.messages[0].content


def test_cursor_read_session_invalid_path(tmp_path):
    """Test read_session with invalid path format."""
    storage_dir = tmp_path / "workspaceStorage"
    storage_dir.mkdir(parents=True)

    reader = CursorReader(storage_dir)

    from pathlib import Path

    with pytest.raises(ValueError, match="Invalid Cursor session path"):
        reader.read_session(Path("/some/path/without/hash"))


def test_cursor_filter_sessions_by_workspace(tmp_path):
    """Test that sessions are filtered by workspace."""
    # Create workspace storage
    workspace_storage = tmp_path / "workspaceStorage" / "ws1"
    workspace_storage.mkdir(parents=True)

    workspace_json = {"folder": f"file://{tmp_path}/project-a"}
    with open(workspace_storage / "workspace.json", "w") as f:
        json.dump(workspace_json, f)

    ws_db = workspace_storage / "state.vscdb"
    conn = sqlite3.connect(ws_db)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute(
        "INSERT INTO ItemTable VALUES (?, ?)",
        ("composer.composerData", json.dumps({"allComposers": [{"composerId": "composer-a"}]})),
    )
    conn.commit()
    conn.close()

    # Create global storage with multiple composers
    global_storage = tmp_path / "globalStorage"
    global_storage.mkdir(parents=True)
    global_db = global_storage / "state.vscdb"

    conn = sqlite3.connect(global_db)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value TEXT)")

    # Composer A (belongs to workspace)
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)",
        (
            "composerData:composer-a",
            json.dumps(
                {
                    "composerId": "composer-a",
                    "name": "Project A Session",
                    "createdAt": 1705315200000,
                    "lastUpdatedAt": 1705315200000,
                    "fullConversationHeadersOnly": [{"type": 1, "bubbleId": "b1"}],
                }
            ),
        ),
    )

    # Composer B (different workspace)
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)",
        (
            "composerData:composer-b",
            json.dumps(
                {
                    "composerId": "composer-b",
                    "name": "Project B Session",
                    "createdAt": 1705315200000,
                    "lastUpdatedAt": 1705315200000,
                    "fullConversationHeadersOnly": [{"type": 1, "bubbleId": "b2"}],
                }
            ),
        ),
    )

    # Add bubble data
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)", ("bubbleId:composer-a:b1", json.dumps({"text": "Hello A"}))
    )
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)", ("bubbleId:composer-b:b2", json.dumps({"text": "Hello B"}))
    )

    conn.commit()
    conn.close()

    # Test filtering
    reader = CursorReader(tmp_path / "workspaceStorage")
    workspace_path = str(tmp_path / "project-a")

    summaries = reader._get_sessions_from_global_db(global_db, workspace_path)

    # Should only return composer-a
    assert len(summaries) == 1
    assert summaries[0].id == "composer-a"
    assert summaries[0].title == "Project A Session"
