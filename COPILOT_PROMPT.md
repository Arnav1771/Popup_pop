# GitHub Copilot Workspace Prompt — CmdPop
## Copy everything below this line into Copilot's prompt / workspace instructions

---

## PROJECT: CmdPop — Cross-Platform Terminal Command History Picker

You are building **CmdPop**, a standalone Python CLI tool that acts like Windows+V (clipboard history popup) but exclusively for terminal commands. It works across ALL shells and ALL operating systems with zero shell plugin installation required.

---

## CONTEXT: What Already Exists (and Why We're Different)

Before writing any code, understand the competitive landscape:

- **fzf**: General fuzzy finder, needs shell integration, not a floating overlay
- **Atuin**: Great shell history tool but requires a shell plugin (bash/zsh/fish only), no Windows CMD support
- **McFly**: Neural-net history search, shell plugin required, Linux/Mac only
- **F7History**: PowerShell module, PowerShell only
- **PSReadLine Ctrl+R**: PowerShell only

**CmdPop's unique value**: Shell-agnostic, no plugin needed, reads history files directly, works in any terminal window on Windows/Mac/Linux, floating TUI overlay with fuzzy search, injects selected command back into the terminal.

---

## TECH STACK (do not deviate from this)

- **Language**: Python 3.11+
- **TUI**: `textual` library (for the floating command picker overlay)
- **Fuzzy Search**: `rapidfuzz` 
- **Database**: SQLite via `aiosqlite` (persistent cross-session history)
- **Global Hotkey**: `pynput`
- **Command Injection**: `pyautogui` + platform-specific overrides
- **Config**: `tomllib` (Python 3.11 stdlib, no extra dep)
- **Testing**: `pytest` + `pytest-asyncio` + `pytest-textual-snapshot`
- **Packaging**: `pyproject.toml` (installable via `pipx install cmdpop`)

---

## PROJECT STRUCTURE

Create exactly this directory structure:

```
cmdpop/
├── src/
│   └── cmdpop/
│       ├── __init__.py
│       ├── main.py                   # CLI entry point + hotkey daemon
│       ├── app.py                    # Textual TUI App class
│       ├── history/
│       │   ├── __init__.py
│       │   ├── base.py               # Abstract HistoryReader base class
│       │   ├── bash_reader.py        # Parses ~/.bash_history
│       │   ├── zsh_reader.py         # Parses ~/.zsh_history (EXTENDED_HISTORY aware)
│       │   ├── fish_reader.py        # Parses ~/.local/share/fish/fish_history (YAML)
│       │   ├── powershell_reader.py  # Parses PSReadLine ConsoleHost_history.txt
│       │   └── cmd_reader.py         # Parses Clink .history on Windows
│       ├── injector/
│       │   ├── __init__.py
│       │   ├── base.py               # Abstract Injector base class
│       │   ├── windows.py            # win32api SendKeys
│       │   ├── linux.py              # xdotool type (X11), ydotool (Wayland)
│       │   └── mac.py                # osascript AppleScript
│       ├── storage/
│       │   ├── __init__.py
│       │   └── db.py                 # SQLite: schema, CRUD, migrations
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py           # TOML config loader + defaults
│       └── utils/
│           ├── __init__.py
│           └── platform.py           # OS detection, shell detection
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Shared fixtures
│   ├── generate_tests.py             # SELF-BUILDING test generator script
│   ├── fixtures/
│   │   └── history_samples/
│   │       ├── bash.txt              # Sample bash history lines
│   │       ├── zsh_plain.txt         # Plain zsh history
│   │       ├── zsh_extended.txt      # EXTENDED_HISTORY format
│   │       ├── fish.txt              # Fish YAML history format
│   │       ├── powershell.txt        # PSReadLine history format
│   │       └── cmd_clink.txt         # Clink history format
│   ├── test_history_readers.py       # (initially empty, filled by generator)
│   ├── test_dedup.py
│   ├── test_fuzzy_search.py
│   ├── test_injector.py
│   ├── test_storage.py
│   └── snapshots/                    # Textual TUI snapshots
│
├── pyproject.toml
├── README.md
└── .github/
    └── workflows/
        └── ci.yml
```

---

## IMPLEMENTATION REQUIREMENTS

