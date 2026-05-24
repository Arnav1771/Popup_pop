"""CMD (Windows Command Prompt) history reader."""

import sys
from datetime import datetime
from pathlib import Path

from .base import HistoryEntry, HistoryReader


class CmdReader(HistoryReader):
    """Reader for CMD/Clink history files.
    
    Note: CMD.exe doesn't save history between sessions natively.
    This reader works with Clink, which provides a history file.
    """

    def get_history_path(self) -> Path | None:
        """Return path to Clink history file.
        
        Windows only: %LOCALAPPDATA%\\clink\\.history
        """
        if sys.platform != "win32":
            return None

        localappdata = Path(
            __import__("os").environ.get(
                "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
            )
        )
        path = localappdata / "clink" / ".history"
        return path if path.exists() else None

    def parse(self, content: str) -> list[HistoryEntry]:
        """Parse Clink history format.
        
        Format: One command per line, plain text.
        """
        entries = []
        path = self.get_history_path()
        if not path:
            # For testing, use a placeholder path
            path = Path("%LOCALAPPDATA%\\clink\\.history")

        lines = content.splitlines()

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            entries.append(
                HistoryEntry(
                    command=line,
                    timestamp=None,
                    source_shell="cmd",
                    source_file=path,
                )
            )

        return entries
