# System Architecture — CmdPop

**Version:** v0.1  
**Status:** DECIDED (Sprint 0)  
**Focus:** Core engine design, trust model, error recovery  

---

## System Overview

```
User Terminal          CmdPop Daemon (Background)        Persistent State
─────────────         ─────────────────────────────      ──────────────
   User                  Hotkey Listener
    │                         │
    │ (Ctrl+Alt+H)            │
    ├────────────────────────>├─→ Active Window Detector
    │                         │
    │ <─┬─ TUI Picker         ├─→ History Reader (all 5 shells)
    │   │ (fuzzy search)      │
    │   │ (selection)         ├─→ SQLite DB
    │   │                     │   ├─ Deduplicator
    │   │                     │   ├─ Ranking Engine (recency, frequency, fuzzy score)
    │   │                     │   └─ Favorites / Metadata
    │   │                     │
    │ ┌─┴─ Command Injector   ├─→ Platform-specific APIs
    │ │ (type into terminal)  │   ├─ Windows: pywin32 SendKeys
    │ │                       │   ├─ macOS: osascript
    │ │                       │   └─ Linux: xdotool / ydotool
    │ │                       │
    ├─┤ (command in input)    └─→ Config (TOML)
    │ │                           └─ ~/.cmdpop/config.toml
    │ └→ Command ready to execute
```

---

## Core Components

### 1. Hotkey Listener (`pynput` integration)

**Responsibility:** Listen globally for hotkey, trigger picker on match  
**Status:** DECIDED  
**Rationale:** Cross-platform, reliable, no shell integration needed  

**Interface:**
```python
class HotkeyListener:
    def start(self, hotkey: str, callback: Callable) -> None:
        """Start listening for hotkey."""
        
    def stop(self) -> None:
        """Stop listening."""
```

**Behavior:**
- Listens in background thread, non-blocking
- On hotkey match: call `callback()` → opens picker
- If callback fails: log error, continue listening
- Hotkey is configurable in `config.toml`

**Error Handling:**
- Hotkey already in use by another app: show clear error, offer config alternatives
- pynput not available on platform: warn and disable hotkey feature

---

### 2. History Reader (`src/cmdpop/history/`)

**Responsibility:** Read shell history from all 5 supported shells  
**Status:** DECIDED  
**Rationale:** No shell plugins → reads files directly → works everywhere  

**Architecture:**

```python
# Base class (abstract)
class HistoryReader(ABC):
    def read(self) -> List[HistoryEntry]: pass

# Concrete implementations
class BashReader(HistoryReader): pass   # ~/.bash_history
class ZshReader(HistoryReader): pass    # ~/.zsh_history (EXTENDED_HISTORY format)
class FishReader(HistoryReader): pass   # ~/.local/share/fish/fish_history
class PowerShellReader(HistoryReader): pass  # Windows/macOS/Linux PSReadLine
class CmdReader(HistoryReader): pass    # Windows Clink (requires Clink installed)

# Orchestrator
class HistoryAggregator:
    def read_all(self) -> List[HistoryEntry]:
        """Auto-detect installed shells, read all, merge + deduplicate."""
```

**Data Model:**
```python
@dataclass
class HistoryEntry:
    command: str                # The shell command text
    shell: str                  # "bash" | "zsh" | "fish" | "powershell" | "cmd"
    timestamp: datetime         # When command was run
    source_file: str            # Path to history file (for debugging)
    
    def __hash__(self):
        return hash(self.command)  # For deduplication
```

**Shell-Specific Formats:**

| Shell | File | Format | Challenges |
|-------|------|--------|-----------|
| **bash** | `~/.bash_history` | Plain text, one per line | Simple; handles UTF-8 |
| **zsh** | `~/.zsh_history` | Extended format: `: <ts>:0;<cmd>` | Parse timestamp; handle multi-line |
| **fish** | `~/.local/share/fish/fish_history` | YAML-like: `- cmd: ...\n  when: <ts>` | Parse YAML-ish format |
| **PowerShell** | `%APPDATA%\...\ConsoleHost_history.txt` | Plain text, one per line | Handle Windows paths |
| **cmd** | Clink: `%LOCALAPPDATA%\clink\.history` | Plain text (if Clink installed) | Optional; warn if missing |

