"""Tests for command injector."""

import pytest
from unittest.mock import Mock, patch
from cmdpop.injector.base import Injector


class MockInjector(Injector):
    """Mock injector for testing."""

    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.last_command = None

    def inject(self, command: str) -> bool:
        self.last_command = command
        return self.should_succeed


def test_injector_success():
    """Test successful injection."""
    injector = MockInjector(should_succeed=True)
    result = injector.inject("git status")
    assert result is True
    assert injector.last_command == "git status"


def test_injector_failure():
    """Test failed injection."""
    injector = MockInjector(should_succeed=False)
    result = injector.inject("git status")
    assert result is False


def test_injector_fallback_to_clipboard():
    """Test fallback to clipboard on failure."""
    injector = MockInjector(should_succeed=False)

    with patch("pyperclip.copy") as mock_copy:
        injector.inject_with_fallback("git status")
        mock_copy.assert_called_once_with("git status")


def test_long_command_injection():
    """Test that long commands can be injected."""
    long_command = "git commit -m 'A very long commit message that explains all the changes made in this commit in great detail and probably runs on for quite a while'"
    injector = MockInjector(should_succeed=True)
    result = injector.inject(long_command)
    assert result is True
    assert len(injector.last_command) > 100


def test_command_with_quotes():
    """Test injection of commands with quotes."""
    command = """git commit -m "fix: quotes and 'apostrophes' in message" """
    injector = MockInjector(should_succeed=True)
    result = injector.inject(command)
    assert result is True


def test_command_with_special_chars():
    """Test injection of commands with special characters."""
    command = "echo 'test $VAR && ls | grep pattern'"
    injector = MockInjector(should_succeed=True)
    result = injector.inject(command)
    assert result is True
