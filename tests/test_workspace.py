"""Tests for workspace detection and hashing."""

import hashlib
from pathlib import Path

from ai_session_bridge.core.workspace import (
    get_platform_config_dir,
    get_workspace_hash,
    normalize_workspace_path,
)


def test_workspace_hash():
    """Test workspace hash calculation."""
    workspace = "/Users/test/project"
    expected_hash = hashlib.md5(workspace.encode()).hexdigest()[:32]
    assert get_workspace_hash(workspace) == expected_hash


def test_workspace_hash_strips_trailing_slash():
    """Test that trailing slashes are stripped before hashing."""
    workspace1 = "/Users/test/project"
    workspace2 = "/Users/test/project/"
    assert get_workspace_hash(workspace1) == get_workspace_hash(workspace2)


def test_normalize_workspace_path(temp_workspace):
    """Test workspace path normalization."""
    normalized = normalize_workspace_path(str(temp_workspace))
    assert Path(normalized).is_absolute()
    assert Path(normalized).exists()


def test_normalize_relative_path(temp_workspace, monkeypatch):
    """Test normalizing relative paths."""
    monkeypatch.chdir(temp_workspace.parent)
    relative = temp_workspace.name
    normalized = normalize_workspace_path(relative)
    assert Path(normalized).is_absolute()
    assert Path(normalized) == temp_workspace


def test_get_platform_config_dir():
    """Test platform-specific config directory."""
    config_dir = get_platform_config_dir()
    assert config_dir.exists() or config_dir.parent.exists()
    assert isinstance(config_dir, Path)
