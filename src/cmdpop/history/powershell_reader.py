"""PowerShell history reader."""

import sys
from datetime import datetime
from pathlib import Path

from .base import HistoryEntry, HistoryReader


class PowerShellReader(HistoryReader):
    """Reader for PowerShell PSReadLine history files."""

    def get_history_path(self) -> Path | None:
        """Return path to PSReadLine history file.
        
        Windows: %APPDATA%\\Microsoft\\Windows\\PowerShell\\PSReadLine\\ConsoleHost_history.txt
        Unix: ~/.local/share/powershell/PSReadLine/ConsoleHost_history.txt
        """
        if sys.platform == "win32":
            appdata = Path(
                __import__("os").environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            )
            path = (
                appdata
                / "Microsoft"
                / "Windows"
                / "PowerShell"
                / "PSReadLine"
                / "ConsoleHost_history.txt"
            )
        else:
            path = (
                Path.home()
                / ".local"
                / "share"
                / "powershell"
                / "PSReadLine"
                / "ConsoleHost_history.txt"
            )

        return path if path.exists() else None

    def parse(self, content: str) -> list[HistoryEntry]:
        """Parse PowerShell history format.
        
        Format: One command per line, plain text.
        """
        entries = []
        path = self.get_history_path()
        if not path:
            # For testing, use a placeholder path
            path = Path("~/.local/share/powershell/PSReadLine/ConsoleHost_history.txt")

        lines = content.splitlines()

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            entries.append(
                HistoryEntry(
                    command=line,
                    timestamp=None,
                    source_shell="powershell",
                    source_file=path,
                )
            )

        return entries
