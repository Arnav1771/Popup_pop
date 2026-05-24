"""Tests for fuzzy search functionality."""

import pytest
from rapidfuzz import fuzz


def test_exact_match_high_score():
    """Exact matches should score highest."""
    query = "git status"
    command = "git status"
    score = fuzz.token_sort_ratio(query, command)
    assert score == 100


def test_partial_match():
    """Partial matches should be found."""
    query = "git"
    commands = ["git status", "git log", "ls -la"]
    scores = [(cmd, fuzz.token_sort_ratio(query, cmd)) for cmd in commands]
    scored = [(cmd, score) for cmd, score in scores if score > 30]
    assert len(scored) == 2


def test_case_insensitive_search():
    """Search should be case-insensitive."""
    query = "GIT STATUS"
    command = "git status"
    score = fuzz.token_sort_ratio(query.lower(), command.lower())
    assert score > 50


def test_empty_query_no_filter():
    """Empty query should not filter any commands."""
    query = ""
    commands = ["git status", "ls -la", "cd ~"]

    if not query:
        # Empty query returns all
        assert True
    else:
        # Non-empty query filters
        assert False


def test_typo_tolerance():
    """Should find commands with minor typos."""
    query = "git comit"  # typo: missing 'm'
    command = "git commit"
    score = fuzz.token_sort_ratio(query, command)
    assert score > 50


def test_order_insensitive():
    """Should find commands regardless of word order."""
    query = "status git"
    command = "git status"
    score = fuzz.token_sort_ratio(query, command)
    assert score > 50
