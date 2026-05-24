"""Bash history reader."""

from datetime import datetime
from pathlib import Path

from .base import HistoryEntry, HistoryReader


class BashReader(HistoryReader):
    """Reader for bash history files (~/.bash_history)."""

    def get_history_path(self) -> Path | None:
        """Return path to bash history file."""
        path = Path.home() / ".bash_history"
        return path if path.exists() else None

    def parse(self, content: str) -> list[HistoryEntry]:
        """Parse bash history format.
        
        Format: One command per line. Can have timestamp markers starting with '#'.
        """
        entries = []
        path = self.get_history_path()
        if not path:
            # For testing, use a placeholder path
            path = Path("~/.bash_history")

        lines = content.splitlines()
        current_timestamp = None

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            # Handle HISTTIMEFORMAT lines (e.g., "# 1234567890")
            if line.startswith("#"):
                try:
                    current_timestamp = datetime.fromtimestamp(int(line[1:].strip()))
                except (ValueError, IndexError):
                    continue
                continue

            # Add command entry
            entries.append(
                HistoryEntry(
                    command=line,
                    timestamp=current_timestamp,
                    source_shell="bash",
                    source_file=path,
                )
            )

        return entries
