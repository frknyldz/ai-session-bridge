"""Copilot session reader (also works for Cursor)."""

import json
from datetime import datetime
from pathlib import Path

from ..core.session import Message, MessageRole, Session, SessionSummary, ToolCall
from ..core.workspace import find_workspace_session_dir
from .base import SessionReader


class CopilotReader(SessionReader):
    """Reader for VS Code Copilot sessions (copilot_v3 format)."""

    def __init__(self, storage_dir: Path):
        """
        Initialize Copilot reader.

        Args:
            storage_dir: VS Code or Cursor workspaceStorage directory
        """
        self.storage_dir = storage_dir
        self.tool_name = "copilot"

    def get_tool_name(self) -> str:
        """Get tool name."""
        return self.tool_name

    def get_sessions(self, workspace_path: str | None) -> list[SessionSummary]:
        """Get all Copilot sessions for a workspace (or all if workspace_path is None)."""
        if workspace_path:
            # Get sessions for specific workspace
            sessions_dir = self._get_sessions_dir(workspace_path)
            if not sessions_dir or not sessions_dir.exists():
                return []

            summaries = []
            for session_file in sessions_dir.glob("*.json"):
                try:
                    summary = self._read_session_summary(session_file, workspace_path)
                    if summary:
                        summaries.append(summary)
                except Exception as e:
                    print(f"Warning: Failed to read {session_file}: {e}")
        else:
            # Get sessions from all workspaces
            summaries = []
            for workspace_dir in self.storage_dir.glob("*/chatSessions"):
                if not workspace_dir.exists():
                    continue
                for session_file in workspace_dir.glob("*.json"):
                    try:
                        # Try to get real workspace path from workspace.json
                        workspace_json = workspace_dir.parent / "workspace.json"
                        if workspace_json.exists():
                            try:
                                import json
                                from urllib.parse import unquote, urlparse

                                with open(workspace_json) as f:
                                    workspace_data = json.load(f)
                                folder_uri = workspace_data.get("folder")
                                if folder_uri:
                                    parsed = urlparse(folder_uri)
                                    if parsed.scheme == "file":
                                        ws_path = unquote(parsed.path)
                                    else:
                                        ws_path = f"workspace-{workspace_dir.parent.name}"
                                else:
                                    ws_path = f"workspace-{workspace_dir.parent.name}"
                            except Exception:
                                ws_path = f"workspace-{workspace_dir.parent.name}"
                        else:
                            ws_path = f"workspace-{workspace_dir.parent.name}"
                        summary = self._read_session_summary(session_file, ws_path)
                        if summary:
                            summaries.append(summary)
                    except Exception as e:
                        print(f"Warning: Failed to read {session_file}: {e}")

        # Sort by update time, newest first
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def read_session(self, session_path: Path, workspace_path: str | None = None) -> Session:
        """Read a full Copilot session."""
        with open(session_path) as f:
            data = json.load(f)

        return self._parse_session(data, session_path, workspace_path)

    def _get_sessions_dir(self, workspace_path: str) -> Path | None:
        """Get the chatSessions directory for a workspace."""
        # Use find_workspace_session_dir to scan workspace.json files
        workspace_dir = find_workspace_session_dir(workspace_path, self.storage_dir, use_hash=True)

        if not workspace_dir:
            return None

        # Look for chatSessions directory
        chat_sessions = workspace_dir / "chatSessions"
        return chat_sessions if chat_sessions.exists() else None

    def _read_session_summary(self, session_file: Path, workspace_path: str) -> SessionSummary | None:
        """Read session summary without parsing all messages."""
        try:
            with open(session_file) as f:
                data = json.load(f)

            session_id = data.get("sessionId") or session_file.stem
            title = data.get("customTitle")

            # Get timestamps - version 3 doesn't have top-level timestamps
            # We'll extract from first/last request
            requests = data.get("requests", [])
            if not requests:
                return None

            # Use file modification time as fallback
            import os

            stat = os.stat(session_file)
            created_at = datetime.fromtimestamp(stat.st_ctime)
            updated_at = datetime.fromtimestamp(stat.st_mtime)

            # Count messages (requests and responses)
            message_count = 0
            for req in requests:
                message_count += 1  # User message
                response = req.get("response", [])
                if response:
                    message_count += 1  # Assistant response

            # Get preview from first user request
            preview = ""
            if requests:
                first_request = requests[0]
                message = first_request.get("message", {})
                text = message.get("text", "")
                if text:
                    preview = text[:200] + "..." if len(text) > 200 else text

            return SessionSummary(
                id=session_id,
                tool=self.tool_name,
                workspace_path=workspace_path,
                created_at=created_at,
                updated_at=updated_at,
                message_count=message_count,
                preview=preview,
                file_path=str(session_file),
                title=title,
            )
        except Exception as e:
            print(f"Warning: Failed to read summary from {session_file}: {e}")
            return None

    def _parse_session(self, data: dict, session_path: Path, workspace_path: str | None = None) -> Session:
        """Parse Copilot session data (version 3 format)."""
        session_id = data.get("sessionId") or session_path.stem

        # Use file timestamps as fallback
        import os

        stat = os.stat(session_path)
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)

        messages = []
        requests = data.get("requests", [])

        for req in requests:
            # User message
            message = req.get("message", {})
            text = message.get("text", "")
            if text:
                messages.append(
                    Message(
                        role=MessageRole.USER,
                        content=text,
                        timestamp=created_at,  # We don't have per-message timestamps in v3
                    )
                )

            # Assistant response
            response = req.get("response", [])
            if response:
                # Collect all text responses
                response_parts = []
                for part in response:
                    kind = part.get("kind", "")
                    if kind == "text":
                        response_parts.append(part.get("value", ""))
                    elif kind == "thinking":
                        # Include thinking as part of response
                        thinking = part.get("value", "")
                        if thinking:
                            response_parts.append(f"[Thinking: {thinking}]")
                    elif kind == "toolCall":
                        # Tool call
                        tool_name = part.get("toolName", "unknown")
                        tool_input = part.get("input", {})
                        response_parts.append(f"[Tool Call: {tool_name}({tool_input})]")

                if response_parts:
                    messages.append(
                        Message(
                            role=MessageRole.ASSISTANT,
                            content="\n".join(response_parts),
                            timestamp=updated_at,
                        )
                    )

        # Use provided workspace path or extract from file location
        if workspace_path is None:
            workspace_path = self._extract_workspace_path(session_path)

        return Session(
            id=session_id,
            tool=self.tool_name,
            workspace_path=workspace_path,
            title=data.get("customTitle"),
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata={"file_path": str(session_path), "version": data.get("version")},
        )

    def _parse_tool_calls(self, chat: dict) -> list[ToolCall] | None:
        """Parse tool calls from chat data."""
        # Copilot may have function calls in the response
        # This is a simplified parser - adjust based on actual format
        commands = chat.get("commands", [])
        if not commands:
            return None

        tool_calls = []
        for cmd in commands:
            tool_calls.append(
                ToolCall(
                    name=cmd.get("name", "unknown"),
                    arguments=json.dumps(cmd.get("arguments", {})),
                    id=cmd.get("id"),
                )
            )

        return tool_calls if tool_calls else None

    def _format_reference(self, ref: dict) -> str:
        """Format a reference (tool result) for display."""
        ref_type = ref.get("type", "")

        if ref_type == "file":
            file_path = ref.get("path", "")
            return f"Referenced file: {file_path}"
        elif ref_type == "symbol":
            symbol = ref.get("symbol", "")
            return f"Referenced symbol: {symbol}"
        else:
            # Generic reference
            return json.dumps(ref, indent=2)

    def _parse_timestamp(self, timestamp: str | None) -> datetime:
        """Parse ISO timestamp or return current time."""
        if not timestamp:
            return datetime.now()

        try:
            # Handle various ISO formats
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            return datetime.fromisoformat(timestamp)
        except Exception:
            return datetime.now()

    def _extract_workspace_path(self, session_path: Path) -> str:
        """Extract workspace path from session file location."""
        # Session path: .../workspaceStorage/{hash}/chatSessions/session.json
        # We need to work backwards to find the workspace
        try:
            workspace_hash = session_path.parent.parent.name
            # We have the hash but not the original path
            # For now, return a placeholder
            return f"workspace-{workspace_hash}"
        except Exception:
            return "unknown"
