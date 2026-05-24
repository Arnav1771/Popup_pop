"""Linux-specific command injector."""

import logging
import shutil
import subprocess

import pyautogui

from .base import Injector

logger = logging.getLogger(__name__)


class LinuxInjector(Injector):
    """Command injector for Linux using xdotool or ydotool."""

    def inject(self, command: str) -> bool:
        """Inject command into active terminal.
        
        Args:
            command: Command text to inject
            
        Returns:
            True if successful, False otherwise.
        """
        # Try xdotool first (X11)
        if shutil.which("xdotool"):
            if self._inject_with_xdotool(command):
                return True

        # Try ydotool (Wayland)
        if shutil.which("ydotool"):
            if self._inject_with_ydotool(command):
                return True

        # Fallback to pyautogui
        try:
            pyautogui.typewrite(command, interval=0.01)
            return True
        except Exception as e:
            logger.debug(f"pyautogui injection failed: {e}")
            return False

    def _inject_with_xdotool(self, command: str) -> bool:
        """Inject using xdotool (X11)."""
        try:
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", command],
                check=True,
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as e:
            logger.debug(f"xdotool injection failed: {e}")
            return False

    def _inject_with_ydotool(self, command: str) -> bool:
        """Inject using ydotool (Wayland)."""
        try:
            subprocess.run(
                ["ydotool", "type", command],
                check=True,
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as e:
            logger.debug(f"ydotool injection failed: {e}")
            return False
