# 🖥️ CmdPop — Terminal Command History Picker
## Full Project Plan + GitHub Copilot Prompt

---

## 🔍 WHAT ALREADY EXISTS (Research Summary)

Before building, here's what's out there and why none of them fully solve this:

| Tool | What it does | Why it's NOT what we want |
|---|---|---|
| **fzf** | General-purpose fuzzy finder, pipe `history \| fzf` | Requires shell integration, not cross-platform natively, general-purpose not focused |
| **Atuin** | SQLite-backed history, TUI on Ctrl+R, syncs across machines | Requires shell plugin (bash/zsh/fish), NOT for Windows CMD natively |
| **McFly** | Neural-net history search | Shell plugin only, no Windows CMD, no standalone overlay |
| **F7History** | PowerShell F7 popup | PowerShell ONLY, not CMD, not bash/zsh |
| **PSReadLine** | PowerShell Ctrl+R search | PowerShell ONLY |
| **Clink** | CMD.exe enhancement on Windows | Windows CMD only, no cross-platform |
| **Win+V** | Clipboard history popup | General clipboard, NOT terminal-specific, not cross-platform |

### 🎯 The Gap CmdPop Fills
A **standalone, shell-agnostic, cross-platform floating TUI** that:
- Works in ANY terminal (CMD, PowerShell, bash, zsh, fish) on Windows, Mac, Linux
- Needs **zero shell plugins** — reads history files directly
- Shows a **floating overlay** above the terminal with fuzzy search
- Injects the selected command back into the active terminal
- Persists history across sessions in its own SQLite database
- Has **self-generating tests**

---

## 🧱 PROJECT ARCHITECTURE

```
cmdpop/
├── src/
│   └── cmdpop/
│       ├── __init__.py
│       ├── main.py               # Entry point, hotkey daemon
│       ├── app.py                # Textual TUI application
│       ├── history/
│       │   ├── __init__.py
│       │   ├── base.py           # Abstract HistoryReader
│       │   ├── bash_reader.py    # ~/.bash_history
│       │   ├── zsh_reader.py     # ~/.zsh_history (handles EXTENDED_HISTORY)
│       │   ├── fish_reader.py    # ~/.local/share/fish/fish_history
│       │   ├── powershell_reader.py  # PSReadLine history file
│       │   └── cmd_reader.py     # Clink history / doskey
│       ├── injector/
│       │   ├── __init__.py
│       │   ├── base.py           # Abstract Injector
│       │   ├── windows.py        # pywin32 SendKeys to terminal
│       │   ├── linux.py          # xdotool / ydotool
│       │   └── mac.py            # AppleScript / pyautogui
│       ├── storage/
│       │   ├── __init__.py
│       │   └── db.py             # SQLite persistence, dedup, favorites
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py       # TOML config, hotkey, theme
│       └── utils/
│           ├── __init__.py
│           └── platform.py       # OS detection helpers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Fixtures + test generator bootstrap
│   ├── generate_tests.py         # Self-building test generator
│   ├── test_history_readers.py   # Auto-generated + manual
│   ├── test_dedup.py
│   ├── test_fuzzy_search.py
│   ├── test_injector.py
│   ├── test_storage.py
│   └── snapshots/                # Textual TUI snapshots
│
├── pyproject.toml
├── README.md
├── PLAN.md                       # This file
└── .github/
    └── workflows/
        └── ci.yml
```

---

## 🚀 CORE FEATURES (MVP)

### 1. Universal History Reading
- Detect installed shells automatically
- Parse each shell's history format:
  - **bash**: `~/.bash_history` (plain text, one per line)
  - **zsh**: `~/.zsh_history` (with optional `: <timestamp>:0;<cmd>` format)
  - **fish**: `~/.local/share/fish/fish_history` (YAML-like)
  - **PowerShell**: `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt`
  - **CMD/Clink**: `%LOCALAPPDATA%\clink\.history`