**Error Handling:**
- File not found: skip shell (log warning, continue)
- File not readable (permissions): skip shell (log warning)
- Corrupted history format: skip line (log warning), continue
- Encoding issues: attempt UTF-8; fallback to latin-1

---

### 3. Deduplicator & Merger

**Responsibility:** Merge multiple shell histories, deduplicate  
**Status:** DECIDED  
**Rationale:** Same command run in bash and zsh should appear once, ranked highest  

**Algorithm:**

```
1. Read all shells → List[HistoryEntry]
2. Group by command text (case-sensitive)
3. For each group:
   - Keep entry with most recent timestamp
   - Aggregate metadata:
     - run_count = number of identical commands seen
     - first_seen = earliest timestamp
     - shells_used = set of shells where this command appeared
4. Sort by (last_used desc, run_count desc, command text asc)
5. Store deduplicated + ranked list in SQLite
```

**Deduplication Rules:**
- Two commands are identical if their text matches exactly (whitespace-sensitive)
- "git status" and "git  status" (extra space) → treated as different
- Rationale: Preserve user's actual typing style

**Storage:** After deduplication, store in `commands` table with:
```sql
CREATE TABLE commands (
    id INTEGER PRIMARY KEY,
    command TEXT UNIQUE NOT NULL,
    shell VARCHAR(20),           -- last shell where seen
    last_used TIMESTAMP,
    first_seen TIMESTAMP,
    run_count INTEGER,
    shells_used TEXT,            -- comma-separated: "bash,zsh,fish"
    is_favorite BOOLEAN,
    source_file TEXT,            -- for debugging
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 4. SQLite Database (`src/cmdpop/storage/db.py`)

**Responsibility:** Persistent storage, CRUD, search  
**Status:** DECIDED  
**Rationale:** Zero-config, embedded, cross-platform, no server  

**Schema:**
```sql
CREATE TABLE commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT UNIQUE NOT NULL,
    shell VARCHAR(20),
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP,
    run_count INTEGER DEFAULT 1,
    shells_used TEXT,            -- "bash,zsh,fish"
    is_favorite BOOLEAN DEFAULT 0,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_last_used ON commands(last_used DESC);
CREATE INDEX idx_run_count ON commands(run_count DESC);
CREATE INDEX idx_is_favorite ON commands(is_favorite);
```

**Location:** `~/.cmdpop/history.db`  
**Permissions:** 0600 (owner read/write only)  
**Migrations:** Simple schema versioning — version integer in metadata table

**Interface:**
```python
class CommandDB:
    async def add_command(self, entry: HistoryEntry) -> None:
        """Insert or update command."""
        
    async def search(self, query: str, limit: int = 100) -> List[Command]:
        """Fuzzy search."""
        
    async def get_all(self, limit: int = 1000) -> List[Command]:
        """Most recent commands."""
        
    async def toggle_favorite(self, command_id: int) -> None:
        """Mark/unmark as favorite."""
        
    async def delete_command(self, command_id: int) -> None:
        """Remove from DB."""
        
    async def cleanup(self, older_than_days: int = 90) -> None:
        """Auto-delete old commands (configurable)."""
```

**Async Design:** All DB operations are async (aiosqlite) to prevent UI blocking

---

### 5. Fuzzy Search & Ranking Engine

**Responsibility:** Real-time search + intelligent ranking  
**Status:** DECIDED  
**Rationale:** RapidFuzz is fast, accurate, and pure Python  

**Ranking Formula:**
```
score = (fuzzy_score × 0.4) + (recency_score × 0.3) + (frequency_score × 0.3)

where:
  fuzzy_score = rapidfuzz.fuzz.token_set_ratio(query, command) / 100
  recency_score = exp(-(days_since_last_used / 30))  -- decay over ~month
  frequency_score = min(run_count, 100) / 100  -- cap at 100 runs
```

**Behavior:**
- User types "git com" → fuzzy matches "git commit", "git config", etc.
- Recently-used commands ranked higher
- Frequently-used commands ranked higher
- Favorites always float to top (is_favorite=1)

**Interface:**
```python
class SearchEngine:
    def search(self, query: str, commands: List[Command]) -> List[Command]:
        """Real-time fuzzy search with ranking."""
        return sorted(commands, key=lambda c: self.score(query, c), reverse=True)
