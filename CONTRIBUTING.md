# Contributing to CmdPop

**Welcome!** This guide explains how to set up your environment, follow project conventions, and submit changes.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ (see `pyproject.toml`) | Language runtime |
| pip | Latest | Dependency manager |
| git | 2.30+ | Version control |

---

## Getting Started

### 1. Clone & Setup

```bash
# Clone repository
git clone https://github.com/Arnav1771/Popup_pop.git
cd Popup_pop

# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### 2. Verify Setup

```bash
# Run tests
pytest tests/ -v

# Run type check
mypy src/cmdpop/

# Run linter
ruff check src/ tests/

# Format code
black src/ tests/
isort src/ tests/
```

If all pass, you're ready to code.

---

## Project Structure

See `docs/sprint0/TECH_STACK.md` for detailed module layout.

Quick overview:
```
Popup_pop/
├── src/cmdpop/         # Main package
│   ├── main.py         # CLI entry point
│   ├── app.py          # Textual TUI
│   ├── history/        # Shell history readers
│   ├── injector/       # Command injection
│   ├── storage/        # SQLite DB layer
│   ├── config/         # Configuration
│   └── utils/          # Helper functions
├── tests/              # Test suite
├── docs/               # Documentation
│   └── sprint0/        # Sprint 0 decisions
└── pyproject.toml      # Package metadata
```

---

## Code Conventions

### Style Guide

- **Line length:** 100 characters (enforced by ruff + black)
- **Import order:** isort profile "black"
- **Type hints:** Mandatory on all public functions (mypy --strict)
- **Docstrings:** Google-style, on all public modules/classes/functions

### Example Function

```python
"""
Module docstring: one-line summary.

Longer description if needed.
"""

def fetch_command_history(shell: str, max_items: int = 1000) -> List[str]:
    """
    Fetch command history from the specified shell.
    
    Args:
        shell: Name of the shell ("bash", "zsh", "fish", "powershell", "cmd")
        max_items: Maximum number of commands to fetch (default: 1000)
        
    Returns:
        List of commands, most recent first.
        
    Raises:
        FileNotFoundError: If shell history file not found.
        ValueError: If shell name is not supported.
        
    Example:
        >>> commands = fetch_command_history("bash")
        >>> print(len(commands))
        1000
    """
    if shell not in ("bash", "zsh", "fish", "powershell", "cmd"):
        raise ValueError(f"Unsupported shell: {shell}")
    
    history_file = _get_history_path(shell)
    if not history_file.exists():
        raise FileNotFoundError(f"History file not found: {history_file}")
    
    # Implementation...
    return commands[:max_items]
```

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Class | PascalCase | `CommandDB`, `HistoryEntry`, `WindowsInjector` |
| Function | snake_case | `fetch_history`, `inject_command` |
| Variable | snake_case | `max_history`, `is_favorite` |
| Constant | UPPER_SNAKE_CASE | `DEFAULT_HOTKEY`, `MAX_HISTORY` |
| Private | _leading_underscore | `_parse_extended_history` |
| Type | PascalCase | `List[str]`, `Optional[datetime]` |

### No Anti-Patterns

✅ **DO:**
```python
# Type hints on public functions
async def search(self, query: str) -> List[Command]:
    pass

# Structured logging
logger.info("Daemon started", extra={"pid": os.getpid()})

# Explicit error handling
try:
    db.add_command(cmd)
except sqlite3.IntegrityError:
    logger.warning(f"Duplicate command: {cmd.command}")
```

❌ **DON'T:**
```python
# No type hints
def search(query):
    pass

# No print statements (use logging)
print(f"Found command: {cmd}")

# Silent failures
try:
    db.add_command(cmd)
except:
    pass
```

---

## Commit Conventions

CmdPop uses **Conventional Commits** format:

```
<type>(<scope>): <short description>

<longer explanation if needed>

<optional footer>
```

### Types

| Type | When To Use | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(history): add fish shell reader` |
| `fix` | Bug fix | `fix(injector): handle special chars in windows` |
| `docs` | Documentation only | `docs(sprint0): add architecture diagram` |
| `style` | Code formatting (no logic change) | `style(config): format toml with black` |
| `refactor` | Code reorganization (no logic change) | `refactor(storage): extract db utilities` |
| `test` | New tests or test fixes | `test(dedup): add edge case for unicode` |
| `chore` | Tooling, deps, CI (no code change) | `chore(ci): pin ruff to 0.3.7` |
| `perf` | Performance improvement | `perf(search): cache fuzzy results` |

### Scopes

Scopes align with module structure:
- `history` — History readers
- `injector` — Command injection
- `storage` — SQLite layer
- `config` — Configuration
- `app` — Textual TUI
- `ci` — GitHub Actions
- `docs` — Documentation
- `sprint0`, `sprint1`, etc. — Sprint planning

### Examples

```
feat(history): add zsh EXTENDED_HISTORY parser

- Handle ':' prefix format
- Parse timestamp correctly
- Add tests with real zsh history fixtures

Closes #12
```

```
fix(injector): escape quotes in windows SendKeys

The Windows API doesn't handle double quotes well. Now escaping
them with backslashes.

Tested on Windows 10 and Windows 11.
```

```
docs(readme): add installation via pipx

Simple one-liner: pipx install cmdpop
```

