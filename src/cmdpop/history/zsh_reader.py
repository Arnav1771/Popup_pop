"""Zsh history reader."""

from datetime import datetime
from pathlib import Path

from .base import HistoryEntry, HistoryReader


class ZshReader(HistoryReader):
    """Reader for zsh history files (~/.zsh_history)."""

    def get_history_path(self) -> Path | None:
        """Return path to zsh history file."""
        path = Path.home() / ".zsh_history"
        return path if path.exists() else None

    def parse(self, content: str) -> list[HistoryEntry]:
        """Parse zsh history format.
        
        Handles both plain and EXTENDED_HISTORY formats:
        - Plain: one command per line
        - Extended: `: <unix_timestamp>:<elapsed>;<command>` with possible multi-line commands
        """
        entries = []
        path = self.get_history_path()
        if not path:
            # For testing, use a placeholder path
            path = Path("~/.zsh_history")

        lines = content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]
            i += 1

            # Skip empty lines
            if not line.strip():
                continue

            # Check for EXTENDED_HISTORY format
            if line.startswith(": "):
                parts = line.split(";", 1)
                if len(parts) == 2:
                    # Extract timestamp from ": timestamp:elapsed;"
                    try:
                        meta_part = parts[0]  # ": timestamp:elapsed"
                        meta_tokens = meta_part.split(":")
                        if len(meta_tokens) >= 2:
                            timestamp = int(meta_tokens[1])
                            dt = datetime.fromtimestamp(timestamp)
                        else:
                            dt = None
                    except (ValueError, IndexError):
                        dt = None

                    # Get command, handling multi-line continuations
                    command = parts[1].rstrip()

                    # Handle line continuation with backslash
                    while command.endswith("\\") and i < len(lines):
                        command = command[:-1] + lines[i]
                        i += 1

                    entries.append(
                        HistoryEntry(
                            command=command,
                            timestamp=dt,
                            source_shell="zsh",
                            source_file=path,
                        )
                    )
                    continue

            # Plain format: just a command
            entries.append(
                HistoryEntry(
                    command=line,
                    timestamp=None,
                    source_shell="zsh",
                    source_file=path,
                )
            )

        return entries
