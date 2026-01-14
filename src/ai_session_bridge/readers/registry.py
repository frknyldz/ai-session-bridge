"""Reader registry for managing session readers."""

from ..core.workspace import (
    get_cursor_storage_dir,
    get_rovodev_sessions_dir,
    get_vscode_storage_dir,
)
from .base import SessionReader
from .copilot import CopilotReader
from .cursor import CursorReader
from .rovodev import RovodevReader


class ReaderRegistry:
    """Registry of all session readers."""

    def __init__(self):
        """Initialize reader registry."""
        self._readers: dict[str, SessionReader] = {}
        self._initialize_readers()

    def _initialize_readers(self) -> None:
        """Initialize all available readers."""
        # VS Code Copilot
        vscode_storage = get_vscode_storage_dir()
        if vscode_storage.exists():
            self._readers["copilot"] = CopilotReader(vscode_storage)

        # Cursor
        cursor_storage = get_cursor_storage_dir()
        if cursor_storage.exists():
            self._readers["cursor"] = CursorReader(cursor_storage)

        # Rovodev
        rovodev_sessions = get_rovodev_sessions_dir()
        if rovodev_sessions.exists():
            self._readers["rovodev"] = RovodevReader()

    def get_reader(self, tool: str) -> SessionReader | None:
        """
        Get a reader by tool name.

        Args:
            tool: Tool name (copilot, cursor, rovodev)

        Returns:
            Reader instance or None if not available
        """
        return self._readers.get(tool)

    def get_all_readers(self) -> dict[str, SessionReader]:
        """Get all available readers."""
        return self._readers.copy()

    def list_tools(self) -> list[str]:
        """Get list of available tool names."""
        return list(self._readers.keys())


# Global registry instance
_registry: ReaderRegistry | None = None


def get_registry() -> ReaderRegistry:
    """Get the global reader registry."""
    global _registry
    if _registry is None:
        _registry = ReaderRegistry()
    return _registry
