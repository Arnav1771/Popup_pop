# Tech Stack — CmdPop

**Version:** v0.1  
**Status:** DECIDED (Sprint 0)  
**Focus:** Language, libraries, versions, local development setup  

---

## Language & Runtime

| Component | Version | Rationale |
|-----------|---------|-----------|
| Python | 3.11+ (strict) | Type hints, async/await maturity, stdlib tomllib |
| Minimum | 3.11.0 | tomllib became built-in; simplifies dependency management |

---

## Core Dependencies

All versions are **pinned exactly** (no version ranges) to ensure reproducibility.

```toml
[project]
requires-python = ">=3.11"

dependencies = [
    "textual==0.75.1",              # TUI framework
    "rapidfuzz==3.8.1",             # Fuzzy search
    "aiosqlite==3.2.0",             # Async SQLite
    "pynput==1.7.7",                # Global hotkey listener
    "pyautogui==0.9.54",            # Command injection fallback
    "pyperclip==1.8.2",             # Clipboard fallback
    "rich==13.7.0",                 # Terminal formatting
    "pywin32==308; sys_platform == 'win32'",  # Windows-only
]
```

### Core Library Details

| Library | Version | Why | Platform | Purpose |
|---------|---------|-----|----------|---------|
| **textual** | 0.75.1 | Stable, CSS-based layout, testable | All | TUI picker overlay |
| **rapidfuzz** | 3.8.1 | Fast fuzzy matching, pure Python | All | Search ranking |
| **aiosqlite** | 3.2.0 | Async SQLite wrapper | All | Non-blocking DB access |
| **pynput** | 1.7.7 | Cross-platform hotkey listener | All | Global hotkey detection |
| **pyautogui** | 0.9.54 | Screenshot + keyboard control | All | Injection fallback |
| **pyperclip** | 1.8.2 | Cross-platform clipboard | All | Clipboard fallback |
| **rich** | 13.7.0 | Terminal formatting | All | Error messages, styling |
| **pywin32** | 308 | Windows API bindings | Windows | Win32 SendKeys injection |

---

## Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest==7.4.4",                # Test runner
    "pytest-asyncio==0.23.2",       # Async test support
    "pytest-textual-snapshot==0.9.0",  # Textual snapshot tests
    "ruff==0.3.7",                  # Linter & formatter
    "mypy==1.9.0",                  # Type checker
    "black==24.3.0",                # Code formatter
    "isort==5.13.2",                # Import sorter
]
```

### Dev Library Details

| Tool | Version | Purpose |
|------|---------|---------|
| **pytest** | 7.4.4 | Test runner |
| **pytest-asyncio** | 0.23.2 | Fixture support for async tests |
| **pytest-textual-snapshot** | 0.9.0 | Snapshot testing for Textual TUI |
| **ruff** | 0.3.7 | Fast Python linter (replaces pylint, flake8) |
| **mypy** | 1.9.0 | Static type checker (strict mode) |
| **black** | 24.3.0 | Code formatter (opinionated) |
| **isort** | 5.13.2 | Import organizer |

---

## Tool Configuration

### Ruff (Linter)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "C4",   # flake8-comprehensions
    "B",    # flake8-bugbear
    "PIE",  # flake8-pie
]
```

### MyPy (Type Checker)

```toml
[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true
disallow_untyped_calls = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_unused_configs = true
```

### Black (Formatter)

```toml
[tool.black]
line-length = 100
target-version = ["py311"]
```

### isort (Import Sorter)

```toml
[tool.isort]
profile = "black"
line_length = 100
multi_line_mode = 3  # Vertical hanging indent
```

### Pytest (Test Runner)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --tb=short --strict-markers"
markers = [
    "integration: integration tests (slow)",
    "snapshot: snapshot tests",
]
```

---

## Dependency Graph

```
cmdpop (main package)
  ├── textual (TUI)
  │   └── (async, CSS)
  ├── aiosqlite (Async DB)
  │   └── sqlite3 (stdlib)
  ├── rapidfuzz (Fuzzy search)
  │   └── (C extensions for speed)
  ├── pynput (Global hotkey)
  │   └── (OS APIs via ctypes/win32)
  ├── pyautogui (Injection fallback)
  │   └── (OS-specific screenshots/input)
  ├── pyperclip (Clipboard fallback)
  │   └── (OS-specific clipboard)
  ├── rich (Terminal formatting)
  │   └── (colorama for Windows)
  └── pywin32 (Windows only)
      └── (Windows COM/Win32 APIs)
```

---

## Module Structure

```
src/cmdpop/
├── __init__.py                  # Package root
├── main.py                      # CLI entry point (cmdpop command)
├── app.py                       # Textual TUI application
│
├── history/
│   ├── __init__.py
│   ├── base.py                  # Abstract HistoryReader
│   ├── bash_reader.py           # ~/.bash_history
│   ├── zsh_reader.py            # ~/.zsh_history (EXTENDED_HISTORY)
│   ├── fish_reader.py           # ~/.local/share/fish/fish_history
│   ├── powershell_reader.py     # PSReadLine history (Windows/macOS/Linux)
│   ├── cmd_reader.py            # Clink history (Windows only)
│   ├── aggregator.py            # HistoryAggregator — orchestrates all readers
│   └── deduplicator.py          # Deduplication + merging logic
│
├── injector/
│   ├── __init__.py
│   ├── base.py                  # Abstract Injector
│   ├── windows.py               # Windows injector (pywin32 + fallback)
│   ├── mac.py                   # macOS injector (osascript)
│   ├── linux.py                 # Linux injector (xdotool, ydotool)
│   ├── factory.py               # InjectorFactory for platform detection
│   └── fallback.py              # Clipboard + notification fallback
│
├── storage/
│   ├── __init__.py
│   ├── db.py                    # SQLite database layer (async)
│   ├── schema.py                # Database schema definition
│   └── migrations.py            # Schema versioning
│
├── config/
│   ├── __init__.py
│   ├── settings.py              # Config loader + validation
│   └── defaults.py              # Default configuration
│
├── utils/
│   ├── __init__.py
│   ├── platform.py              # OS/shell detection helpers
│   ├── logging.py               # Structured logging
│   └── decorators.py            # Common decorators (retry, timeout, etc.)
│
└── daemon/
    ├── __init__.py
    ├── manager.py               # Daemon lifecycle management
    └── hotkey_handler.py        # Hotkey callback