- Merge all sources, deduplicate, sort by recency

### 2. Floating TUI Overlay (Textual)
- Hotkey: `Ctrl+Alt+H` (configurable) to open overlay
- Fuzzy search input at top
- Scrollable list of commands (most recent first)
- Keyboard: `↑/↓` to navigate, `Enter` to select, `Esc` to cancel
- Preview panel showing command details (timestamp, source shell, run count)
- Favorites marked with ★

### 3. Command Injection
- After selection, injects command text into the active terminal
- Uses OS-native APIs:
  - **Windows**: `win32api.SendMessage` / `pywin32` / `pyautogui`
  - **Linux**: `xdotool type` (X11) / `ydotool` (Wayland)
  - **Mac**: `osascript` AppleScript
- Fallback: copy to clipboard + notify user

### 4. Persistent Storage (SQLite)
- Every command CmdPop has seen goes into SQLite
- Tracks: command text, source shell, timestamp, run count, is_favorite
- Survives reboots; history never lost

### 5. Configuration (TOML)
```toml
[cmdpop]
hotkey = "ctrl+alt+h"
max_history = 10000
theme = "dark"          # dark | light | auto
inject_method = "auto"  # auto | clipboard | xdotool | win32

[history]
sources = ["auto"]      # auto-detect or list: ["bash", "zsh", "powershell"]
exclude_patterns = ["password", "secret", "token"]  # Never store these

[display]
height_percent = 60
width_percent = 50
position = "center"     # center | top | bottom
show_timestamps = true
show_source_shell = true
```

---

## 🧪 SELF-BUILDING TESTS

### How Tests Build Themselves
The `generate_tests.py` script:
1. Reads real shell history sample files from `tests/fixtures/`
2. Analyzes edge cases (empty lines, timestamps, special chars, duplicates)
3. Generates `test_history_readers.py` parametrize decorators automatically
4. Writes snapshot tests for every TUI screen state
5. Creates regression tests from any discovered parsing failures

```python
# tests/generate_tests.py — example of what gets generated

def generate_reader_tests():
    """Auto-generates parametrized test cases from fixture files."""
    fixtures = Path("tests/fixtures/history_samples")
    test_cases = []
    
    for fixture_file in fixtures.glob("*.txt"):
        shell_type = fixture_file.stem  # e.g. "bash", "zsh_extended"
        lines = fixture_file.read_text().splitlines()
        
        for i, line in enumerate(lines):
            test_cases.append({
                "id": f"{shell_type}_line_{i}",
                "input": line,
                "shell": shell_type,
                "expected_parsed": should_parse_as_command(line, shell_type),
            })
    
    write_parametrized_tests(test_cases, "tests/test_history_readers.py")
```

### Test Categories
```
tests/
├── test_history_readers.py    ← auto-generated from fixture samples
├── test_dedup.py              ← deduplication logic edge cases
├── test_fuzzy_search.py       ← search scoring, ranking
├── test_injector.py           ← mocked OS calls, injection strings
├── test_storage.py            ← SQLite CRUD, migrations
└── test_app_snapshots.py      ← Textual TUI visual regression tests
```

### Self-Test Command
```bash
# Run this once to bootstrap all tests from real history fixtures:
python tests/generate_tests.py

# Then run all tests normally:
pytest tests/ -v --tb=short
```

---

## 🛠️ TECH STACK

| Layer | Technology | Why |
|---|---|---|
| Language | **Python 3.11+** | Cross-platform, rich ecosystem, easiest for Copilot |
| TUI Framework | **Textual** (`textual`) | Best modern Python TUI, CSS-based, testable |
| Fuzzy Search | **rapidfuzz** | Fast, Levenshtein + token sort, pure Python wheels |
| Database | **SQLite** via `aiosqlite` | Zero-config, embedded, cross-platform |
| Global Hotkey | **pynput** | Cross-platform keyboard listener |
| Command Injection | **pyautogui** + OS APIs | Cross-platform with platform overrides |
| Config | **tomllib** (stdlib 3.11) | Built-in, no extra dependency |
| Testing | **pytest** + **pytest-asyncio** + **textual** snapshots | Full coverage |
| Packaging | **pyproject.toml** + **pipx** | Easy global install |
| CI | **GitHub Actions** (matrix: win/mac/linux) | Cross-platform validation |

