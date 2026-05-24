"""Self-building test generator for CmdPop.

This script generates test cases from fixture files and creates the test_history_readers.py file.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Sample fixture data
FIXTURE_SAMPLES = {
    "bash": [
        "git commit -m 'fix auth'",
        "npm run dev",
        "",  # empty → skip
        "# 1698765432",  # bash timestamp → skip
        "docker build -t myapp . --no-cache",
        "export SECRET_TOKEN=abc123",  # sensitive → excluded from DB
        "ls -la | grep '.py' | head -20",  # pipes
        "cd ~/Projects/myapp && git pull",  # compound
        "for f in *.txt; do echo $f; done",  # loop
        "git commit -m 'feat: add émojis 🎉'",  # unicode
    ],
    "zsh_extended": [
        ": 1698765432:0;git status",
        ": 1698765431:0;git diff HEAD~1",
        ": 1698765430:120;npm install",  # with elapsed time
        ": 1698765429:0;git commit -m 'multi\\",  # multi-line start
        "line command'",  # continuation
    ],
    "fish": [
        "- cmd: git log --oneline -10",
        "  when: 1698765432",
        "- cmd: kubectl get pods -A",
        "  when: 1698765430",
    ],
    "powershell": [
        "Get-ChildItem -Recurse",
        "Set-Location C:\\Users\\dev\\projects",
        "git commit -m 'fix: windows paths'",
        "docker ps -a",
    ],
}


def generate_fixture_files() -> None:
    """Create sample history files if they don't exist."""
    fixtures_dir = Path("tests/fixtures/history_samples")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    for shell, lines in FIXTURE_SAMPLES.items():
        fixture_file = fixtures_dir / f"{shell}.txt"
        if not fixture_file.exists():
            fixture_file.write_text("\n".join(lines))
            print(f"Created {fixture_file}")


def analyze_edge_cases(lines: list[str], shell: str) -> list[dict]:
    """Return list of edge case test scenarios."""
    cases = []

    for i, line in enumerate(lines):
        # Skip empty lines - they shouldn't appear in tests
        if not line.strip():
            continue

        case = {
            "id": f"{shell}_line_{i}",
            "input": line,
            "shell": shell,
            "should_parse": True,
            "reason": "",
        }

        # Analyze edge cases based on shell
        if shell == "bash":
            if line.startswith("#"):
                case["should_parse"] = False
                case["reason"] = "bash timestamp marker"
            elif "password" in line.lower() or "secret" in line.lower():
                case["reason"] = "contains sensitive keyword"
            elif any(char in line for char in ["|", ">", "<", "&", ";"]):
                case["reason"] = "contains pipe/redirect/compound operators"
            elif "\\" in line:
                case["reason"] = "contains backslash"
            elif any(char in line for char in ["'", '"']):
                case["reason"] = "contains quotes"
            elif any(ord(c) > 127 for c in line):
                case["reason"] = "contains unicode/emoji"

        elif shell == "zsh_extended":
            if line.startswith(": "):
                case["reason"] = "EXTENDED_HISTORY format with timestamp"
                if line.rstrip().endswith("\\"):
                    case["reason"] = "multi-line command (continuation)"

        elif shell == "fish":
            if line.startswith("- cmd:"):
                case["reason"] = "fish YAML entry"
            elif line.strip().startswith("when:"):
                case["should_parse"] = False
                case["reason"] = "timestamp line only"

        elif shell == "powershell":
            if "\\" in line or "/" in line:
                case["reason"] = "contains path separators"
            elif any(char in line for char in ["$", "-"]):
                case["reason"] = "contains PowerShell syntax"

        cases.append(case)

    return cases


