# Architectural Decisions — CmdPop

**Version:** v0.1  
**Sprint:** Sprint 0  
**Status:** All decisions DECIDED or DEFERRED (no OPEN decisions)  
**Last Updated:** 2026-05-24  

---

## Decision Format

Each decision follows this structure:

```
## D-NNN: Short Title

**Question:** What is the core question being answered?

**Decision:** What did we choose?

**Alternatives Considered:**
- Alternative A: why we rejected it
- Alternative B: why we rejected it

**Rationale:** Why this decision is the right one (constraints, risks, dependencies)

**Status:** DECIDED | DEFERRED

**Depends On:** (if any prior decisions)

**Blocks:** (if any downstream decisions)

**Revisit Date:** (if time-bound, e.g., after Sprint 1 proof-of-concept)
```

---

## D-001: Database Technology

**Question:** What database should CmdPop use for persistent command history?

**Decision:** **SQLite** (via `aiosqlite` for async access)

**Alternatives Considered:**
- PostgreSQL: Overkill for single-user tool; requires external service; adds deployment complexity
- Redis: In-memory; not suitable for persistent history across reboots
- File-based JSON: No querying, slow for 10k+ items, no atomic writes
- DuckDB: Interesting but less mature than SQLite

**Rationale:**
- Zero configuration — database file lives at `~/.cmdpop/history.db`
- Embedded, no server needed — user runs `pipx install cmdpop` and immediately has working persistence
- Cross-platform — same code runs on Windows, macOS, Linux unchanged
- Battle-tested — SQLite powers Firefox, Chromium, millions of apps
- Async support via aiosqlite prevents UI blocking during queries
- Sufficient for 100k+ commands (our scalability target)
- RLS (row-level security) not needed — single-user tool

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** D-008 (schema design)

**Revisit Date:** After Sprint 1 if query performance degrades >500ms for 10k items

---

## D-002: Hotkey Listener

**Question:** How should CmdPop detect when the user presses the configured hotkey?

**Decision:** **pynput** library for global hotkey listening

**Alternatives Considered:**
- Shell-specific hotkey integration (bash/zsh/fish hooks): Not universal; doesn't work in Windows CMD
- OS-level keybinding APIs (Win32, Cocoa, X11): More complex; hard to distribute; platform-specific code
- Python keyboard library: Good, but pynput is more mature and widely tested

**Rationale:**
- Cross-platform: Single code path for Windows, macOS, Linux
- No shell integration needed — works in ANY terminal
- Runs in background daemon — not tied to shell lifetime
- Simple to configure — just `hotkey = "ctrl+alt+h"` in config
- Proven: Used by many Python CLI tools

**Status:** **DECIDED**

**Depends On:** D-003 (daemon architecture)

**Blocks:** None

**Revisit Date:** Never; proven approach

---

## D-003: Architecture: Daemon vs. One-Shot

**Question:** Should CmdPop be a background daemon or a one-shot CLI that exits after each use?

**Decision:** **Background daemon** that runs continuously and listens for global hotkey

**Alternatives Considered:**
- One-shot CLI: Fast startup but requires user to manually type `cmdpop open` every time (defeats purpose of hotkey)
- Desktop integration via systemd/LaunchAgent: Too heavy; daemon approach simpler

**Rationale:**
- Hotkey listening requires persistent background process
- Daemon is lightweight (just listening, not CPU-intensive)
- Daemon survives terminal close — always available
- Autostart (optional) via OS-level configuration (systemd, LaunchAgent)
- User still has one-shot options: `cmdpop open` (manual), `cmdpop sync` (manual refresh)

**Status:** **DECIDED**

**Depends On:** D-002 (hotkey listening)

**Blocks:** None

**Revisit Date:** Never; core architecture decision

---

## D-004: TUI Framework

**Question:** What framework should CmdPop use to build the interactive picker overlay?

**Decision:** **Textual** (modern Python TUI library)

**Alternatives Considered:**
- Curses: Industry standard but outdated API; poor Windows support
- urwid: Good but steeper learning curve; less maintained
- Rich (tables only): Not interactive; would need custom input handling
- Web-based (Flask + web UI): Requires browser; too heavyweight
- PyQt/Tkinter: Desktop framework, not TUI; feels wrong for CLI tool
- Blessed: Simpler but less featureful than Textual

