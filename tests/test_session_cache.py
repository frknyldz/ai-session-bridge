"""Tests for session cache functionality."""

from datetime import datetime, timedelta

import pytest

from ai_session_bridge.cache.session_cache import CachedSession, SessionCache
from ai_session_bridge.core.session import SessionSummary


@pytest.fixture
def cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture
def sample_session_file(tmp_path):
    """Create a sample session file."""
    session_file = tmp_path / "session.json"
    session_file.write_text('{"test": "data"}')
    return session_file


@pytest.fixture
def sample_summary(sample_session_file):
    """Create a sample session summary."""
    return SessionSummary(
        id="test-session-123",
        tool="cursor",
        workspace_path="/test/workspace",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        message_count=5,
        preview="Test preview message",
        file_path=str(sample_session_file),
    )


def test_session_cache_init(cache_dir):
    """Test session cache initialization."""
    cache = SessionCache(cache_dir)
    assert cache.cache_dir == cache_dir
    assert cache.cache_file == cache_dir / "sessions.json"
    assert cache._index == {}


def test_session_cache_cache_summary(cache_dir, sample_summary, sample_session_file):
    """Test caching a session summary."""
    cache = SessionCache(cache_dir)
    cache.cache_summary(sample_summary)

    assert str(sample_session_file) in cache._index
    cached = cache._index[str(sample_session_file)]
    assert cached.session_id == "test-session-123"
    assert cached.tool == "cursor"
    assert cached.message_count == 5


def test_session_cache_get_cached_summary(cache_dir, sample_summary, sample_session_file):
    """Test retrieving a cached session summary."""
    cache = SessionCache(cache_dir)
    cache.cache_summary(sample_summary)

    # Retrieve the cached summary
    retrieved = cache.get_cached_summary(sample_session_file)
    assert retrieved is not None
    assert retrieved.id == "test-session-123"
    assert retrieved.tool == "cursor"
    assert retrieved.preview == "Test preview message"


def test_session_cache_get_cached_summary_not_found(cache_dir, tmp_path):
    """Test retrieving a non-existent cached summary."""
    cache = SessionCache(cache_dir)
    non_existent = tmp_path / "nonexistent.json"

    retrieved = cache.get_cached_summary(non_existent)
    assert retrieved is None


def test_session_cache_invalidate_on_file_modified(cache_dir, sample_summary, sample_session_file):
    """Test cache invalidation when file is modified."""
    cache = SessionCache(cache_dir)
    cache.cache_summary(sample_summary)

    # Modify the file
    import time

    time.sleep(0.1)  # Ensure different mtime
    sample_session_file.write_text('{"test": "modified"}')

    # Should return None since file was modified
    retrieved = cache.get_cached_summary(sample_session_file)
    assert retrieved is None


def test_session_cache_invalidate_on_file_deleted(cache_dir, sample_summary, sample_session_file):
    """Test cache invalidation when file is deleted."""
    cache = SessionCache(cache_dir)
    cache.cache_summary(sample_summary)

    # Delete the file
    sample_session_file.unlink()

    # Should return None since file was deleted
    retrieved = cache.get_cached_summary(sample_session_file)
    assert retrieved is None


def test_session_cache_invalidate(cache_dir, sample_summary, sample_session_file):
    """Test manual cache invalidation."""
    cache = SessionCache(cache_dir)
    cache.cache_summary(sample_summary)

    # Manually invalidate
    cache.invalidate(sample_session_file)

    assert str(sample_session_file) not in cache._index


def test_session_cache_clear(cache_dir, sample_summary):
    """Test clearing the cache."""
    cache = SessionCache(cache_dir)
    cache.cache_summary(sample_summary)

    # Clear all cache
    cache.clear()

    assert cache._index == {}
    assert not cache.cache_file.exists()


def test_session_cache_persistence(cache_dir, sample_summary, sample_session_file):
    """Test cache persistence across instances."""
    # Create cache and save
    cache1 = SessionCache(cache_dir)
    cache1.cache_summary(sample_summary)

    # Create new instance and verify it loads
    cache2 = SessionCache(cache_dir)
    assert str(sample_session_file) in cache2._index
    cached = cache2._index[str(sample_session_file)]
    assert cached.session_id == "test-session-123"


def test_session_cache_clean_old_entries(cache_dir, sample_session_file):
    """Test cleaning old cache entries."""
    cache = SessionCache(cache_dir)

    # Manually create an old entry
    old_cached = CachedSession(
        session_id="old-session",
        tool="cursor",
        workspace_path="/test",
        file_path=str(sample_session_file),
        file_mtime=sample_session_file.stat().st_mtime,
        parsed_at=(datetime.now() - timedelta(days=60)).timestamp(),  # 60 days old
        summary="Old summary",
        message_count=1,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
    cache._index[str(sample_session_file)] = old_cached
    cache._save_cache()

    # Clean entries older than 30 days
    removed = cache.clean_old_entries(max_age_days=30)

    assert removed == 1
    assert str(sample_session_file) not in cache._index


def test_session_cache_clean_old_entries_keeps_recent(cache_dir, sample_summary, sample_session_file):
    """Test that clean_old_entries keeps recent entries."""
    cache = SessionCache(cache_dir)
    cache.cache_summary(sample_summary)

    # Clean entries older than 30 days (should keep recent)
    removed = cache.clean_old_entries(max_age_days=30)

    assert removed == 0
    assert str(sample_session_file) in cache._index


def test_session_cache_load_corrupted_cache(cache_dir):
    """Test loading a corrupted cache file."""
    # Write corrupted JSON
    cache_file = cache_dir / "sessions.json"
    cache_file.write_text("{invalid json")

    # Should handle gracefully
    cache = SessionCache(cache_dir)
    assert cache._index == {}


def test_session_cache_cache_summary_missing_file(cache_dir, tmp_path):
    """Test caching a summary for a non-existent file."""
    cache = SessionCache(cache_dir)

    summary = SessionSummary(
        id="test-session",
        tool="cursor",
        workspace_path="/test",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        message_count=1,
        preview="Test",
        file_path=str(tmp_path / "nonexistent.json"),
    )

    # Should not raise, just skip caching
    cache.cache_summary(summary)
    assert str(tmp_path / "nonexistent.json") not in cache._index


def test_cached_session_dataclass():
    """Test CachedSession dataclass."""
    cached = CachedSession(
        session_id="test-123",
        tool="cursor",
        workspace_path="/test/path",
        file_path="/test/file.json",
        file_mtime=1234567890.0,
        parsed_at=1234567891.0,
        summary="Test summary",
        message_count=10,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T01:00:00",
    )

    assert cached.session_id == "test-123"
    assert cached.tool == "cursor"
    assert cached.message_count == 10
