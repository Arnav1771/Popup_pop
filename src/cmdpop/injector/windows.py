"""Windows-specific command injector."""

import logging
import subprocess

import pyautogui

from .base import Injector

logger = logging.getLogger(__name__)


class WindowsInjector(Injector):
    """Command injector for Windows using pyautogui and win32 APIs."""

    def inject(self, command: str) -> bool:
        """Inject command into active terminal window.
        
        Args:
            command: Command text to inject
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Try using pywin32 first (more reliable for Windows)
            try:
                import pywin32  # noqa: F401

                return self._inject_with_pywin32(command)
            except ImportError:
                pass

            # Fallback to pyautogui
            pyautogui.typewrite(command, interval=0.05)
            return True

        except Exception as e:
            logger.debug(f"Windows injection failed: {e}")
            return False

    def _inject_with_pywin32(self, command: str) -> bool:
        """Try to inject using win32api."""
        try:
            import win32gui
            from win32com.client import Dispatch

            # Get the active window
            hwnd = win32gui.GetForegroundWindow()

            # Try to send keys using a COM interface
            shell = Dispatch("WScript.Shell")
            shell.SendKeys(command)
            return True
        except Exception as e:
            logger.debug(f"pywin32 injection failed: {e}")
            return False