### 1. HistoryReader Base Class (`src/cmdpop/history/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class HistoryEntry:
    command: str
    timestamp: datetime | None
    source_shell: str   # "bash" | "zsh" | "fish" | "powershell" | "cmd"
    source_file: Path

class HistoryReader(ABC):
    @abstractmethod
    def get_history_path(self) -> Path | None:
        """Return path to history file, or None if shell not installed."""
        ...
    
    @abstractmethod
    def parse(self, content: str) -> list[HistoryEntry]:
        """Parse raw history file content into entries."""
        ...
    
    def read(self) -> list[HistoryEntry]:
        """Read and parse history. Returns [] if file not found."""
        path = self.get_history_path()
        if not path or not path.exists():
            return []
        try:
            return self.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (PermissionError, OSError):
            return []
```

### 2. Shell-Specific Readers

**bash_reader.py**: Read `~/.bash_history`. One command per line. Skip blank lines. Handle `HISTTIMEFORMAT` lines starting with `#<timestamp>`.

**zsh_reader.py**: Read `~/.zsh_history`. Two formats:
- Plain: one command per line
- Extended: `: <unix_timestamp>:<elapsed>;<command>` — MUST handle multi-line commands (continuation with `\` at end of line)

**fish_reader.py**: Read `~/.local/share/fish/fish_history`. YAML-like format:
```
- cmd: git commit -m "fix"
  when: 1698765432
- cmd: npm run dev
  when: 1698765430
```
Use simple line-by-line parsing, NOT a YAML library (fish format is subset).

**powershell_reader.py**: Read `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` on Windows, or `~/.local/share/powershell/PSReadLine/ConsoleHost_history.txt` on Linux/Mac. One command per line.

**cmd_reader.py**: Read `%LOCALAPPDATA%\clink\.history` on Windows. One command per line. Return [] on non-Windows.

### 3. Storage (`src/cmdpop/storage/db.py`)

SQLite schema:
```sql
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    source_shell TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_count INTEGER DEFAULT 1,
    is_favorite INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_commands_text ON commands(command);
```

Required functions:
- `async def upsert_commands(entries: list[HistoryEntry]) -> None` — Insert or update run_count/last_seen
- `async def search(query: str, limit: int = 100) -> list[CommandRow]` — Fuzzy search using rapidfuzz
- `async def toggle_favorite(command: str) -> bool` — Toggle and return new state
- `async def delete_command(command: str) -> None`
- `async def get_all(limit: int = 500) -> list[CommandRow]` — Most recent first

Database location: `~/.cmdpop/history.db`. Create directory if not exists.

### 4. Textual TUI App (`src/cmdpop/app.py`)

Build a `textual` App with:
- **SearchInput**: A text input at the top for fuzzy filtering
- **CommandList**: A `ListView` showing commands. Each item shows: favorite star, command text (truncated), source shell badge, relative time
- **PreviewPanel**: Bottom panel showing full command, timestamp, run count, source
- **Keyboard shortcuts**:
  - `Up/Down`: navigate list
  - `Enter`: select and inject command
  - `F` or `Ctrl+D`: toggle favorite
  - `Delete`: remove command from history
  - `Escape`: close without selecting
  - `Ctrl+A`: select all text in search

The app should be launched as a **floating overlay** (not full screen). Use `Screen` with fixed dimensions:
- Width: 60% of terminal width (min 60 chars)
- Height: 70% of terminal height (min 15 lines)
- Centered on screen

CSS styling (dark theme by default):
```css
CommandList {
    border: solid $primary;
    height: 1fr;
}
SearchInput {
    border: solid $accent;
    height: 3;
}
.favorite {
    color: yellow;
}
.source-badge {
    color: $text-muted;
}
```

### 5. Command Injector

**Base** (`injector/base.py`):
```python
from abc import ABC, abstractmethod

class Injector(ABC):
    @abstractmethod
    def inject(self, command: str) -> bool:
        """Inject command text into the active terminal. Returns True on success."""
        ...
    
    def inject_with_fallback(self, command: str) -> None:
        if not self.inject(command):
            import pyperclip
            pyperclip.copy(command)
            print(f"[CmdPop] Copied to clipboard: {command[:50]}...")
```

**Windows** (`injector/windows.py`): Use `pywin32` to find the active console window and send WM_CHAR messages. Fallback to `pyautogui.typewrite()`.

**Linux** (`injector/linux.py`): Try `subprocess.run(["xdotool", "type", "--clearmodifiers", command])`. If xdotool not found, try `ydotool type`. Fallback to clipboard.

**Mac** (`injector/mac.py`): Use `osascript -e 'tell application "Terminal" to do script ...'`. Fallback to `pyautogui.typewrite()`.

**Factory** (`injector/__init__.py`):
```python
import sys

def get_injector():
    if sys.platform == "win32":
        from .windows import WindowsInjector
        return WindowsInjector()
    elif sys.platform == "darwin":
        from .mac import MacInjector
        return MacInjector()
    else:
        from .linux import LinuxInjector
        return LinuxInjector()
```

### 6. Config (`src/cmdpop/config/settings.py`)

TOML config at `~/.cmdpop/config.toml`. Use `tomllib` to parse. Provide defaults for all settings:

```python
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
    }
}
```

Sensitive command filtering: before storing any command in SQLite, check if any word from `exclude_patterns` appears in the command (case-insensitive). If so, skip storage entirely.

### 7. Main Entry Point (`src/cmdpop/main.py`)

```python
import argparse

