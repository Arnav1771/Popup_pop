"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def fixture_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures" / "history_samples"


@pytest.fixture
def bash_fixture(fixture_dir: Path) -> str:
    """Load bash history fixture."""
    bash_file = fixture_dir / "bash.txt"
    if bash_file.exists():
        return bash_file.read_text()
    return ""


@pytest.fixture
def zsh_fixture(fixture_dir: Path) -> str:
    """Load zsh history fixture."""
    zsh_file = fixture_dir / "zsh_extended.txt"
    if zsh_file.exists():
        return zsh_file.read_text()
    return ""


@pytest.fixture
def fish_fixture(fixture_dir: Path) -> str:
    """Load fish history fixture."""
    fish_file = fixture_dir / "fish.txt"
    if fish_file.exists():
        return fish_file.read_text()
    return ""
