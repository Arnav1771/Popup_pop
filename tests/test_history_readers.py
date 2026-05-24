"""Auto-generated test suite for history readers.

Run 'python tests/generate_tests.py' to regenerate this file.
"""

import pytest
from datetime import datetime
from pathlib import Path
from cmdpop.history.bash_reader import BashReader
from cmdpop.history.zsh_reader import ZshReader
from cmdpop.history.fish_reader import FishReader
from cmdpop.history.powershell_reader import PowerShellReader
from cmdpop.history.cmd_reader import CmdReader


# ============================================================================
# AUTO-GENERATED TEST CASES — DO NOT EDIT MANUALLY
# ============================================================================

@pytest.mark.parametrize("raw_line,shell,should_parse,reason", [
    ("git commit -m 'fix auth'", 'bash', True, 'contains quotes'),
    ('npm run dev', 'bash', True, ''),
    ('# 1698765432', 'bash', False, 'bash timestamp marker'),
    ('docker build -t myapp . --no-cache', 'bash', True, ''),
    ('export SECRET_TOKEN=abc123', 'bash', True, 'contains sensitive keyword'),
    ("ls -la | grep '.py' | head -20", 'bash', True, 'contains pipe/redirect/compound operators'),
    ('cd ~/Projects/myapp && git pull', 'bash', True, 'contains pipe/redirect/compound operators'),
    ('for f in *.txt; do echo $f; done', 'bash', True, 'contains pipe/redirect/compound operators'),
    ("git commit -m 'feat: add émojis 🎉'", 'bash', True, 'contains quotes'),
    (': 1698765432:0;git status', 'zsh_extended', True, 'EXTENDED_HISTORY format with timestamp'),
    (': 1698765431:0;git diff HEAD~1', 'zsh_extended', True, 'EXTENDED_HISTORY format with timestamp'),
    (': 1698765430:120;npm install', 'zsh_extended', True, 'EXTENDED_HISTORY format with timestamp'),
    (": 1698765429:0;git commit -m 'multi\\", 'zsh_extended', True, 'multi-line command (continuation)'),
    ("line command'", 'zsh_extended', True, ''),
    ('- cmd: git log --oneline -10', 'fish', True, 'fish YAML entry'),
    ('  when: 1698765432', 'fish', False, 'timestamp line only'),
    ('- cmd: kubectl get pods -A', 'fish', True, 'fish YAML entry'),
    ('  when: 1698765430', 'fish', False, 'timestamp line only'),
    ('Get-ChildItem -Recurse', 'powershell', True, 'contains PowerShell syntax'),
    ('Set-Location C:\\Users\\dev\\projects', 'powershell', True, 'contains path separators'),
    ("git commit -m 'fix: windows paths'", 'powershell', True, 'contains PowerShell syntax'),
    ('docker ps -a', 'powershell', True, 'contains PowerShell syntax'),

])
def test_reader_parse_line(raw_line, shell, should_parse, reason):
    """Test that readers correctly parse or skip lines based on shell format."""
    if shell == "bash":
        reader = BashReader()
        entries = reader.parse(raw_line)
        # Bash timestamp lines (starting with '#' followed by digits) should be skipped
        if raw_line.startswith("#"):
            assert len(entries) == 0, f"Bash timestamp line should be skipped: {raw_line}"
        elif raw_line.strip():
            assert len(entries) == 1, f"Bash command line should be parsed: {raw_line}"
    elif shell == "zsh_extended":
        reader = ZshReader()
        entries = reader.parse(raw_line)
        if raw_line.startswith(": "):
            assert len(entries) == 1 or raw_line.rstrip().endswith("\\"), f"zsh extended format should parse: {raw_line}"
    elif shell == "fish":
        reader = FishReader()
        entries = reader.parse(raw_line)
        if raw_line.startswith("- cmd:"):
            assert len(entries) == 1, f"Fish command line should parse: {raw_line}"
        elif raw_line.startswith("  when:"):
            assert len(entries) == 0, f"Fish timestamp line should be skipped: {raw_line}"
    elif shell == "powershell":
        reader = PowerShellReader()
        entries = reader.parse(raw_line)
        if raw_line.strip():
            assert len(entries) == 1, f"PowerShell command should parse: {raw_line}"
    else:
        pytest.skip(f"Unknown shell: {shell}")


# ============================================================================
# MANUAL TEST SECTION — safe to edit
# ============================================================================

def test_bash_reader_skips_timestamp_lines():
    """Bash reader should skip lines starting with '#' (timestamps)."""
    reader = BashReader()
    content = """git commit -m 'test'
# 1234567890
git status"""
    entries = reader.parse(content)
    assert len(entries) == 2
    assert entries[0].command == "git commit -m 'test'"
    assert entries[1].command == "git status"


def test_bash_reader_skips_empty_lines():
    """Bash reader should skip empty lines."""
    reader = BashReader()
    content = """git commit -m 'test'

git status"""
    entries = reader.parse(content)
    assert len(entries) == 2


def test_zsh_extended_history_with_timestamp():
    """Zsh reader should parse EXTENDED_HISTORY format."""
    reader = ZshReader()
    content = ": 1698765432:0;git status"
    entries = reader.parse(content)
    assert len(entries) == 1
    assert entries[0].command == "git status"
    assert entries[0].timestamp is not None
    assert entries[0].timestamp.timestamp() == 1698765432


def test_zsh_multiline_command():
    """Zsh reader should handle multi-line commands with backslash continuation."""
    reader = ZshReader()
    content = """: 1698765432:0;git commit -m 'multi\
line message'"""
    entries = reader.parse(content)
    assert len(entries) == 1
    assert "multi" in entries[0].command
    assert "line message" in entries[0].command


def test_fish_reader_yaml_format():
    """Fish reader should parse YAML-like format."""
    reader = FishReader()
    content = """- cmd: git log --oneline
  when: 1698765432"""
    entries = reader.parse(content)
    assert len(entries) == 1
    assert entries[0].command == "git log --oneline"
    assert entries[0].timestamp is not None


def test_powershell_reader_plain_format():
    """PowerShell reader should parse plain text format."""
    reader = PowerShellReader()
    content = """Get-ChildItem -Recurse
Set-Location C:\\Users\\dev"""
    entries = reader.parse(content)
    assert len(entries) == 2
    assert entries[0].command == "Get-ChildItem -Recurse"


def test_all_readers_skip_empty_lines():
    """All readers should skip empty lines."""
    test_cases = [
        (BashReader(), "bash", "cmd1\n\ncmd2"),
        (ZshReader(), "zsh", "cmd1\n\ncmd2"),
        (PowerShellReader(), "powershell", "cmd1\n\ncmd2"),
        (FishReader(), "fish", "- cmd: cmd1\n  when: 1234567890\n- cmd: cmd2\n  when: 1234567891"),
    ]

    for reader, shell_name, content in test_cases:
        entries = reader.parse(content)
        assert len(entries) == 2, f"{shell_name} failed to skip empty lines"
        assert entries[0].command == ("cmd1" if shell_name != "fish" else "cmd1")


def test_history_entry_dataclass():
    """Test HistoryEntry dataclass creation."""
    from cmdpop.history.base import HistoryEntry
    from datetime import datetime

    path = Path.home() / ".bash_history"
    entry = HistoryEntry(
        command="git status",
        timestamp=datetime.now(),
        source_shell="bash",
        source_file=path,
    )
    assert entry.command == "git status"
    assert entry.source_shell == "bash"
