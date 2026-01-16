"""Cursor session reader.

Cursor stores chat history in state.vscdb SQLite database.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ..core.session import Message, MessageRole, Session, SessionSummary
from ..core.workspace import find_workspace_session_dir
from .base import SessionReader


class CursorReader(SessionReader):
    """Reader for Cursor sessions (stored in SQLite database)."""

    def __init__(self, storage_dir: Path):
        """
        Initialize Cursor reader.

        Args:
            storage_dir: Cursor workspaceStorage directory
        """
        self.storage_dir = storage_dir
        self.tool_name = "cursor"

    def get_tool_name(self) -> str:
        """Get tool name."""
        return self.tool_name

    def get_sessions(self, workspace_path: str | None) -> list[SessionSummary]:
        """Get all Cursor sessions for a workspace (or all if workspace_path is None)."""
        summaries = []

        # Check global storage first (newer Cursor versions)
        global_db = self.storage_dir.parent / "globalStorage" / "state.vscdb"
        if global_db.exists():
            summaries.extend(self._get_sessions_from_global_db(global_db, workspace_path))

        # Also check workspace-specific databases (older format)
        if workspace_path:
            workspace_dir = find_workspace_session_dir(workspace_path, self.storage_dir, use_hash=True)
            if workspace_dir:
                state_db = workspace_dir / "state.vscdb"
                if state_db.exists():
                    summaries.extend(self._get_sessions_from_workspace_db(state_db, workspace_path))
        elif workspace_path is None:
            # Only get sessions from all workspaces when explicitly requesting all (workspace_path=None)
            for state_db in self.storage_dir.glob("*/state.vscdb"):
                ws_path = f"cursor-{state_db.parent.name}"
                summaries.extend(self._get_sessions_from_workspace_db(state_db, ws_path))

        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def _get_sessions_from_workspace_db(self, state_db: Path, workspace_path: str) -> list[SessionSummary]:
        """Get sessions from workspace-specific database (old format)."""
        summaries = []
        try:
            conn = sqlite3.connect(state_db)
            cursor = conn.execute(
                "SELECT key, value FROM ItemTable WHERE key LIKE 'workbench.panel.aichat.view.aichat.chatdata.%'"
            )

            for row in cursor.fetchall():
                key, value = row
                try:
                    # Extract session ID from key
                    session_id = key.split(".")[-1]

                    # Parse JSON value
                    # Parse JSON value
                    data = json.loads(value)

                    # Create summary
                    messages = data.get("messages", [])
                    if not messages:
                        continue

                    # Get customTitle if available
                    title = data.get("customTitle")

                    # Get first user message as preview
                    preview = ""
                    for msg in messages:
                        if msg.get("sender") == "user":
                            preview = msg.get("text", "")[:200]
                            break

                    # Use file modification time as timestamp
                    import os

                    stat = os.stat(state_db)
                    created_at = datetime.fromtimestamp(stat.st_ctime)
                    updated_at = datetime.fromtimestamp(stat.st_mtime)

                    # Determine workspace path
                    if workspace_path:
                        ws_path = workspace_path
                    else:
                        ws_path = f"cursor-{Path(state_db).parent.name}"

                    summaries.append(
                        SessionSummary(
                            id=session_id,
                            tool=self.tool_name,
                            workspace_path=ws_path,
                            created_at=created_at,
                            updated_at=updated_at,
                            message_count=len(messages),
                            preview=preview,
                            file_path=f"{state_db}#{session_id}",  # Special format: db_path#session_id
                            title=title,
                        )
                    )
                except Exception:
                    continue

            conn.close()

        except Exception:
            pass

        return summaries

        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def _get_sessions_from_global_db(self, global_db: Path, workspace_path: str | None) -> list[SessionSummary]:
        """Get sessions from global storage database (new format with composerData)."""
        summaries = []

        # If workspace_path is specified, get the list of composer IDs for that workspace
        workspace_composer_ids = None
        actual_workspace_path = None
        if workspace_path:
            workspace_composer_ids, actual_workspace_path = self._get_workspace_composer_ids(workspace_path)
            if workspace_composer_ids is not None and len(workspace_composer_ids) == 0:
                # Workspace found but has no composers
                return summaries

        try:
            conn = sqlite3.connect(global_db)
            # Query composerData entries
            cursor = conn.execute(
                "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%' AND LENGTH(value) > 10"
            )

            import os

            stat = os.stat(global_db)

            for row in cursor.fetchall():
                key, value = row
                try:
                    composer_id = key.split(":")[1]

                    # Filter by workspace if specified
                    if workspace_composer_ids is not None and composer_id not in workspace_composer_ids:
                        continue

                    data = json.loads(value)

                    # Get conversation headers to count messages
                    headers = data.get("fullConversationHeadersOnly", [])
                    message_count = len(headers)

                    if message_count == 0:
                        continue

                    # Get title from name or first message
                    title = data.get("name")

                    # Get preview from first user message in conversation
                    preview = ""
                    if headers:
                        # Try to get actual message content from first user message
                        for header in headers:
                            if header.get("type") == 1:  # User message
                                bubble_id = header.get("bubbleId")
                                if bubble_id:
                                    # Try to fetch bubble content from global db
                                    try:
                                        bubble_cursor = conn.execute(
                                            "SELECT value FROM cursorDiskKV WHERE key = ?",
                                            (f"bubbleId:{composer_id}:{bubble_id}",),
                                        )
                                        bubble_row = bubble_cursor.fetchone()
                                        if bubble_row:
                                            bubble_data = json.loads(bubble_row[0])
                                            # Try to extract text from bubble
                                            bubble_text = bubble_data.get("text", "")
                                            if bubble_text:
                                                preview = bubble_text.strip()[:200]
                                    except Exception:
                                        pass
                                if preview:
                                    break

                    # Fallback to title if no preview found
                    if not preview and title:
                        preview = title

                    # Use composer timestamps
                    created_at = datetime.fromtimestamp(data.get("createdAt", stat.st_ctime) / 1000)
                    last_updated = datetime.fromtimestamp(data.get("lastUpdatedAt", stat.st_mtime) / 1000)

                    # Use actual workspace path if we found one, otherwise mark as global
                    ws_path = actual_workspace_path if actual_workspace_path else "cursor-composer-global"

                    summaries.append(
                        SessionSummary(
                            id=composer_id,
                            tool=self.tool_name,
                            workspace_path=ws_path,
                            created_at=created_at,
                            updated_at=last_updated,
                            message_count=message_count,
                            preview=preview,
                            file_path=f"{global_db}#composer#{composer_id}",
                            title=title,
                        )
                    )
                except Exception:
                    continue

            conn.close()
        except Exception:
            pass

        return summaries

    def _get_workspace_composer_ids(self, workspace_path: str) -> tuple[set[str] | None, str | None]:
        """Get the set of composer IDs associated with a workspace.

        Returns:
            Tuple of (composer_ids set or None if workspace not found, actual workspace path)
        """
        from urllib.parse import unquote, urlparse

        # Find the workspace storage directory for this workspace
        for ws_dir in self.storage_dir.iterdir():
            if not ws_dir.is_dir():
                continue

            workspace_json = ws_dir / "workspace.json"
            if not workspace_json.exists():
                continue

            try:
                with open(workspace_json) as f:
                    ws_data = json.load(f)

                folder_uri = ws_data.get("folder", "")
                if folder_uri:
                    parsed = urlparse(folder_uri)
                    if parsed.scheme == "file":
                        ws_folder = unquote(parsed.path)
                        # Normalize both paths for comparison
                        if Path(ws_folder).resolve() == Path(workspace_path).resolve():
                            # Found the workspace! Now get composer IDs
                            state_db = ws_dir / "state.vscdb"
                            if state_db.exists():
                                conn = sqlite3.connect(state_db)
                                cursor = conn.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
                                row = cursor.fetchone()
                                conn.close()

                                if row:
                                    composer_data = json.loads(row[0])
                                    all_composers = composer_data.get("allComposers", [])
                                    composer_ids = set()
                                    for composer in all_composers:
                                        if isinstance(composer, dict):
                                            cid = composer.get("composerId")
                                            if cid:
                                                composer_ids.add(cid)
                                    return composer_ids, workspace_path
                            return set(), workspace_path  # Workspace found but no composers
            except Exception:
                continue

        return None, None  # Workspace not found

    def read_session(self, session_path: Path, workspace_path: str | None = None) -> Session:
        """Read a full Cursor session.

        Args:
            session_path: Path in format "db_path#session_id" or "db_path#composer#session_id"
            workspace_path: Optional workspace path to include in session
        """
        # Parse the special path format
        path_str = str(session_path)
        if "#" not in path_str:
            raise ValueError(f"Invalid Cursor session path: {path_str}")

        parts = path_str.split("#")
        db_path = parts[0]

        # Check if this is a composer session (format: db_path#composer#session_id)
        is_composer = len(parts) == 3 and parts[1] == "composer"
        session_id = parts[2] if is_composer else parts[1]

        conn = sqlite3.connect(db_path)

        if is_composer:
            # Composer sessions are stored in cursorDiskKV table
            return self._read_composer_session(conn, db_path, session_id, workspace_path)
        else:
            # Legacy AI chat sessions in ItemTable
            cursor = conn.execute(
                "SELECT value FROM ItemTable WHERE key = ?",
                (f"workbench.panel.aichat.view.aichat.chatdata.{session_id}",),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                raise ValueError(f"Session {session_id} not found")

        data = json.loads(row[0])

        # Parse messages and get title
        title = data.get("customTitle") or data.get("name")  # Try customTitle first, then name
        messages = []
        for msg in data.get("messages", []):
            sender = msg.get("sender")
            role = MessageRole.USER if sender == "user" else MessageRole.ASSISTANT
            content = msg.get("text", "")

            if content:
                messages.append(
                    Message(
                        role=role,
                        content=content,
                        timestamp=datetime.now(),  # Cursor doesn't store timestamps per message
                    )
                )

        # Use file modification time
        import os

        stat = os.stat(db_path)
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)

        if workspace_path is None:
            workspace_path = f"cursor-{Path(db_path).parent.name}"

        return Session(
            id=session_id,
            tool=self.tool_name,
            workspace_path=workspace_path,
            title=title,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata={"file_path": path_str},
        )

    def _read_composer_session(
        self, conn: sqlite3.Connection, db_path: str, composer_id: str, workspace_path: str | None
    ) -> Session:
        """Read a Cursor Composer session from cursorDiskKV table."""
        # Get composer metadata
        cursor = conn.execute(
            "SELECT value FROM cursorDiskKV WHERE key = ?",
            (f"composerData:{composer_id}",),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise ValueError(f"Composer session {composer_id} not found")

        data = json.loads(row[0])
        title = data.get("name")
        headers = data.get("fullConversationHeadersOnly", [])

        # Get actual message content from bubbles
        messages = []
        for header in headers:
            msg_type = header.get("type")
            bubble_id = header.get("bubbleId")

            if bubble_id:
                try:
                    bubble_cursor = conn.execute(
                        "SELECT value FROM cursorDiskKV WHERE key = ?",
                        (f"bubbleId:{composer_id}:{bubble_id}",),
                    )
                    bubble_row = bubble_cursor.fetchone()
                    if bubble_row:
                        bubble_data = json.loads(bubble_row[0])
                        content = bubble_data.get("text", "")

                        if content:
                            # type 1 = user, type 2 = assistant
                            role = MessageRole.USER if msg_type == 1 else MessageRole.ASSISTANT
                            messages.append(
                                Message(
                                    role=role,
                                    content=content,
                                    timestamp=datetime.now(),
                                )
                            )
                except Exception:
                    continue

        conn.close()

        # Get timestamps
        import os

        stat = os.stat(db_path)
        created_at = datetime.fromtimestamp(data.get("createdAt", stat.st_ctime * 1000) / 1000)
        updated_at = datetime.fromtimestamp(data.get("lastUpdatedAt", stat.st_mtime * 1000) / 1000)

        if workspace_path is None:
            workspace_path = "cursor-composer-global"

        return Session(
            id=composer_id,
            tool=self.tool_name,
            workspace_path=workspace_path,
            title=title,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata={"file_path": f"{db_path}#composer#{composer_id}"},
        )