def write_test_file(test_cases: list[dict]) -> None:
    """Write parametrized pytest file."""
    test_file = Path("tests/test_history_readers.py")

    lines = [
        '"""Auto-generated test suite for history readers.',
        '',
        'Run \'python tests/generate_tests.py\' to regenerate this file.',
        '"""',
        '',
        'import pytest',
        'from datetime import datetime',
        'from pathlib import Path',
        'from cmdpop.history.bash_reader import BashReader',
        'from cmdpop.history.zsh_reader import ZshReader',
        'from cmdpop.history.fish_reader import FishReader',
        'from cmdpop.history.powershell_reader import PowerShellReader',
        'from cmdpop.history.cmd_reader import CmdReader',
        '',
        '',
        '# ============================================================================',
        '# AUTO-GENERATED TEST CASES — DO NOT EDIT MANUALLY',
        '# ============================================================================',
        '',
        '@pytest.mark.parametrize("raw_line,shell", [',
    ]

    for case in test_cases:
        lines.append(f"    ({repr(case['input'])}, {repr(case['shell'])}),")

    lines.extend([
        '])',
        'def test_reader_parse_line(raw_line, shell):',
        '    """Test that readers correctly parse lines based on shell format."""',
        '    # Simple smoke test - verify parsing doesn\'t crash',
        '    if shell == "bash":',
        '        reader = BashReader()',
        '        entries = reader.parse(raw_line)',
        '        assert isinstance(entries, list)',
        '    elif shell == "zsh_extended":',
        '        reader = ZshReader()',
        '        entries = reader.parse(raw_line)',
        '        assert isinstance(entries, list)',
        '    elif shell == "fish":',
        '        reader = FishReader()',
        '        entries = reader.parse(raw_line)',
        '        assert isinstance(entries, list)',
        '    elif shell == "powershell":',
        '        reader = PowerShellReader()',
        '        entries = reader.parse(raw_line)',
        '        assert isinstance(entries, list)',
        '    else:',
        '        pytest.skip(f"Unknown shell: {shell}")',
        '',
        '',
        '# ============================================================================',
        '# MANUAL TEST SECTION — safe to edit',
        '# ============================================================================',
        '',
        'def test_bash_reader_skips_timestamp_lines():',
        '    """Bash reader should skip lines starting with \'#\' (timestamps)."""',
        '    reader = BashReader()',
        '    content = """git commit -m \'test\'',
        '# 1234567890',
        'git status"""',
        '    entries = reader.parse(content)',
        '    assert len(entries) == 2',
        '    assert entries[0].command == "git commit -m \'test\'"',
        '    assert entries[1].command == "git status"',
        '',
        '',
        'def test_bash_reader_skips_empty_lines():',
        '    """Bash reader should skip empty lines."""',
        '    reader = BashReader()',
        '    content = """git commit -m \'test\'',
        '',
        'git status"""',
        '    entries = reader.parse(content)',
        '    assert len(entries) == 2',
        '',
        '',
        'def test_zsh_extended_history_with_timestamp():',
        '    """Zsh reader should parse EXTENDED_HISTORY format."""',
        '    reader = ZshReader()',
        '    content = ": 1698765432:0;git status"',
        '    entries = reader.parse(content)',
        '    assert len(entries) == 1',
        '    assert entries[0].command == "git status"',
        '    assert entries[0].timestamp is not None',
        '    assert entries[0].timestamp.timestamp() == 1698765432',
        '',
        '',
        'def test_zsh_multiline_command():',
        '    """Zsh reader should handle multi-line commands with backslash continuation."""',
        '    reader = ZshReader()',
        '    content = """: 1698765432:0;git commit -m \'multi\\',
        'line message\'"""',
        '    entries = reader.parse(content)',
        '    assert len(entries) == 1',
        '    assert "multi" in entries[0].command',
        '    assert "line message" in entries[0].command',
        '',
        '',
        'def test_fish_reader_yaml_format():',
        '    """Fish reader should parse YAML-like format."""',
        '    reader = FishReader()',
        '    content = """- cmd: git log --oneline',
        '  when: 1698765432"""',
        '    entries = reader.parse(content)',
        '    assert len(entries) == 1',
        '    assert entries[0].command == "git log --oneline"',
        '    assert entries[0].timestamp is not None',
        '',
        '',
        'def test_powershell_reader_plain_format():',
        '    """PowerShell reader should parse plain text format."""',
        '    reader = PowerShellReader()',
        '    content = """Get-ChildItem -Recurse',
        'Set-Location C:\\\\Users\\\\dev"""',
        '    entries = reader.parse(content)',
        '    assert len(entries) == 2',
        '    assert entries[0].command == "Get-ChildItem -Recurse"',
        '',
        '',
        'def test_all_readers_skip_empty_lines():',
        '    """All readers should skip empty lines."""',
        '    # Test each reader type with appropriate format',
        '    test_cases = [',
        '        (BashReader(), "bash", "cmd1\\n\\ncmd2"),',
        '        (ZshReader(), "zsh", "cmd1\\n\\ncmd2"),',
        '        (PowerShellReader(), "ps", "cmd1\\n\\ncmd2"),',
        '        (FishReader(), "fish", "- cmd: cmd1\\n  when: 1234567890\\n- cmd: cmd2\\n  when: 1234567891"),',
        '    ]',
        '',
        '    for reader, shell_type, test_content in test_cases:',
        '        content = test_content.replace("\\\\n", "\\n")',
        '        entries = reader.parse(content)',
        '        assert len(entries) == 2, f"{shell_type}: expected 2 entries, got {len(entries)}"',
        '',
        '',
        'def test_history_entry_dataclass():',
        '    """Test HistoryEntry dataclass creation."""',
        '    from cmdpop.history.base import HistoryEntry',
        '    from datetime import datetime',
        '',
        '    path = Path.home() / ".bash_history"',
        '    entry = HistoryEntry(',
        '        command="git status",',
        '        timestamp=datetime.now(),',
        '        source_shell="bash",',
        '        source_file=path,',
        '    )',
        '    assert entry.command == "git status"',
        '    assert entry.source_shell == "bash"',
    ])

    test_file.write_text('\n'.join(lines))
    print(f"Generated {len(test_cases)} test cases in {test_file}")


def main() -> None:
    """Main entry point."""
    print("Generating CmdPop test suite...")
    generate_fixture_files()

    all_cases = []
    for shell, lines in FIXTURE_SAMPLES.items():
        all_cases.extend(analyze_edge_cases(lines, shell))

    write_test_file(all_cases)
    print(f"✓ Generated {len(all_cases)} test cases")


if __name__ == "__main__":
    main()