### Breaking Changes

If commit introduces breaking changes, append `!` to type:

```
feat(config)!: rename hotkey setting to global_hotkey

BREAKING CHANGE: 'hotkey' in config.toml is now 'global_hotkey'
Existing configs will need updating. Provide migration script.
```

---

## Pull Request Process

### Before Opening a PR

1. **Branch name** follows convention:
   - `feat/sprint1-add-fuzzy-search`
   - `fix/issue-42-windows-injection`
   - `docs/add-troubleshooting`

2. **All checks pass locally:**
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   isort --check src/ tests/
   mypy src/cmdpop/
   pytest tests/ -v
   ```

3. **Commits follow conventions** (see above)

4. **Tests added** for new features:
   - Minimum 1 test per feature
   - All edge cases covered
   - Run: `pytest tests/ -v`

### PR Checklist

Use this template when opening a PR:

```markdown
## Description
<!-- What does this PR do? -->

## Changes
- [ ] New feature / bug fix / documentation / other (describe)
- [ ] Tested on: Windows / macOS / Linux (all if cross-platform)

## Checklist
- [ ] Branch name follows convention (feat/fix/docs/...)
- [ ] Commits follow Conventional Commits format
- [ ] All CI checks pass (ruff, black, isort, mypy, pytest)
- [ ] New tests added (or existing tests updated)
- [ ] Documentation updated (if user-facing change)
- [ ] No console.log / print statements in production code
- [ ] Related issue linked (if applicable)

## Testing
- [ ] Manual test: _describe how you tested_
- [ ] Automated tests: _list test files_

## Related Issues
Closes #NNN (if applicable)
```

### Code Review

Expected feedback:
- **Style:** Follow conventions (ruff, black, etc. should catch these)
- **Logic:** Does this match the architecture? (see `docs/sprint0/`)
- **Tests:** Is coverage sufficient?
- **Docs:** Are changes documented?

Your PR must:
1. ✅ Pass all CI checks
2. ✅ Have at least 1 peer review
3. ✅ Have tests (new features)
4. ✅ Have documentation (if user-facing)

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_history_readers.py -v

# Run specific test
pytest tests/test_history_readers.py::test_bash_simple -v

# With coverage
pytest tests/ --cov=src/cmdpop --cov-report=html
```

### Test Organization

Tests go in `tests/` directory:
```
tests/
├── test_history_readers.py      # History reader tests (auto-generated)
├── test_storage.py              # Database tests
├── test_fuzzy_search.py         # Search ranking tests
├── test_injector.py             # Injection tests (mocked)
├── test_dedup.py                # Deduplication tests
├── conftest.py                  # Fixtures
├── generate_tests.py            # Auto-test generator
└── fixtures/
    └── history_samples/         # Real shell history samples
```

### Writing Tests

```python
import pytest
from cmdpop.history import BashReader
from cmdpop.storage import CommandDB

@pytest.mark.asyncio
async def test_add_and_retrieve_command():
    """Test that commands can be added and retrieved."""
    db = CommandDB(":memory:")
    
    cmd = Command(
        command="git status",
        shell="bash",
        timestamp=datetime.now(),
        source_file="/home/user/.bash_history"
    )
    
    await db.add_command(cmd)
    result = await db.get_command_by_id(1)
    
    assert result.command == "git status"
    assert result.shell == "bash"
```

### Auto-Generated Tests

History readers generate tests from fixtures:

```bash
# Regenerate tests from fixture files
python tests/generate_tests.py

# Then run them
pytest tests/test_history_readers.py -v
```

---

## Local Commands

### Development

```bash
# Install in editable mode
pip install -e ".[dev]"

# Format code (run before committing)
black src/ tests/
isort src/ tests/

# Check code
ruff check src/ tests/
mypy src/cmdpop/

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src/cmdpop --cov-report=html
open htmlcov/index.html  # View report
```

### CLI Testing

```bash
# After install -e
cmdpop --help
cmdpop config
cmdpop start    # Start daemon
cmdpop stop     # Stop daemon
cmdpop status   # Check if running
cmdpop sync     # Manually sync history
```

---

## Documentation

All user-facing changes need documentation:

- **New feature?** Update `README.md`
- **New setting?** Update `docs/sprint0/TECH_STACK.md` (config section)
- **New architectural decision?** Update `docs/sprint0/DECISIONS.md`
- **API change?** Update module docstrings

---

## Troubleshooting

### Import Errors

```
ModuleNotFoundError: No module named 'cmdpop'
```

**Fix:** Make sure you're in the right virtual environment:
```bash
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -e ".[dev]"
```

### Test Failures

```
AssertionError: assert [] == [Command(...)]
```

**Fix:** Check if fixtures exist:
```bash
python tests/generate_tests.py
pytest tests/ -v
```

### CI Failures

If GitHub Actions fails, run locally:
```bash
ruff check src/ tests/
black --check src/ tests/
mypy src/cmdpop/
pytest tests/ -v
```

---

## Questions?

- Check `docs/sprint0/` for architecture/decisions
- Check existing issues for similar problems
- Ask in PR comments or discussions

---

## License

By contributing, you agree to license your work under MIT (same as CmdPop).

---

> Contributing to CmdPop · May 2026