**Rationale:**
- Modern, actively maintained (Textualize team)
- Python-first design with CSS-based layout
- Built-in async support (aligns with aiosqlite)
- Excellent testing support (snapshot tests)
- Cross-platform Windows/macOS/Linux
- Rich component library (Input, Select, DataTable)

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** None

**Revisit Date:** After Sprint 1 if performance or layout issues arise

---

## D-005: Fuzzy Search Algorithm

**Question:** What library should CmdPop use for fuzzy search?

**Decision:** **RapidFuzz** library with token_set_ratio + custom scoring

**Alternatives Considered:**
- fzf: External binary; adds distribution complexity; can't embed in Python
- Whoosh: Full-text search engine; overkill for simple command search
- difflib (stdlib): Too simple; no ranking
- Levenshtein (simple): Only measures edit distance; poor for word matching

**Rationale:**
- RapidFuzz is pure Python with C extensions (fast)
- token_set_ratio handles partial matches well ("git com" matches "git commit")
- Customizable scoring: We layer fuzzy_score + recency + frequency
- Minimal external dependency (just one PyPI package)

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** D-010 (ranking formula)

**Revisit Date:** Never; proven for this use case

---

## D-006: Shell History Integration

**Question:** Should CmdPop require shell plugins or read history files directly?

**Decision:** **Read history files directly** — zero shell plugins required

**Alternatives Considered:**
- Shell hooks/plugins (bash, zsh, fish): Requires user to install and configure per shell; fragile
- PowerShell-only approach: Only works in PowerShell; doesn't cover bash, zsh, etc.

**Rationale:**
- CmdPop works in ANY terminal on ANY shell (or no shell)
- User runs `pipx install cmdpop` and immediately has access to all shell history
- No shell configuration needed — no breaking shell startup time
- More robust — history files are always available, regardless of shell state

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** D-011 (shell readers)

**Revisit Date:** Never; core value proposition

---

## D-007: Command Injection Strategy

**Question:** How should CmdPop inject the selected command into the user's active terminal?

**Decision:** **Platform-specific APIs with fallback chain**

- **Windows:** pywin32 SendKeys → clipboard
- **macOS:** osascript → clipboard
- **Linux:** xdotool (X11) → ydotool (Wayland) → clipboard

**Alternatives Considered:**
- Always use clipboard: Less elegant; user sees copy-paste, not "magical typing"
- Always use pyautogui.write(): Slow and unreliable across terminals
- Shell-specific echo/read: Doesn't work in non-shell contexts

**Rationale:**
- Platform-specific APIs are most reliable per OS
- Clipboard fallback ensures 100% success rate (worst case: command is in clipboard)
- Graceful degradation: Try primary → secondary → fallback
- User experience: Typing feels more natural than paste

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** None

**Revisit Date:** After Sprint 3 if injection failures exceed 1%

---

## D-008: Database Schema & Deduplication

**Question:** How should CmdPop handle duplicate commands from multiple shells?

**Decision:** **Store unique commands; track shell provenance and aggregate stats**

Schema:
```sql
CREATE TABLE commands (
    id INTEGER PRIMARY KEY,
    command TEXT UNIQUE NOT NULL,
    shell VARCHAR(20),              -- last shell where seen
    last_used TIMESTAMP,
    first_seen TIMESTAMP,
    run_count INTEGER,              -- total times seen
    shells_used TEXT,               -- "bash,zsh,fish"
    is_favorite BOOLEAN,
    source_file TEXT,
    created_at TIMESTAMP
);
```

**Alternatives Considered:**
- Store one row per shell: Duplicates; wastes space; makes search harder
- Normalize into separate tables: Over-engineered for single-user tool
- Store raw history per shell (no dedup): Original history preserved but search shows duplicates

**Rationale:**
- Deduplication improves search experience (no duplicate results)
- Aggregated stats (run_count, shells_used) provide valuable context
- UNIQUE constraint ensures command appears once
- Preserves metadata (first_seen, last_used, shells_used) for ranking and debugging

**Status:** **DECIDED**

**Depends On:** D-001 (SQLite)

**Blocks:** D-010 (ranking formula)

**Revisit Date:** Never; schema is sound

---

## D-009: Configuration Format

**Question:** What format should CmdPop use for user configuration?

**Decision:** **TOML** (via `tomllib` built-in to Python 3.11+)

**Alternatives Considered:**
- YAML: Too flexible; human editing errors common
- JSON: Too noisy; requires escaping; not ideal for user config
- INI: Limited nested structure
- TOML: Human-friendly, standards-based, built-in Python 3.11+ support

