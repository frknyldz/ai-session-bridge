"""Configuration loading and management."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .filter import DEFAULT_FILTER_PATTERNS, FilterConfig


@dataclass
class ToolsConfig:
    """Configuration for which tools to read from."""

    copilot: bool = True
    cursor: bool = True
    rovodev: bool = True
    continue_dev: bool = False  # Disabled by default


@dataclass
class CacheConfig:
    """Cache configuration."""

    enabled: bool = True
    directory: str | None = None  # None means use default
    max_age_days: int = 30


@dataclass
class SearchConfig:
    """Search configuration."""

    enabled: bool = True
    use_fts: bool = True  # Use SQLite FTS5


@dataclass
class MCPConfig:
    """MCP server configuration."""

    max_context_messages: int = 50
    max_context_sessions: int = 5


@dataclass
class ScopeConfig:
    """Scope configuration for which workspaces to include."""

    mode: str = "current_workspace"  # current_workspace, all_workspaces, specified
    workspaces: list[str] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration."""

    scope: ScopeConfig = field(default_factory=ScopeConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    filtering: FilterConfig = field(default_factory=FilterConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)

    def get_cache_dir(self) -> Path:
        """Get cache directory path."""
        if self.cache.directory:
            return Path(self.cache.directory).expanduser()
        return Path.home() / ".cache" / "ai-session-bridge"


def get_default_config() -> Config:
    """Get default configuration."""
    return Config()


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> Config:
    """
    Load configuration from files.

    Looks for config in:
    1. ~/.config/ai-session-bridge/config.yaml
    2. ./.ai-session-bridge.yaml (workspace override)

    Returns:
        Merged configuration
    """
    config_paths = [
        Path.home() / ".config" / "ai-session-bridge" / "config.yaml",
        Path.cwd() / ".ai-session-bridge.yaml",
    ]

    # Start with defaults
    config_dict = _config_to_dict(get_default_config())

    # Merge configs from files
    for path in config_paths:
        if path.exists():
            try:
                with open(path) as f:
                    override = yaml.safe_load(f) or {}
                    config_dict = deep_merge(config_dict, override)
            except Exception as e:
                print(f"Warning: Failed to load config from {path}: {e}")

    return _dict_to_config(config_dict)


def _config_to_dict(config: Config) -> dict:
    """Convert Config to dictionary."""
    return {
        "scope": {
            "mode": config.scope.mode,
            "workspaces": config.scope.workspaces,
        },
        "tools": {
            "copilot": config.tools.copilot,
            "cursor": config.tools.cursor,
            "rovodev": config.tools.rovodev,
            "continue": config.tools.continue_dev,
        },
        "cache": {
            "enabled": config.cache.enabled,
            "directory": config.cache.directory,
            "max_age_days": config.cache.max_age_days,
        },
        "search": {
            "enabled": config.search.enabled,
            "use_fts": config.search.use_fts,
        },
        "filtering": {
            "enabled": config.filtering.enabled,
            "patterns": config.filtering.patterns or [],
            "replacement": config.filtering.replacement,
        },
        "mcp": {
            "max_context_messages": config.mcp.max_context_messages,
            "max_context_sessions": config.mcp.max_context_sessions,
        },
    }


def _dict_to_config(data: dict) -> Config:
    """Convert dictionary to Config."""
    scope = data.get("scope", {})
    tools = data.get("tools", {})
    cache = data.get("cache", {})
    search = data.get("search", {})
    filtering = data.get("filtering", {})
    mcp = data.get("mcp", {})

    return Config(
        scope=ScopeConfig(
            mode=scope.get("mode", "current_workspace"),
            workspaces=scope.get("workspaces", []),
        ),
        tools=ToolsConfig(
            copilot=tools.get("copilot", True),
            cursor=tools.get("cursor", True),
            rovodev=tools.get("rovodev", True),
            continue_dev=tools.get("continue", False),
        ),
        cache=CacheConfig(
            enabled=cache.get("enabled", True),
            directory=cache.get("directory"),
            max_age_days=cache.get("max_age_days", 30),
        ),
        search=SearchConfig(
            enabled=search.get("enabled", True),
            use_fts=search.get("use_fts", True),
        ),
        filtering=FilterConfig(
            enabled=filtering.get("enabled", True),
            patterns=filtering.get("patterns") or DEFAULT_FILTER_PATTERNS.copy(),
            replacement=filtering.get("replacement", "[REDACTED]"),
        ),
        mcp=MCPConfig(
            max_context_messages=mcp.get("max_context_messages", 50),
            max_context_sessions=mcp.get("max_context_sessions", 5),
        ),
    )
