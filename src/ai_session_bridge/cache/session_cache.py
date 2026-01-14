"""Session caching for improved performance."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from ..core.session import SessionSummary


@dataclass
class CachedSession:
    """Cached session metadata."""

    session_id: str
    tool: str
    workspace_path: str
    file_path: str
    file_mtime: float  # File modification time
    parsed_at: float  # When we cached it
    summary: str
    message_count: int
    created_at: str  # ISO format
    updated_at: str  # ISO format


class SessionCache:
    """Cache for session metadata and content."""

    def __init__(self, cache_dir: Path):
        """
        Initialize session cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_dir / "sessions.json"
        self._index: dict[str, CachedSession] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file) as f:
                data = json.load(f)

            self._index = {key: CachedSession(**value) for key, value in data.items()}
        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
            self._index = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            data = {key: asdict(value) for key, value in self._index.items()}

            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def get_cached_summary(self, file_path: Path) -> SessionSummary | None:
        """
        Get cached session summary if still valid.

        Args:
            file_path: Path to session file

        Returns:
            Cached summary if valid, None otherwise
        """
        cache_key = str(file_path)

        if cache_key not in self._index:
            return None

        cached = self._index[cache_key]

        # Check if file has been modified
        try:
            current_mtime = file_path.stat().st_mtime
            if current_mtime != cached.file_mtime:
                # File modified, invalidate cache
                del self._index[cache_key]
                self._save_cache()
                return None
        except FileNotFoundError:
            # File deleted, remove from cache
            del self._index[cache_key]
            self._save_cache()
            return None

        # Cache is valid, return summary
        return SessionSummary(
            id=cached.session_id,
            tool=cached.tool,
            workspace_path=cached.workspace_path,
            created_at=datetime.fromisoformat(cached.created_at),
            updated_at=datetime.fromisoformat(cached.updated_at),
            message_count=cached.message_count,
            preview=cached.summary,
            file_path=cached.file_path,
        )

    def cache_summary(self, summary: SessionSummary) -> None:
        """
        Cache a session summary.

        Args:
            summary: Session summary to cache
        """
        file_path = Path(summary.file_path)
        cache_key = str(file_path)

        try:
            file_mtime = file_path.stat().st_mtime
        except FileNotFoundError:
            return

        cached = CachedSession(
            session_id=summary.id,
            tool=summary.tool,
            workspace_path=summary.workspace_path,
            file_path=str(file_path),
            file_mtime=file_mtime,
            parsed_at=datetime.now().timestamp(),
            summary=summary.preview,
            message_count=summary.message_count,
            created_at=summary.created_at.isoformat(),
            updated_at=summary.updated_at.isoformat(),
        )

        self._index[cache_key] = cached
        self._save_cache()

    def invalidate(self, file_path: Path) -> None:
        """
        Invalidate cached session.

        Args:
            file_path: Path to session file
        """
        cache_key = str(file_path)
        if cache_key in self._index:
            del self._index[cache_key]
            self._save_cache()

    def clear(self) -> None:
        """Clear all cached data."""
        self._index = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

    def clean_old_entries(self, max_age_days: int = 30) -> int:
        """
        Remove cached entries older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of entries removed
        """
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)

        to_remove = [key for key, cached in self._index.items() if cached.parsed_at < cutoff]

        for key in to_remove:
            del self._index[key]

        if to_remove:
            self._save_cache()

        return len(to_remove)