**Rationale:**
- Human-readable and easy to edit
- No external dependency (tomllib is stdlib in Python 3.11+)
- Well-suited for application config (sections, arrays, inline tables)
- Familiar to developers (used by Cargo, Poetry, pyproject.toml)

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** None

**Revisit Date:** Never; good choice for this use case

---

## D-010: Ranking Formula for Search Results

**Question:** How should CmdPop rank search results to show the most relevant command first?

**Decision:** **Three-factor scoring: fuzzy_score (40%) + recency (30%) + frequency (30%)**

Formula:
```
score = (fuzzy_score × 0.4) + (recency_score × 0.3) + (frequency_score × 0.3)

where:
  fuzzy_score = token_set_ratio(query, command) / 100    [0..1]
  recency_score = exp(-(days_since_last_used / 30))       [0..1, decay over ~month]
  frequency_score = min(run_count, 100) / 100             [0..1, capped at 100]
```

Plus: Favorites always float to top

**Alternatives Considered:**
- Only fuzzy score: Misses recency/frequency value
- Only recency: Forgets important but unused commands
- Naive frequency (most-used first): Ignores search relevance

**Rationale:**
- Fuzzy score ensures search query is respected
- Recency (30%) makes recently-used commands more likely (80/20 rule — users repeat recent commands)
- Frequency (30%) boosts commands user runs often
- Exponential decay for recency means commands are "fresh" for ~month, then fade
- Favorites override all (explicit user signal)

**Status:** **DECIDED**

**Depends On:** D-005 (fuzzy search), D-008 (schema)

**Blocks:** None

**Revisit Date:** After Sprint 1 if ranking feels wrong in user testing

---

## D-011: Supported Shells

**Question:** Which shells should CmdPop officially support?

**Decision:** **Bash, Zsh, Fish, PowerShell, CMD (with Clink)**

- **Bash** (Linux, macOS): `~/.bash_history` — plain text
- **Zsh** (Linux, macOS): `~/.zsh_history` — extended history format
- **Fish** (Linux, macOS, Windows): `~/.local/share/fish/fish_history` — YAML-like
- **PowerShell** (Windows, macOS, Linux): `%APPDATA%\...\ConsoleHost_history.txt` — plain text
- **CMD** (Windows): `%LOCALAPPDATA%\clink\.history` — plain text (requires Clink)

**Alternatives Considered:**
- PowerShell only: Only 1 shell; doesn't meet "universal" goal
- Bash/Zsh only: Misses Windows users
- All possible shells (ksh, tcsh, nushell, etc.): Too many variants; diminishing returns

**Rationale:**
- These 5 shells cover 95%+ of terminal users
- Multi-shell users (the target) typically use one of these
- Diminishing returns beyond this set
- Future shells can be added without breaking existing code

**Status:** **DECIDED**

**Depends On:** D-006 (no shell plugins)

**Blocks:** None

**Revisit Date:** After Sprint 1 if user demand warrants (e.g., Nushell, ksh)

---

## D-012: Sensitive Command Filtering

**Question:** How should CmdPop avoid storing sensitive commands (passwords, tokens, etc.)?

**Decision:** **Pattern-based exclusion at read time**

Exclude patterns (configurable in config.toml):
```
password, passwd, secret, token, apikey, api_key
```

Behavior:
- Any command matching these patterns (case-insensitive substring) is never stored
- User can add custom patterns to config
- Filtering happens when reading history, before DB insert

**Alternatives Considered:**
- Store everything: Privacy risk; security concern
- Prompt user on suspicious commands: Disruptive
- Only store first N chars of command: Lossy; defeats purpose
- Regex patterns: More powerful but complex; string matching is simpler

**Rationale:**
- Simple substring matching catches 90% of cases ("command contains 'password'")
- User can extend patterns for their own sensitive patterns
- Filtering at read time means DB only contains safe commands
- No network calls, no AI-based detection (stays local)

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** None

**Revisit Date:** After Sprint 1 user feedback on exclusion patterns

---

## D-013: Logging & Debugging

**Question:** What logging strategy should CmdPop use?

**Decision:** **Structured logging to ~/.cmdpop/debug.log; log level configurable**

Behavior:
- INFO: Daemon started, hotkey listened, command injected
- WARNING: Shell history unreadable, injection failed, config issue
- ERROR: DB corruption, hotkey binding failed
- DEBUG: (if configured) Detailed fuzzy search scores, DB queries

