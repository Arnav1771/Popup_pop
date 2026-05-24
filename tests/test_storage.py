"""Tests for storage and database operations."""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from cmdpop.storage.db import CommandDatabase, CommandRow
from cmdpop.history.base import HistoryEntry


@pytest.fixture
async def test_db():
    """Create a test database."""
    db_path = Path("/tmp/test_cmdpop.db")
    if db_path.exists():
        db_path.unlink()

    db = CommandDatabase(db_path)
    await db.init()
    yield db

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.mark.asyncio
async def test_upsert_single_command():
    """Test upserting a single command."""
    db = CommandDatabase(Path("/tmp/test_single.db"))
    await db.init()

    entry = HistoryEntry(
        command="git status",
        timestamp=datetime.now(),
        source_shell="bash",
        source_file=Path("~/.bash_history"),
    )

    await db.upsert_commands([entry])
    results = await db.get_all(limit=10)

    assert len(results) > 0
    assert any(r.command == "git status" for r in results)

    # Cleanup
    db.db_path.unlink()


@pytest.mark.asyncio
async def test_upsert_increments_run_count():
    """Test that upserting same command increments run_count."""
    db = CommandDatabase(Path("/tmp/test_run_count.db"))
    await db.init()

    entry = HistoryEntry(
        command="git status",
        timestamp=datetime.now(),
        source_shell="bash",
        source_file=Path("~/.bash_history"),
    )

    await db.upsert_commands([entry])
    results1 = await db.get_all(limit=10)
    count1 = next((r.run_count for r in results1 if r.command == "git status"), 0)

    await db.upsert_commands([entry])
    results2 = await db.get_all(limit=10)
    count2 = next((r.run_count for r in results2 if r.command == "git status"), 0)

    assert count2 > count1

    # Cleanup
    db.db_path.unlink()


@pytest.mark.asyncio
async def test_sensitive_commands_excluded():
    """Test that commands with sensitive keywords are excluded."""
    db = CommandDatabase(Path("/tmp/test_sensitive.db"))
    await db.init()

    entries = [
        HistoryEntry(
            command="git status",
            timestamp=datetime.now(),
            source_shell="bash",
            source_file=Path("test"),
        ),
        HistoryEntry(
            command="export PASSWORD=secret123",
            timestamp=datetime.now(),
            source_shell="bash",
            source_file=Path("test"),
        ),
    ]

    exclude_patterns = ["password", "token", "apikey"]
    await db.upsert_commands(entries, exclude_patterns)

    results = await db.get_all(limit=10)
    sensitive_found = any("password" in r.command.lower() for r in results)
    assert not sensitive_found

    # Cleanup
    db.db_path.unlink()


@pytest.mark.asyncio
async def test_search_returns_fuzzy_matches():
    """Test that search returns fuzzy matches."""
    db = CommandDatabase(Path("/tmp/test_search.db"))
    await db.init()

    entries = [
        HistoryEntry("git status", datetime.now(), "bash", Path("test")),
        HistoryEntry("git log", datetime.now(), "bash", Path("test")),
        HistoryEntry("git commit", datetime.now(), "bash", Path("test")),
        HistoryEntry("ls -la", datetime.now(), "bash", Path("test")),
    ]

    await db.upsert_commands(entries)

    results = await db.search("git", limit=10)
    assert len(results) >= 3
    assert all("git" in r.command for r in results)

    # Cleanup
    db.db_path.unlink()


@pytest.mark.asyncio
async def test_toggle_favorite():
    """Test toggling favorite status."""
    db = CommandDatabase(Path("/tmp/test_favorite.db"))
    await db.init()

    entry = HistoryEntry("git status", datetime.now(), "bash", Path("test"))
    await db.upsert_commands([entry])

    # Toggle to favorite
    is_fav = await db.toggle_favorite("git status")
    assert is_fav is True

    # Toggle back to not favorite
    is_fav = await db.toggle_favorite("git status")
    assert is_fav is False

    # Cleanup
    db.db_path.unlink()


@pytest.mark.asyncio
async def test_delete_command():
    """Test deleting a command."""
    db = CommandDatabase(Path("/tmp/test_delete.db"))
    await db.init()

    entry = HistoryEntry("git status", datetime.now(), "bash", Path("test"))
    await db.upsert_commands([entry])

    results_before = await db.get_all(limit=10)
    assert any(r.command == "git status" for r in results_before)

    await db.delete_command("git status")

    results_after = await db.get_all(limit=10)
    assert not any(r.command == "git status" for r in results_after)

    # Cleanup
    db.db_path.unlink()
