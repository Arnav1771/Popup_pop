"""Configuration system for CmdPop."""

import logging
import sys
import tomllib
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Settings:
    """Load and manage CmdPop configuration."""

    DEFAULTS = {
        "cmdpop": {
            "hotkey": "ctrl+alt+h",
            "max_history": 10000,
            "theme": "dark",
        },
        "history": {
            "sources": ["auto"],
            "exclude_patterns": ["password", "passwd", "secret", "token", "apikey", "api_key"],
        },
        "display": {
            "height_percent": 60,
            "width_percent": 50,
            "position": "center",
            "show_timestamps": True,
            "show_source_shell": True,
        },
    }

    def __init__(self, config_path: Path | None = None):
        """Initialize settings from config file or defaults.
        
        Args:
            config_path: Path to config file. Defaults to ~/.cmdpop/config.toml
        """
        if config_path is None:
            config_path = Path.home() / ".cmdpop" / "config.toml"

        self.config_path = config_path
        self.data: dict[str, Any] = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file or use defaults."""
        config = dict(self.DEFAULTS)

        if self.config_path.exists():
            try:
                with open(self.config_path, "rb") as f:
                    file_config = tomllib.load(f)
                    # Deep merge with defaults
                    for key, value in file_config.items():
                        if isinstance(value, dict) and key in config:
                            config[key].update(value)
                        else:
                            config[key] = value
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")

        return config

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: Config section (e.g., "cmdpop", "history")
            key: Config key
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        if section in self.data:
            return self.data[section].get(key, default)
        return default

    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire config section.
        
        Args:
            section: Config section name
            
        Returns:
            Dictionary of section settings
        """
        return self.data.get(section, {})

    def get_hotkey(self) -> str:
        """Get the configured hotkey."""
        return self.get("cmdpop", "hotkey", "ctrl+alt+h")

    def get_exclude_patterns(self) -> list[str]:
        """Get patterns to exclude from history storage."""
        return self.get("history", "exclude_patterns", [])

    def get_max_history(self) -> int:
        """Get maximum history items to store."""
        return self.get("cmdpop", "max_history", 10000)

    def get_theme(self) -> str:
        """Get UI theme preference."""
        return self.get("cmdpop", "theme", "dark")

    def get_sources(self) -> list[str]:
        """Get history sources to read."""
        return self.get("history", "sources", ["auto"])

    def get_display_height_percent(self) -> int:
        """Get display height as percentage of terminal."""
        return self.get("display", "height_percent", 60)

    def get_display_width_percent(self) -> int:
        """Get display width as percentage of terminal."""
        return self.get("display", "width_percent", 50)

    def get_display_position(self) -> str:
        """Get display position (center, top, bottom)."""
        return self.get("display", "position", "center")

    def show_timestamps(self) -> bool:
        """Whether to show timestamps in the UI."""
        return self.get("display", "show_timestamps", True)

    def show_source_shell(self) -> bool:
        """Whether to show source shell in the UI."""
        return self.get("display", "show_source_shell", True)

    def save(self) -> None:
        """Save current settings to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            f.write(self._to_toml(self.data))

    def _to_toml(self, data: dict[str, Any], indent: int = 0) -> str:
        """Convert dict to TOML format."""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"[{key}]")
                for k, v in value.items():
                    lines.append(f"{k} = {self._format_value(v)}")
            else:
                lines.append(f"{key} = {self._format_value(value)}")
        return "\n".join(lines)

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a value for TOML output."""
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, list):
            return "[" + ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in value) + "]"
        else:
            return str(value)