Files:
- `.cmdpop/debug.log` — rolling log (max 10MB, 3 backups)
- `.cmdpop/daemon.pid` — PID of running daemon

**Alternatives Considered:**
- No logging: Makes debugging impossible
- Syslog: Platform-specific; complex
- Just print to stdout: Lost if daemon runs in background

**Rationale:**
- Rolling log prevents disk bloat
- User can check log for troubleshooting ("why didn't my command inject?")
- Structured format makes parsing/analysis easier
- Local file stays private (no external log aggregation)

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** None

**Revisit Date:** Never; logging is standard practice

---

## D-014: Testing Strategy

**Question:** How should CmdPop be tested?

**Decision:** **Multi-level testing: unit, integration, snapshot, manual**

- **Unit Tests**: History readers, deduplicator, search ranking, DB CRUD
- **Integration Tests**: Full pipeline (read → deduplicate → search → inject)
- **Snapshot Tests**: Textual TUI visual consistency (CSS layout changes)
- **Manual Tests**: Hotkey responsiveness, command injection on real terminals (can't fully automate)

Test Fixtures:
- Real shell history samples in `tests/fixtures/history_samples/`
- Auto-generated test cases via `tests/generate_tests.py`

**Alternatives Considered:**
- Only unit tests: Misses integration bugs
- Only integration tests: Slow, hard to debug
- Only manual tests: Doesn't scale; regression prone

**Rationale:**
- Unit tests catch logic errors early
- Integration tests catch cross-component failures
- Snapshot tests catch accidental UI breaks
- Manual testing needed for platform-specific injection (can't mock terminal completely)
- Auto-generated tests from fixtures ensure coverage of edge cases

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** None

**Revisit Date:** Never; multi-level testing is best practice

---

## D-015: Packaging & Distribution

**Question:** How should CmdPop be distributed to users?

**Decision:** **PyPI via pipx (primary); source install for developers**

User installation:
```bash
pipx install cmdpop
```

Developer installation:
```bash
git clone ...
cd Popup_pop
pip install -e ".[dev]"
```

**Alternatives Considered:**
- System package managers (apt, brew, choco): Slower release cycle; platform-specific
- Standalone executables (PyInstaller): Harder to maintain
- Conda: Smaller user base

**Rationale:**
- PyPI: Standard Python distribution; pipx is the recommended way to install CLI tools
- pipx isolates dependencies (no conflicts with system Python)
- Easy updates: `pipx upgrade cmdpop`
- Works cross-platform (Windows, macOS, Linux)
- Developers can install from source with `pip install -e .`

**Status:** **DECIDED**

**Depends On:** None

**Blocks:** D-016 (CI/CD)

**Revisit Date:** Never; pipx is standard for CLI tools

---

## D-016: CI/CD Pipeline

**Question:** What CI/CD strategy should CmdPop use?

**Decision:** **GitHub Actions matrix (Windows, macOS, Linux); publish to PyPI on release tag**

Pipeline:
1. **CI** (on every push/PR): Lint (ruff), type check (mypy), tests (pytest) on all 3 platforms
2. **CD** (on main): Build wheels/sdist
3. **Release** (on version tag): Publish to PyPI

**Alternatives Considered:**
- Manual releases: Error-prone; hard to track versions
- Travis CI: Less integrated with GitHub
- GitLab CI: Not GitHub-native

**Rationale:**
- GitHub Actions integrates directly with repo
- Matrix testing ensures multi-platform compatibility
- Automated publishing reduces manual work and errors
- Version tag (e.g., `v0.2.0`) triggers automatic PyPI publish

**Status:** **DECIDED** (implementation in Phase 3)

**Depends On:** D-015 (packaging)

**Blocks:** None

**Revisit Date:** Never; GitHub Actions is standard

---

## DEFERRED Decisions

No decisions are currently deferred. All architectural decisions are made and solid enough to proceed with implementation.

---

## Decision History

| Decision | Sprint | Status | Date |
|----------|--------|--------|------|
| D-001 to D-016 | Sprint 0 | DECIDED | 2026-05-24 |

---

## Next Steps

1. **Sprint 1**: Implement all DECIDED decisions in order (history reading → storage → TUI → injection)
2. **After Sprint 1**: Revisit D-010 (ranking formula) and D-007 (injection reliability) if user feedback warrants
3. **Future sprints**: Consider deferred features (multi-machine sync, advanced ML ranking, additional shells)

---

> CmdPop Decisions · Sprint 0 · May 2026