```

---

### 6. TUI Overlay (`src/cmdpop/app.py` — Textual)

**Responsibility:** User interface for search, navigation, selection  
**Status:** DECIDED  
**Rationale:** Modern, CSS-based, testable, cross-platform  

**Components:**
- **Search Input** (top): User types query
- **Command List** (middle): Scrollable list with timestamps, shells
- **Preview** (side): Expanded view of selected command
- **Footer** (bottom): Keyboard hints

**Behavior:**
- Real-time filtering as user types
- Arrow keys navigate
- Enter selects
- F toggles favorite
- Delete removes
- Esc closes

**State Machine:**
```
[Idle] --(user presses hotkey)--> [Opening]
       --(TUI loaded)--> [Searching] <--(user types)--+
                            |
                      --(user presses Enter)--> [Injecting]
                            |
                      --(user presses Esc)--> [Closing] --> [Idle]
```

---

### 7. Command Injector (`src/cmdpop/injector/`)

**Responsibility:** Type selected command into active terminal  
**Status:** DECIDED  
**Rationale:** Platform-specific APIs for reliability  

**Architecture:**
```python
class Injector(ABC):
    async def inject(self, command: str) -> bool:
        """Type command into active terminal. Return True if success."""
        pass

class WindowsInjector(Injector):
    """Uses pywin32 SendKeys + pyautogui fallback."""
    
class MacOSInjector(Injector):
    """Uses osascript AppleScript."""
    
class LinuxInjector(Injector):
    """Uses xdotool (X11) with ydotool (Wayland) fallback."""

class InjectorFactory:
    @staticmethod
    def get_injector() -> Injector:
        """Auto-detect platform, return appropriate injector."""
```

**Fallback Chain:**
```
Primary (platform-specific)
    ↓ (if fails)
Secondary (platform-specific)
    ↓ (if fails)
Clipboard + notification
    ↓ (if fails)
Silent failure (log error)
```

**Special Character Handling:**
- Escape quotes, backslashes per platform
- Long commands (>1000 chars): use clipboard
- Multi-line commands: replace newlines with `;` or appropriate separator

---

### 8. Configuration (`src/cmdpop/config/settings.py`)

**Responsibility:** Load + validate TOML config  
**Status:** DECIDED  
**Rationale:** Human-readable, built-in Python 3.11+ support  

**Location:** `~/.cmdpop/config.toml`

**Default Config:**
```toml
[cmdpop]
hotkey = "ctrl+alt+h"
max_history = 10000
theme = "dark"                    # dark | light | auto
inject_method = "auto"            # auto | clipboard | xdotool | win32

[history]
sources = ["auto"]                # auto-detect or list: ["bash", "zsh", "fish", "powershell"]
exclude_patterns = ["password", "passwd", "secret", "token", "apikey", "api_key"]
cleanup_days = 90                 # Auto-delete commands older than N days

[display]
height_percent = 60
width_percent = 50
position = "center"               # center | top | bottom
show_timestamps = true
show_source_shell = true
show_run_count = true
show_favorites = true
```

**Interface:**
```python
@dataclass
class Config:
    hotkey: str
    max_history: int
    theme: str
    inject_method: str
    sources: List[str]
    exclude_patterns: List[str]
    cleanup_days: int
    height_percent: int
    width_percent: int
    position: str
    show_timestamps: bool
    show_source_shell: bool

def load_config() -> Config:
    """Load from ~/.cmdpop/config.toml, or create with defaults."""
