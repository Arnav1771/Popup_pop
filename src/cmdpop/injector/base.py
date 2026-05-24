"""Base class for command injection."""

from abc import ABC, abstractmethod

import pyperclip


class Injector(ABC):
    """Abstract base class for command injection on different platforms."""

    @abstractmethod
    def inject(self, command: str) -> bool:
        """Inject command text into the active terminal.
        
        Args:
            command: Command text to inject
            
        Returns:
            True if injection was successful, False otherwise.
        """
        ...

    def inject_with_fallback(self, command: str) -> None:
        """Inject command with clipboard fallback.
        
        Tries to inject the command. If injection fails, copies to clipboard.
        
        Args:
            command: Command text to inject
        """
        if not self.inject(command):
            try:
                pyperclip.copy(command)
                print(f"[CmdPop] Copied to clipboard: {command[:50]}...")
            except Exception as e:
                print(f"[CmdPop] Failed to inject or copy: {e}")
