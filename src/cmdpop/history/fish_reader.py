"""Fish history reader."""

from datetime import datetime
from pathlib import Path

from .base import HistoryEntry, HistoryReader


class FishReader(HistoryReader):
    """Reader for fish shell history files (~/.local/share/fish/fish_history)."""

    def get_history_path(self) -> Path | None:
        """Return path to fish history file."""
        path = Path.home() / ".local" / "share" / "fish" / "fish_history"
        return path if path.exists() else None

    def parse(self, content: str) -> list[HistoryEntry]:
        """Parse fish history format.
        
        Format: YAML-like with entries like:
        - cmd: git commit -m "fix"
          when: 1698765432
        """
        entries = []
        path = self.get_history_path()
        if not path:
            # For testing, use a placeholder path
            path = Path("~/.local/share/fish/fish_history")

        lines = content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]
            i += 1

            # Look for entry starting with "- cmd:"
            if line.startswith("- cmd:"):
                # Extract command text after "- cmd: "
                command = line[6:].strip()

                # Get timestamp from next line if it exists
                timestamp = None
                if i < len(lines):
                    next_line = lines[i]
                    if next_line.strip().startswith("when:"):
                        try:
                            ts_value = int(next_line.split(":", 1)[1].strip())
                            timestamp = datetime.fromtimestamp(ts_value)
                        except (ValueError, IndexError):
                            pass
                        i += 1

                entries.append(
                    HistoryEntry(
                        command=command,
                        timestamp=timestamp,
                        source_shell="fish",
                        source_file=path,
                    )
                )

        return entries