```

**Validation Rules:**
- hotkey: must be valid (e.g., "ctrl+alt+h", "shift+f1")
- max_history: 100 to 100000
- theme: one of ["dark", "light", "auto"]
- height/width percent: 20 to 100
- cleanup_days: 0 to 365 (0 = no cleanup)

---

## Error Handling & Recovery

### Levels of Failure

| Level | Severity | Recovery |
|-------|----------|----------|
| Hotkey binding fails | Warning | Offer config alternatives; daemon still runs |
| One shell history unreadable | Info | Log and skip; other shells still read |
| DB is locked | Error | Wait 5s; if still locked, show message |
| DB is corrupted | Critical | Fall back to in-memory (no persistence); warn user |
| Injection fails on all methods | Warning | Copy to clipboard; show notification |
| TUI crash | Critical | Close picker; daemon continues (hotkey still works) |

### Resilience Guarantees

1. **Daemon survives shell history failures** — One shell's history failure does not crash daemon
2. **DB writes are atomic** — No partial updates
3. **Hotkey listener survives picker crashes** — Picker can crash; daemon still listens
4. **Command injection failures are non-fatal** — User can manually type; clipboard has copy
5. **Config is gracefully downgraded** — If config is missing/invalid, defaults apply

---

## Security Model

### Trust Boundary

**Trusted:**
- Shell history files (written by user's own shells)
- SQLite database (local, user permissions)
- Config file (local, user editable)

**Untrusted:**
- Commands in history may contain sensitive data → exclude by pattern
- External hotkey events → validate before processing
- TUI input → sanitize before display

### Sensitive Data Handling

**Exclude Patterns (from config):**
```
"password", "passwd", "secret", "token", "apikey", "api_key"
```

**Behavior:**
- Any command matching these patterns (case-insensitive) is never stored
- User can add custom patterns to config
- Filtering happens at read time, not storage time

**Database Permissions:**
```bash
chmod 600 ~/.cmdpop/history.db
```

**No Network Calls:**
- All operations are local
- No cloud sync, no telemetry
- No external API calls

---

## Performance Targets

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Hotkey → picker visible | < 500ms | User expects snappy response |
| Fuzzy search on 10k items | < 100ms | Real-time search feels responsive |
| DB write (add command) | < 50ms | No noticeable lag in daemon |
| Startup (daemon start) | < 2s | User can wait for daemon to initialize |

**Optimization Strategy:**
- Limit query results to top 1000 most recent (UI pagination on demand)
- Fuzzy search on top 1000, not entire DB
- Lazy-load history on first picker open (not at daemon startup)
- Index DB by last_used and run_count for fast sorting

---

## Scalability

**Expected Limits:**
- **Database:** 100k+ commands (SQLite handles this fine)
- **Memory:** ~50MB per 10k commands (HistoryEntry objects)
- **UI response:** Still snappy with 10k commands (limited to display 100 at a time)

**Beyond Scope (defer to future sprint):**
- Multi-machine sync
- Cloud backup
- Advanced ML ranking

---

## Testing Strategy

**Unit Tests:**
- History readers: fixture-based, auto-generated from real shell formats
- Deduplicator: edge cases (empty, duplicates, timestamps)
- Fuzzy search: scoring correctness
- DB: CRUD operations, migrations
- Config: parsing, validation

**Integration Tests:**
- Full pipeline: read → deduplicate → search → inject
- All platforms: Windows, macOS, Linux

**Snapshot Tests (Textual):**
- TUI layout consistency
- Search results display

**Manual Testing:**
- Hotkey responsiveness
- Command injection on actual terminals (can't fully automate)

---

## Migration Path (if schema changes)

```python
# Version 1: Initial schema
# Version 2: Add new column (ALTER TABLE ADD COLUMN)
# Version 3: Rename column (CREATE new table, copy, DROP old, RENAME)

def migrate_schema(current_version: int, target_version: int) -> None:
    """Apply incremental migrations."""
```

---

## Decision Rationale Summary

| Component | Why This Choice | Alternatives Rejected |
|-----------|-----------------|----------------------|
| **Hotkey (pynput)** | Cross-platform, no plugins | Shell-specific hooks (not universal) |
| **Database (SQLite)** | Zero-config, embedded, cross-platform | PostgreSQL (overkill), Redis (not persistent), JSON files (not queryable) |
| **Fuzzy Search (RapidFuzz)** | Fast, pure Python, accurate | Fzf (external dependency), Whoosh (overkill) |
| **TUI (Textual)** | Modern, CSS-based, testable, Python-native | Curses (outdated), Rich Tables (not interactive), web UI (requires browser) |
| **Injection (platform-specific)** | Most reliable per OS | Single method (fragile), all-clipboard (less ideal) |
| **Config (TOML)** | Human-readable, built-in 3.11+, simple | YAML (too flexible), INI (limited), JSON (too noisy) |

---

> CmdPop Architecture · Sprint 0 · May 2026
