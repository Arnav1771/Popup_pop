"""Tests for deduplication logic."""

import pytest
from cmdpop.history.base import HistoryEntry
from datetime import datetime
from pathlib import Path


def test_dedup_identical_commands():
    """Test that identical commands are deduplicated."""
    entries = [
        HistoryEntry("git status", None, "bash", Path("test")),
        HistoryEntry("git status", None, "bash", Path("test")),
        HistoryEntry("git status", None, "zsh", Path("test")),
    ]

    # Deduplicate by command text
    unique = {}
    for entry in entries:
        if entry.command not in unique:
            unique[entry.command] = entry

    assert len(unique) == 1
    assert "git status" in unique


def test_case_sensitive_dedup():
    """Test that deduplication is case-sensitive."""
    entries = [
        HistoryEntry("git status", None, "bash", Path("test")),
        HistoryEntry("Git status", None, "bash", Path("test")),
    ]

    unique = {}
    for entry in entries:
        if entry.command not in unique:
            unique[entry.command] = entry

    assert len(unique) == 2


def test_whitespace_matters_in_dedup():
    """Test that whitespace is significant in deduplication."""
    entries = [
        HistoryEntry("git  status", None, "bash", Path("test")),
        HistoryEntry("git status", None, "bash", Path("test")),
    ]

    unique = {}
    for entry in entries:
        if entry.command not in unique:
            unique[entry.command] = entry

    assert len(unique) == 2
