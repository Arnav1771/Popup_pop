"""Base class for history readers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class HistoryEntry:
    """Represents a single command history entry."""

    command: str
    timestamp: datetime | None
    source_shell: str  # "bash" | "zsh" | "fish" | "powershell" | "cmd"
    source_file: Path


class HistoryReader(ABC):
    """Abstract base class for shell history readers."""

    @abstractmethod
    def get_history_path(self) -> Path | None:
        """Return path to history file, or None if shell not installed."""
        ...

    @abstractmethod
    def parse(self, content: str) -> list[HistoryEntry]:
        """Parse raw history file content into entries."""
        ...

    def read(self) -> list[HistoryEntry]:
        """Read and parse history. Returns [] if file not found."""
        path = self.get_history_path()
        if not path or not path.exists():
            return []
        try:
            return self.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (PermissionError, OSError):
            return []