```

---

## Local Development Setup

### Prerequisites

- **Python 3.11+** (check: `python --version`)
- **pip** (included with Python)
- **git** (for version control)

### Quick Start

```bash
# 1. Clone repo
git clone https://github.com/Arnav1771/Popup_pop.git
cd Popup_pop

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install in development mode with all dev dependencies
pip install -e ".[dev]"

# 4. Run tests to verify setup
pytest tests/ -v

# 5. Run type checking
mypy src/cmdpop/

# 6. Run linter
ruff check src/ tests/

# 7. Format code
black src/ tests/
isort src/ tests/
```

### IDE Setup (Recommended: VS Code + Pylance)

**.vscode/settings.json:**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "ruff.importStrategy": "fromEnvironment"
}
```

### Running Tests Locally

```bash
# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src/cmdpop --cov-report=html

# Run only unit tests (skip integration)
pytest tests/ -m "not integration"

# Run specific test file
pytest tests/test_history_readers.py -v

# Run specific test
pytest tests/test_history_readers.py::test_bash_simple -v

# Generate test cases from fixtures
python tests/generate_tests.py

# Run with debug output
pytest tests/ -v -s          # -s shows print statements
RUST_LOG=debug pytest tests/ # (if using Rust bindings later)
```

### Manual Testing

```bash
# Build package
pip install build
python -m build

# Test CLI entry point (after install -e)
cmdpop --help
cmdpop config
cmdpop start          # Starts daemon
cmdpop stop           # Stops daemon
cmdpop sync           # Manually sync history

# Check daemon status
cmdpop status
ps aux | grep cmdpop  # On Unix
tasklist | grep cmdpop  # On Windows
```

### Debugging

```bash
# Enable debug logging
# Set log_level = "debug" in ~/.cmdpop/config.toml

# Check log file
cat ~/.cmdpop/debug.log

# Run daemon in foreground (for debugging)
cmdpop start --foreground --debug

# Test hotkey binding
python -c "from pynput import keyboard; listener = keyboard.Listener(on_press=lambda k: print(f'Pressed: {k}')); listener.start(); input('Press Ctrl+C to exit...'); listener.stop()"

# Test injection
python -c "from src.cmdpop.injector import InjectorFactory; injector = InjectorFactory.get_injector(); injector.inject('echo hello')"
```

---

## CI/CD Pipeline

### GitHub Actions (see `.github/workflows/ci.yml`)

```yaml
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install ruff black isort
      - run: ruff check src/ tests/
      - run: black --check src/ tests/
      - run: isort --check src/ tests/

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install mypy
      - run: mypy src/cmdpop/

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
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --cov=src/cmdpop
```

---

## Versioning Scheme

**CmdPop uses Semantic Versioning (SemVer):**

- **MAJOR**: Breaking API changes (e.g., config file format change)
- **MINOR**: New features, backward-compatible
- **PATCH**: Bug fixes, no new features

Example: `v0.1.0` → `v0.2.0` → `v0.2.1` → `v1.0.0`

Git tags: `v0.1.0`, `v0.2.0`, etc.

PyPI release is automatic on tag push (CI/CD).

---

## Performance Targets & Optimization

| Operation | Target | How Achieved |
|-----------|--------|-------------|
| Daemon startup | < 2s | Lazy-load history on first hotkey press |
| Hotkey → picker | < 500ms | Async TUI, preloaded DB queries |
| Fuzzy search (10k items) | < 100ms | Index query, limit results to top 1000 |
| DB write (add command) | < 50ms | Async aiosqlite, no sync barrier |
| Memory (daemon) | < 100MB | Stream history reads, limit in-memory cache |

---

## Backward Compatibility

- **Config format**: TOML; if schema changes, provide migration script
- **Database schema**: Versioned; migrations applied on startup
- **CLI commands**: Documented; deprecated flags get warnings, then removed in major version

---

## Security Hardening

- **No hardcoded credentials**: All sensitive config in `~/.cmdpop/config.toml`
- **DB file permissions**: `chmod 600 ~/.cmdpop/history.db` (owner only)
- **No network calls**: All local, no telemetry, no cloud sync
- **Command filtering**: Exclude patterns prevent sensitive commands storage
- **Input validation**: Config values validated; CLI args sanitized

---

## Documentation

- **README.md**: Installation, usage, features
- **CONTRIBUTING.md**: Development setup, code style, PR process
- **docs/sprint0/**: Architecture, decisions, tech stack
- **Code docstrings**: Google-style docstrings on all public APIs
- **Examples**: `examples/` directory with sample config, scripts

---

> CmdPop Tech Stack · Sprint 0 · May 2026
