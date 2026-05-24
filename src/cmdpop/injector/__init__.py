"""Command injection system for various platforms."""

import sys
from .base import Injector


def get_injector() -> Injector:
    """Get the appropriate injector for the current platform."""
    if sys.platform == "win32":
        from .windows import WindowsInjector

        return WindowsInjector()
    elif sys.platform == "darwin":
        from .mac import MacInjector

        return MacInjector()
    else:
        from .linux import LinuxInjector

        return LinuxInjector()


__all__ = ["Injector", "get_injector"]