def main():
    parser = argparse.ArgumentParser(prog="cmdpop")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("start", help="Start CmdPop hotkey daemon")
    subparsers.add_parser("open", help="Open picker manually (no daemon)")
    subparsers.add_parser("sync", help="Sync shell history files into CmdPop DB now")
    subparsers.add_parser("generate-tests", help="Regenerate test suite from fixtures")
    subparsers.add_parser("config", help="Print current config path and values")
    
    args = parser.parse_args()
    
    match args.command:
        case "start" | None: start_daemon()
        case "open": open_picker()
        case "sync": sync_history()
        case "generate-tests": generate_tests()
        case "config": show_config()
```

`start_daemon()` uses `pynput.keyboard.GlobalHotKeys` to listen for the configured hotkey and call `open_picker()` in a thread.

---

## SELF-BUILDING TEST SYSTEM

### Test Generator (`tests/generate_tests.py`)

This is the most important part. Create a script that:

1. **Reads fixture files** from `tests/fixtures/history_samples/`
2. **Detects edge cases automatically**:
   - Empty lines → should be skipped
   - Lines starting with `#` in bash → timestamp markers, not commands
   - Lines with special shell chars: pipes, redirects, quotes, semicolons
   - Multi-line commands (zsh `\` continuation)
   - Duplicate commands
   - Commands with env vars: `FOO=bar git commit`
   - Very long commands (>500 chars)
   - Unicode/emoji in commands
3. **Generates parametrized tests** by writing Python code to `tests/test_history_readers.py`
4. **Creates fixture samples** if none exist — generates synthetic test data covering all edge cases

The generator script must be idempotent (safe to run multiple times).

```python
# tests/generate_tests.py

FIXTURE_SAMPLES = {
    "bash": [
        "git commit -m 'fix auth'",
        "npm run dev",
        "",                                    # empty → skip
        "# 1698765432",                        # bash timestamp → skip  
        "docker build -t myapp . --no-cache",
        "export SECRET_TOKEN=abc123",          # sensitive → excluded from DB
        "ls -la | grep '.py' | head -20",     # pipes
        "cd ~/Projects/myapp && git pull",     # compound
        "for f in *.txt; do echo $f; done",   # loop
        "git commit -m 'feat: add émojis 🎉'", # unicode
    ],
    "zsh_extended": [
        ": 1698765432:0;git status",
        ": 1698765431:0;git diff HEAD~1",
        ": 1698765430:120;npm install",       # with elapsed time
        ": 1698765429:0;git commit -m 'multi\\",  # multi-line start
        "line command'",                        # continuation
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

def generate_fixture_files():
    """Create sample history files if they don't exist."""
    ...

def analyze_edge_cases(lines: list[str], shell: str) -> list[dict]:
    """Return list of {input, expected_parsed, expected_command, reason}."""
    ...

def write_test_file(test_cases: list[dict]):
    """Write parametrized pytest file."""
    ...

def main():
    generate_fixture_files()
    all_cases = []
    for shell, lines in FIXTURE_SAMPLES.items():
        all_cases.extend(analyze_edge_cases(lines, shell))
    write_test_file(all_cases)
    print(f"Generated {len(all_cases)} test cases in tests/test_history_readers.py")

if __name__ == "__main__":
    main()
```

### Test Structure Requirements

**test_history_readers.py** (generated + manual sections):
```python
import pytest
# Auto-generated section — DO NOT EDIT MANUALLY, run generate_tests.py
@pytest.mark.parametrize("raw_line,shell,expected_command", [
    # ... generated cases ...
])
def test_reader_parse_line(raw_line, shell, expected_command):
    ...

# Manual section — safe to edit
def test_bash_reader_skips_timestamp_lines():
    ...

def test_zsh_extended_history_with_elapsed():
    ...

def test_fish_multientry_parse():
    ...
```

**test_storage.py**:
```python
async def test_upsert_increments_run_count():
    ...

async def test_sensitive_commands_excluded():
    # Commands with "password" should never appear in DB
    ...

async def test_search_returns_fuzzy_matches():
    ...

async def test_favorite_toggle():
    ...
```

**test_fuzzy_search.py**:
```python
def test_exact_match_ranks_first():
    ...

def test_partial_match_found():
    ...

def test_empty_query_returns_all():
    ...

def test_case_insensitive_search():
    ...
```

**test_injector.py**: Mock all OS calls. Test that:
- `inject()` calls the right OS function
- Falls back to clipboard when OS call fails
- Long commands (>1000 chars) work correctly
- Commands with quotes, backslashes are escaped properly

---

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "cmdpop"
version = "0.1.0"
description = "Cross-platform terminal command history picker — like Win+V for your terminal"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
keywords = ["terminal", "history", "cli", "tui", "productivity"]
dependencies = [
    "textual>=0.50.0",
    "rapidfuzz>=3.0.0",
    "aiosqlite>=0.19.0",
    "pynput>=1.7.6",
    "pyautogui>=0.9.54",
    "pyperclip>=1.8.2",
    "rich>=13.0.0",
    "pywin32>=306; sys_platform == 'win32'",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.21",
    "pytest-textual-snapshot",
    "ruff>=0.1.0",
    "mypy>=1.0",
]

[project.scripts]
cmdpop = "cmdpop.main:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

---

## CI (`/.github/workflows/ci.yml`)

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Generate tests from fixtures
        run: python tests/generate_tests.py
      
      - name: Run tests
        run: pytest tests/ -v --tb=short
      
      - name: Type check
        run: mypy src/cmdpop/
      
      - name: Lint
        run: ruff check src/ tests/
```

---

## CODING STANDARDS

1. **Type hints everywhere** — all function signatures must have full type annotations
2. **Docstrings on every class and public method**
3. **No bare `except:`** — always catch specific exceptions
4. **Async-first for storage** — all DB operations must be `async`
5. **Platform guards** — wrap any OS-specific import in `if sys.platform ==` checks
6. **No hardcoded paths** — always use `pathlib.Path` and `Path.home()`
7. **Logging not print** — use `logging.getLogger(__name__)` for debug output
8. **Fail gracefully** — if a history file can't be read, log warning and continue; never crash

---

## README REQUIREMENTS

The README must include:
1. One-line description
2. Install: `pipx install cmdpop`
3. Usage:
   ```
   cmdpop start         # Start hotkey daemon
   cmdpop open          # Open picker right now
   cmdpop sync          # Sync history files into DB
   cmdpop generate-tests  # Rebuild test suite
   ```
4. Hotkey: `Ctrl+Alt+H` opens the picker in any terminal
5. Supported shells table (bash, zsh, fish, PowerShell, CMD+Clink)
6. Config file location and example
7. How self-building tests work

---

## START HERE

Build in this exact order:
1. `pyproject.toml` and project structure
2. `src/cmdpop/history/base.py` — HistoryEntry + HistoryReader
3. All 5 shell readers with their tests
4. `src/cmdpop/storage/db.py` + `tests/test_storage.py`
5. `tests/generate_tests.py` — the self-building test generator
6. Run `python tests/generate_tests.py` and verify it creates valid test files
7. `src/cmdpop/app.py` — Textual TUI
8. `src/cmdpop/injector/` — all 3 platform injectors
9. `src/cmdpop/config/settings.py`
10. `src/cmdpop/main.py` — CLI entry point + daemon
11. `pyproject.toml` scripts + packaging
12. CI workflow

**After each module is written, run `pytest tests/ -v` before moving to the next.**
