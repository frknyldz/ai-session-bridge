"""Rovodev session reader."""

import json
from datetime import datetime
from pathlib import Path

from ..core.session import Message, MessageRole, Session, SessionSummary
from ..core.workspace import get_rovodev_sessions_dir
from .base import SessionReader


class RovodevReader(SessionReader):
    """Reader for Rovodev sessions."""

    def get_tool_name(self) -> str:
        """Get tool name."""
        return "rovodev"

    def get_sessions(self, workspace_path: str | None) -> list[SessionSummary]:
        """Get all Rovodev sessions for a workspace (or all if workspace_path is None)."""
        sessions_dir = get_rovodev_sessions_dir()
        if not sessions_dir.exists():
            return []

        summaries = []

        # Iterate through all session directories
        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # Check if this session belongs to the workspace
            session_workspace = self._get_session_workspace(session_dir)
            if not session_workspace:
                continue

            # Check if workspace matches (skip check if workspace_path is None)
            if workspace_path and not self._workspace_matches(workspace_path, session_workspace):
                continue

            # Read session summary
            try:
                summary = self._read_session_summary(session_dir, session_workspace)
                if summary:
                    summaries.append(summary)
            except Exception as e:
                print(f"Warning: Failed to read Rovodev session {session_dir}: {e}")

        # Sort by update time, newest first
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def read_session(self, session_path: Path) -> Session:
        """Read a full Rovodev session."""
        # session_path should be the session directory or session_context.json
        if session_path.is_dir():
            session_file = session_path / "session_context.json"
        else:
            session_file = session_path
            session_path = session_path.parent

        with open(session_file) as f:
            data = json.load(f)

        return self._parse_session(data, session_path)

    def _get_session_workspace(self, session_dir: Path) -> str | None:
        """Extract workspace path from Rovodev session metadata."""
        metadata_file = session_dir / "metadata.json"
        if not metadata_file.exists():
            return None

        try:
            import json

            metadata = json.load(open(metadata_file))
            return metadata.get("workspace_path")
        except Exception as e:
            print(f"Warning: Failed to read metadata from {session_dir}: {e}")
            return None

    def _workspace_matches(self, target_workspace: str, session_workspace: str) -> bool:
        """Check if workspace paths match exactly."""
        # Normalize both paths for exact comparison
        target = Path(target_workspace).resolve()
        session = Path(session_workspace).resolve()

        # Only exact matches
        return target == session

    def _read_session_summary(self, session_dir: Path, workspace_path: str) -> SessionSummary | None:
        """Read Rovodev session summary."""
        session_file = session_dir / "session_context.json"
        metadata_file = session_dir / "metadata.json"
        if not session_file.exists():
            return None

        try:
            with open(session_file) as f:
                data = json.load(f)

            # Read metadata for title
            title = None
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        title = metadata.get("title")
                except Exception:
                    pass

            session_id = session_dir.name  # UUID

            # Get timestamps from file
            stat = session_file.stat()
            created_at = datetime.fromtimestamp(stat.st_ctime)
            updated_at = datetime.fromtimestamp(stat.st_mtime)

            # Count messages
            messages = data.get("message_history", [])
            message_count = len(messages)

            # Get preview from first user message (skip system prompt at index 0)
            preview = ""
            for i, msg in enumerate(messages):
                if i == 0:  # Skip system prompt
                    continue
                # Rovodev messages have a parts array
                parts = msg.get("parts", [])
                for part in parts:
                    content = part.get("content", "")
                    # Skip empty or whitespace-only content, and ensure content is a string
                    if content and isinstance(content, str) and content.strip() and part.get("part_kind") == "text":
                        content_stripped = content.strip()
                        preview = content_stripped[:200] + "..." if len(content_stripped) > 200 else content_stripped
                        break
                if preview:
                    break

            return SessionSummary(
                id=session_id,
                tool="rovodev",
                workspace_path=workspace_path,
                created_at=created_at,
                updated_at=updated_at,
                message_count=message_count,
                preview=preview,
                file_path=str(session_file),
                title=title,
            )
        except Exception as e:
            print(f"Warning: Failed to read Rovodev summary from {session_dir}: {e}")
            return None

    def _parse_session(self, data: dict, session_dir: Path) -> Session:
        """Parse Rovodev session data."""
        session_id = session_dir.name

        # Get timestamps
        session_file = session_dir / "session_context.json"
        stat = session_file.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)

        # Parse messages
        messages = []
        for msg_data in data.get("message_history", []):
            # Rovodev uses "kind" field: "request" = user, "response" = assistant
            msg_kind = msg_data.get("kind", "request")

            # Rovodev messages have a "parts" array containing the actual content
            parts = msg_data.get("parts", [])
            content_parts = []
            latest_timestamp = None

            for part in parts:
                # Each part can have different types
                part_kind = part.get("part_kind")
                part_content = part.get("content", "")

                # Track the latest timestamp from parts
                part_timestamp = part.get("timestamp")
                if part_timestamp:
                    latest_timestamp = part_timestamp

                if part_kind in ("text", "user-prompt", "retry-prompt"):
                    # Only add non-empty content
                    if part_content and isinstance(part_content, str) and part_content.strip():
                        content_parts.append(part_content)
                elif part_kind == "system-prompt":
                    # Skip system prompts in output - they're too verbose
                    pass
                elif part_kind == "tool-call":
                    # Tool call representation - only show if we have a meaningful name
                    tool_name = part.get("tool_name", "") or part.get("name", "")
                    if tool_name and tool_name != "unknown":
                        content_parts.append(f"[Tool Call: {tool_name}]")
                elif part_kind in ("tool-result", "tool-return"):
                    # Tool result representation - skip for cleaner output
                    pass

            content = "\n\n".join(content_parts) if content_parts else ""

            # Skip messages with empty or whitespace-only content
            if not content or not content.strip():
                continue

            # Map kind to role
            if msg_kind == "request":
                msg_role = MessageRole.USER
            elif msg_kind == "response":
                msg_role = MessageRole.ASSISTANT
            else:
                msg_role = MessageRole.USER

            # Get timestamp from parts or fallback to file timestamp
            if latest_timestamp:
                try:
                    timestamp = datetime.fromisoformat(latest_timestamp.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    timestamp = updated_at
            else:
                timestamp = updated_at

            messages.append(
                Message(
                    role=msg_role,
                    content=content,
                    timestamp=timestamp,
                )
            )

        # Get workspace path
        workspace_path = self._get_session_workspace(session_dir) or "unknown"

        # Get title from metadata
        title = None
        try:
            metadata_file = session_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    title = metadata.get("title")
        except Exception:
            pass

        return Session(
            id=session_id,
            tool="rovodev",
            workspace_path=workspace_path,
            title=title,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata={
                "session_dir": str(session_dir),
                "file_path": str(session_file),
            },
        )
