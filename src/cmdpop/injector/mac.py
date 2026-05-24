"""macOS-specific command injector."""

import logging
import subprocess

import pyautogui

from .base import Injector

logger = logging.getLogger(__name__)


class MacInjector(Injector):
    """Command injector for macOS using AppleScript or pyautogui."""

    def inject(self, command: str) -> bool:
        """Inject command into active terminal.
        
        Args:
            command: Command text to inject
            
        Returns:
            True if successful, False otherwise.
        """
        # Try AppleScript first
        if self._inject_with_applescript(command):
            return True

        # Fallback to pyautogui
        try:
            pyautogui.typewrite(command, interval=0.05)
            return True
        except Exception as e:
            logger.debug(f"pyautogui injection failed: {e}")
            return False

    def _inject_with_applescript(self, command: str) -> bool:
        """Inject using AppleScript."""
        try:
            # Escape quotes in command for AppleScript
            escaped = command.replace('"', '\\"')

            # Try to send to Terminal.app
            script = f'tell application "Terminal" to do script "{escaped}"'
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as e:
            logger.debug(f"AppleScript injection failed: {e}")
            return False
