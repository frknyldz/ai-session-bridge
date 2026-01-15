"""Search index using SQLite FTS5."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..core.session import Session


@dataclass
class SearchResult:
    """A search result."""

    session_id: str
    tool: str
    workspace_path: str
    role: str
    content: str
    timestamp: datetime
    session_title: str | None = None
    relevance: float = 0.0


class SearchIndex:
    """Full-text search index using SQLite FTS5."""

    def __init__(self, cache_dir: Path):
        """
        Initialize search index.

        Args:
            cache_dir: Directory to store index database
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "search.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database and FTS5 table."""
        conn = sqlite3.connect(self.db_path)

        # Create FTS5 virtual table
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages USING fts5(
                session_id,
                tool,
                workspace,
                role,
                content,
                timestamp,
                session_title,
                tokenize = 'porter unicode61'
            )
        """)

        # Create metadata table for tracking indexed sessions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indexed_sessions (
                session_id TEXT PRIMARY KEY,
                tool TEXT,
                workspace TEXT,
                file_path TEXT,
                file_mtime REAL,
                indexed_at REAL
            )
        """)

        conn.commit()
        conn.close()

    def is_indexed(self, session: Session, file_path: Path) -> bool:
        """
        Check if a session is already indexed and up-to-date.

        Args:
            session: Session to check
            file_path: Path to session file

        Returns:
            True if indexed and current, False otherwise
        """
        try:
            current_mtime = file_path.stat().st_mtime
        except (FileNotFoundError, OSError):
            # For special paths or demo data, always re-index
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT file_mtime FROM indexed_sessions WHERE session_id = ? AND tool = ?", (session.id, session.tool)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return False

        cached_mtime = row[0]
        return current_mtime == cached_mtime

    def index_session(self, session: Session, file_path: Path) -> None:
        """
        Index a session for full-text search.

        Args:
            session: Session to index
            file_path: Path to session file
        """
        conn = sqlite3.connect(self.db_path)

        try:
            # Remove old entries for this session
            conn.execute("DELETE FROM messages WHERE session_id = ? AND tool = ?", (session.id, session.tool))

            # Index all messages with non-empty content
            for msg in session.messages:
                # Skip empty or whitespace-only messages
                if not msg.content or not msg.content.strip():
                    continue

                conn.execute(
                    "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        session.id,
                        session.tool,
                        session.workspace_path,
                        msg.role.value,
                        msg.content,
                        msg.timestamp.isoformat(),
                        session.title or "",
                    ),
                )

            # Update indexed_sessions metadata
            try:
                file_mtime = file_path.stat().st_mtime
            except (FileNotFoundError, OSError):
                # Use current time if file doesn't exist (e.g., for demo data or special paths)
                file_mtime = datetime.now().timestamp()

            conn.execute(
                """
                INSERT OR REPLACE INTO indexed_sessions
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.tool,
                    session.workspace_path,
                    str(file_path),
                    file_mtime,
                    datetime.now().timestamp(),
                ),
            )

            conn.commit()
        finally:
            conn.close()

    def search(
        self, query: str, workspace: str | None = None, tool: str | None = None, limit: int = 20
    ) -> list[SearchResult]:
        """
        Search across indexed sessions.

        Args:
            query: Search query
            workspace: Optional workspace filter
            tool: Optional tool filter
            limit: Maximum results to return

        Returns:
            List of search results
        """
        conn = sqlite3.connect(self.db_path)

        # Build query
        sql = "SELECT session_id, tool, workspace, role, content, timestamp, session_title, rank FROM messages"
        params = [query]

        where_clauses = ["messages MATCH ?"]

        if workspace:
            where_clauses.append("workspace = ?")
            params.append(workspace)

        if tool:
            where_clauses.append("tool = ?")
            params.append(tool)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            session_id, tool_name, workspace_path, role, content, timestamp_str, session_title, rank = row

            results.append(
                SearchResult(
                    session_id=session_id,
                    tool=tool_name,
                    workspace_path=workspace_path,
                    role=role,
                    content=content,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    session_title=session_title if session_title else None,
                    relevance=-rank,
                )
            )

        return results

    def clear(self) -> None:
        """Clear all indexed data."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM indexed_sessions")
        conn.commit()
        conn.close()

    def remove_session(self, session_id: str, tool: str) -> None:
        """
        Remove a session from the index.

        Args:
            session_id: Session ID
            tool: Tool name
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM messages WHERE session_id = ? AND tool = ?", (session_id, tool))
        conn.execute("DELETE FROM indexed_sessions WHERE session_id = ? AND tool = ?", (session_id, tool))
        conn.commit()
        conn.close()
