"""Platform detection utilities."""

import sys
from typing import Literal


def get_os() -> Literal["windows", "darwin", "linux"]:
    """Get the current operating system."""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "darwin"
    else:
        return "linux"


def get_shell_name() -> str | None:
    """Detect the current shell being used."""
    import os

    # Check SHELL environment variable
    shell = os.environ.get("SHELL", "").split("/")[-1]
    if shell in ("bash", "zsh", "fish", "sh"):
        return shell

    # Windows: check if running in PowerShell
    if sys.platform == "win32":
        if "POWERSHELL" in os.environ.get("PSModulePath", "").upper():
            return "powershell"
        return "cmd"

    return None