---

## 📦 DEPENDENCIES

```toml
[project]
name = "cmdpop"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.50.0",
    "rapidfuzz>=3.0.0",
    "aiosqlite>=0.19.0",
    "pynput>=1.7.6",
    "pyautogui>=0.9.54",
    "pywin32>=306; sys_platform == 'win32'",
    "pyperclip>=1.8.2",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.21",
    "pytest-textual-snapshot",
    "ruff",
    "mypy",
]

[project.scripts]
cmdpop = "cmdpop.main:main"
cmdpop-generate-tests = "tests.generate_tests:main"
```

---

## 🖥️ UI DESIGN

```
╔══════════════════════════════════════════════════╗
║  ⌨  CmdPop — Command History          [Esc] Close ║
╠══════════════════════════════════════════════════╣
║  🔍  git commit -m "                             ║
╠══════════════════════════════════════════════════╣
║  ★  git commit -m "fix: auth bug"    bash  2m ago ║
║     git commit -m "feat: add login"  zsh   1h ago ║
║     git commit -am "wip"             bash  3h ago ║
║     git push origin main             ps    5h ago ║
║     docker build -t myapp .          bash 1d ago  ║
║     npm run dev                      fish 1d ago  ║
║  ─────────────────────────────────────────────   ║
║  [Enter] Insert  [F] Favorite  [Del] Remove       ║
╚══════════════════════════════════════════════════╝
```

---

## 🗺️ IMPLEMENTATION PHASES

### Phase 1: History Reading + Storage (Week 1)
- [ ] `HistoryReader` base class + all 5 shell parsers
- [ ] SQLite schema + CRUD operations
- [ ] Deduplication + merge logic
- [ ] Unit tests (auto-generated from fixtures)

### Phase 2: TUI Overlay (Week 2)
- [ ] Textual app with fuzzy search input
- [ ] Scrollable command list
- [ ] Keyboard navigation
- [ ] Favorites system
- [ ] TUI snapshot tests

### Phase 3: Command Injection (Week 3)
- [ ] Windows injector (pyautogui + win32)
- [ ] Linux injector (xdotool + ydotool fallback)
- [ ] Mac injector (AppleScript + pyautogui fallback)
- [ ] Clipboard fallback for all platforms
- [ ] Integration tests (mocked)

### Phase 4: Hotkey Daemon + Config (Week 4)
- [ ] Background pynput listener
- [ ] TOML config parsing
- [ ] `cmdpop` CLI entry point
- [ ] `cmdpop --install-autostart` helper

### Phase 5: Packaging + CI (Week 5)
- [ ] pyproject.toml + pipx install
- [ ] GitHub Actions matrix (Windows, Ubuntu, macOS)
- [ ] README with install/usage GIF

---

## ⚠️ KNOWN CHALLENGES

1. **Command injection on Wayland** — xdotool doesn't work; need ydotool (requires uinput permissions)
2. **Windows CMD history** — CMD doesn't save history between sessions natively; users need Clink installed, or we intercept via PSReadLine only
3. **Sensitive commands** — Must exclude patterns like passwords/tokens from storage
4. **zsh EXTENDED_HISTORY format** — `: 1698765432:0;git commit` format needs special parser
5. **Fish YAML history** — Fish writes `- cmd: git commit\n  when: 1698765432` format

---

## 🔒 SECURITY

- `exclude_patterns` in config filters sensitive commands before storage
- SQLite DB stored at `~/.cmdpop/history.db` with 600 permissions (owner read/write only)
- No network calls, fully local
- No plaintext logging of commands

---

