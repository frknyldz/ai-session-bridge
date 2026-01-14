"""Workspace detection and hash calculation."""

import hashlib
import json
import platform
from pathlib import Path
from urllib.parse import unquote, urlparse


def get_workspace_hash(workspace_path: str) -> str:
    """
    Calculate VS Code/Cursor workspace storage hash.

    VS Code uses MD5 hash of the normalized workspace path.

    Args:
        workspace_path: Absolute path to workspace

    Returns:
        32-character MD5 hash
    """
    normalized = workspace_path.rstrip("/")
    return hashlib.md5(normalized.encode()).hexdigest()[:32]


def get_current_workspace() -> str:
    """
    Get current workspace path.

    Returns:
        Absolute path to current working directory
    """
    return str(Path.cwd().resolve())


def normalize_workspace_path(path: str) -> str:
    """
    Normalize workspace path for comparison.

    Args:
        path: Workspace path (can be relative)

    Returns:
        Absolute, normalized path
    """
    return str(Path(path).expanduser().resolve())


def get_platform_config_dir() -> Path:
    """
    Get platform-specific configuration directory.

    Returns:
        Path to config directory:
        - macOS: ~/Library/Application Support/
        - Linux: ~/.config/
        - Windows: %APPDATA%
    """
    system = platform.system()
    home = Path.home()

    if system == "Darwin":  # macOS
        return home / "Library" / "Application Support"
    elif system == "Linux":
        return home / ".config"
    elif system == "Windows":
        import os

        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata)
        return home / "AppData" / "Roaming"
    else:
        # Fallback
        return home / ".config"


def get_vscode_storage_dir() -> Path:
    """Get VS Code workspace storage directory."""
    return get_platform_config_dir() / "Code" / "User" / "workspaceStorage"


def get_cursor_storage_dir() -> Path:
    """Get Cursor workspace storage directory."""
    return get_platform_config_dir() / "Cursor" / "User" / "workspaceStorage"


def get_rovodev_sessions_dir() -> Path:
    """Get Rovodev sessions directory."""
    return Path.home() / ".rovodev" / "sessions"


def find_workspace_session_dir(workspace_path: str, storage_dir: Path, use_hash: bool = True) -> Path | None:
    """
    Find the session directory for a workspace.

    For VS Code/Cursor, scans all workspace directories and reads workspace.json
    to find the matching workspace path.

    Args:
        workspace_path: Workspace absolute path
        storage_dir: Base storage directory (e.g., VS Code workspaceStorage)
        use_hash: Whether to scan workspace.json files (True for VS Code/Cursor)

    Returns:
        Path to session directory if found, None otherwise
    """
    if not storage_dir.exists():
        return None

    if use_hash:
        # Scan all workspace directories and read workspace.json files
        normalized_target = normalize_workspace_path(workspace_path)

        for workspace_dir in storage_dir.iterdir():
            if not workspace_dir.is_dir():
                continue

            workspace_json = workspace_dir / "workspace.json"
            if not workspace_json.exists():
                continue

            try:
                with open(workspace_json) as f:
                    data = json.load(f)

                # Extract folder path from workspace.json
                folder_uri = data.get("folder")
                if folder_uri:
                    # Parse file:// URI to get path
                    parsed = urlparse(folder_uri)
                    if parsed.scheme == "file":
                        folder_path = unquote(parsed.path)
                        # Normalize and compare
                        normalized_folder = normalize_workspace_path(folder_path)
                        if normalized_folder == normalized_target:
                            return workspace_dir
            except Exception:
                # Skip invalid workspace.json files
                continue

        return None

    # Direct path lookup
    return storage_dir if storage_dir.exists() else None
