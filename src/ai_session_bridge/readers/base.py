"""Base reader interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from ..core.session import Session, SessionSummary


class SessionReader(ABC):
    """Abstract base class for session readers."""

    @abstractmethod
    def get_sessions(self, workspace_path: str) -> list[SessionSummary]:
        """
        Get all sessions for a workspace.

        Args:
            workspace_path: Absolute path to workspace

        Returns:
            List of session summaries
        """
        pass

    @abstractmethod
    def read_session(self, session_path: Path) -> Session:
        """
        Read a full session from a file.

        Args:
            session_path: Path to session file

        Returns:
            Complete session with messages
        """
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """
        Get the name of the tool this reader is for.

        Returns:
            Tool name (e.g., "copilot", "rovodev")
        """
        pass

    def find_session_by_id(self, session_id: str, workspace_path: str) -> Path | None:
        """
        Find a session file by ID.

        Args:
            session_id: Session identifier
            workspace_path: Workspace path

        Returns:
            Path to session file if found, None otherwise
        """
        sessions = self.get_sessions(workspace_path)
        for summary in sessions:
            if summary.id == session_id:
                return Path(summary.file_path)
        return None
