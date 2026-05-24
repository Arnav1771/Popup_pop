"""SQLite-based command history storage."""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiosqlite
from rapidfuzz import fuzz

from cmdpop.history.base import HistoryEntry

logger = logging.getLogger(__name__)


@dataclass
class CommandRow:
    """A command row from the database."""

    id: int
    command: str
    source_shell: str | None
    first_seen: datetime | None
    last_seen: datetime | None
    run_count: int
    is_favorite: bool


class CommandDatabase:
    """SQLite database for command history."""

    def __init__(self, db_path: Path | None = None):
        """Initialize the database.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.cmdpop/history.db
        """
        if db_path is None:
            db_path = Path.home() / ".cmdpop" / "history.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    source_shell TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    run_count INTEGER DEFAULT 1,
                    is_favorite INTEGER DEFAULT 0
                )
                """
            )
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_commands_text ON commands(command)"
            )
            await db.commit()

    async def upsert_commands(
        self, entries: list[HistoryEntry], exclude_patterns: list[str] | None = None
    ) -> None:
        """Insert or update commands in the database.
        
        Args:
            entries: List of history entries to upsert.
            exclude_patterns: List of patterns to exclude from storage (case-insensitive).
        """
        if exclude_patterns is None:
            exclude_patterns = []

        async with aiosqlite.connect(self.db_path) as db:
            for entry in entries:
                # Check if command matches any exclude pattern
                command_lower = entry.command.lower()
                if any(
                    pattern.lower() in command_lower for pattern in exclude_patterns
                ):
                    continue

                try:
                    # Try to update first
                    cursor = await db.execute(
                        """
                        UPDATE commands
                        SET run_count = run_count + 1, last_seen = CURRENT_TIMESTAMP
                        WHERE command = ?
                        """,
                        (entry.command,),
                    )

                    if cursor.rowcount == 0:
                        # Insert new command
                        await db.execute(
                            """
                            INSERT INTO commands (command, source_shell, run_count)
                            VALUES (?, ?, 1)
                            """,
                            (entry.command, entry.source_shell),
                        )
                except sqlite3.IntegrityError:
                    # Command already exists, update it
                    await db.execute(
                        """
                        UPDATE commands
                        SET run_count = run_count + 1, last_seen = CURRENT_TIMESTAMP
                        WHERE command = ?
                        """,
                        (entry.command,),
                    )

            await db.commit()

    async def search(self, query: str, limit: int = 100) -> list[CommandRow]:
        """Fuzzy search commands.
        
        Args:
            query: Search query string.
            limit: Maximum number of results to return.
            
        Returns:
            List of matching commands, scored and sorted by relevance.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, command, source_shell, first_seen, last_seen, run_count, is_favorite
                FROM commands
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (limit * 5,),  # Get more to filter
            )
            rows = await cursor.fetchall()

        if not query:
            return [
                CommandRow(
                    id=row["id"],
                    command=row["command"],
                    source_shell=row["source_shell"],
                    first_seen=datetime.fromisoformat(row["first_seen"])
                    if row["first_seen"]
                    else None,
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    run_count=row["run_count"],
                    is_favorite=bool(row["is_favorite"]),
                )
                for row in rows[:limit]
            ]

        # Score each command
        scored = []
        for row in rows:
            score = fuzz.token_sort_ratio(query.lower(), row["command"].lower())
            if score > 30:  # Minimum score threshold
                scored.append((score, row))

        # Sort by score descending, then by last_seen
        scored.sort(key=lambda x: (-x[0], x[1]["last_seen"]), reverse=False)

        results = []
        for _, row in scored[:limit]:
            results.append(
                CommandRow(
                    id=row["id"],
                    command=row["command"],
                    source_shell=row["source_shell"],
                    first_seen=datetime.fromisoformat(row["first_seen"])
                    if row["first_seen"]
                    else None,
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    run_count=row["run_count"],
                    is_favorite=bool(row["is_favorite"]),
                )
            )

        return results

    async def toggle_favorite(self, command: str) -> bool:
        """Toggle favorite status of a command.
        
        Args:
            command: The command to toggle.
            
        Returns:
            New favorite state (True if now favorited, False otherwise).
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Get current state
            cursor = await db.execute(
                "SELECT is_favorite FROM commands WHERE command = ?", (command,)
            )
            row = await cursor.fetchone()

            if row is None:
                return False

            new_state = 1 - row[0]
            await db.execute(
                "UPDATE commands SET is_favorite = ? WHERE command = ?",
                (new_state, command),
            )
            await db.commit()

            return bool(new_state)

    async def delete_command(self, command: str) -> None:
        """Delete a command from the database.
        
        Args:
            command: The command to delete.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM commands WHERE command = ?", (command,))
            await db.commit()

    async def get_all(self, limit: int = 500) -> list[CommandRow]:
        """Get all commands, most recent first.
        
        Args:
            limit: Maximum number of commands to return.
            
        Returns:
            List of commands.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, command, source_shell, first_seen, last_seen, run_count, is_favorite
                FROM commands
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                CommandRow(
                    id=row["id"],
                    command=row["command"],
                    source_shell=row["source_shell"],
                    first_seen=datetime.fromisoformat(row["first_seen"])
                    if row["first_seen"]
                    else None,
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    run_count=row["run_count"],
                    is_favorite=bool(row["is_favorite"]),
                )
            )

        return results
