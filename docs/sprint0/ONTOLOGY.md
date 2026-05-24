# Ontology — CmdPop Data Model

**Version:** v0.1  
**Status:** DECIDED (Sprint 0)  
**Focus:** Entity definitions, relationships, validation rules  

---

## Core Entities

### HistoryEntry

**Definition:** A single command entry read from a shell's history file, before deduplication.

**Fields:**
```python
@dataclass
class HistoryEntry:
    command: str              # The shell command text (required)
    shell: str                # "bash" | "zsh" | "fish" | "powershell" | "cmd"
    timestamp: datetime       # When command was run (UTC)
    source_file: str          # Path to history file (e.g., ~/.bash_history)
```

**Validation:**
- `command`: Non-empty string, UTF-8 encoded, max 10,000 characters
- `shell`: One of the 5 supported shells (enum)
- `timestamp`: Valid datetime in UTC; must be < current time
- `source_file`: Absolute path, must exist

**Derived From:** Parsing shell history files (bash, zsh, fish, PowerShell, Clink)

**Lifetime:** Temporary — created during history read, then deduplicated into Command

**Example:**
```python
HistoryEntry(
    command="git commit -m 'fix: auth bug'",
    shell="bash",
    timestamp=datetime(2026, 5, 24, 14, 30, 0),
    source_file="/home/user/.bash_history"
)
```

---

### Command

**Definition:** A unique shell command, deduplicated and persisted in the database.

**Fields:**
```python
@dataclass
class Command:
    id: int                   # Database primary key
    command: str              # Unique command text
    shell: str                # Last shell where seen
    last_used: datetime       # Most recent execution
    first_seen: datetime      # Earliest known execution
    run_count: int            # Total times this command appears in history
    shells_used: List[str]    # All shells where this command was found
    is_favorite: bool         # User marked as favorite?
    source_files: List[str]   # All source files this command came from
    created_at: datetime      # When inserted into CmdPop DB
```

**Validation:**
- `command`: UNIQUE in database; non-empty; < 10k chars
- `shell`: One of the 5 supported shells
- `last_used`: >= first_seen; <= current time
- `run_count`: Integer >= 1
- `shells_used`: Non-empty list; all valid shell names
- `is_favorite`: Boolean (default: False)
- `created_at`: Auto-set to insertion time

**Derived From:** Deduplication of HistoryEntry objects

**Relationship:** One Command = Multiple HistoryEntry (same command from different shells)

**Indexing:**
- Primary index: `id` (auto-increment)
- Unique index: `command` (UNIQUE constraint)
- Secondary indices: `last_used`, `run_count`, `is_favorite`

**Example:**
```python
Command(
    id=42,
    command="git commit -m 'fix: auth bug'",
    shell="bash",
    last_used=datetime(2026, 5, 24, 14, 30, 0),
    first_seen=datetime(2026, 3, 15, 10, 0, 0),
    run_count=3,
    shells_used=["bash", "zsh"],
    is_favorite=True,
    source_files=["/home/user/.bash_history", "/home/user/.zsh_history"],
    created_at=datetime(2026, 3, 15, 11, 0, 0)
)
```

---

### Session

**Definition:** A single TUI picker session — user opens picker, selects a command, picker closes.

**Fields:**
```python
@dataclass
class Session:
    id: int                   # Session ID
    started_at: datetime      # When picker was opened
    ended_at: datetime        # When picker was closed (None if still open)
    selected_command_id: int  # (if command was selected; None if cancelled)
    search_query: str         # Last search text user typed
    results_count: int        # How many results matched the search
    injection_success: bool   # Was command injected into terminal?
    source_pid: int           # PID of daemon that spawned this session
```

**Validation:**
- `started_at`: Valid datetime, UTC
- `ended_at`: None (still open) or >= started_at
- `selected_command_id`: Refers to valid Command.id or None
- `search_query`: String (can be empty)
- `results_count`: Integer >= 0
- `injection_success`: Boolean
- `source_pid`: Valid process ID

**Derived From:** User interactions with TUI (created on picker open, finalized on close)

**Relationship:** One Session → Zero or One Command (depends on whether user selected)

**Lifetime:** Ephemeral — used for analytics/debugging only; not persisted long-term

**Purpose:** Debug "why didn't my command injection work?" → look at Session history

**Example:**
```python
Session(
    id=1,
    started_at=datetime(2026, 5, 24, 14, 35, 0),
    ended_at=datetime(2026, 5, 24, 14, 35, 2),
    selected_command_id=42,
    search_query="git com",
    results_count=7,
    injection_success=True,
    source_pid=12345
)
```

---

### Injection

**Definition:** Attempt to inject a command into the active terminal.

**Fields:**
```python
@dataclass
class Injection:
    id: int                    # Injection ID
    command_id: int            # Which Command was injected
    method: str                # "win32" | "osascript" | "xdotool" | "ydotool" | "clipboard"
    platform: str              # "windows" | "macos" | "linux"
    success: bool              # Was injection successful?
    error_message: str         # (if failed; None if successful)
    timestamp: datetime        # When injection was attempted
```

**Validation:**
- `command_id`: Refers to valid Command.id
- `method`: One of [win32, osascript, xdotool, ydotool, clipboard]
- `platform`: One of [windows, macos, linux]
- `success`: Boolean
- `error_message`: String or None
- `timestamp`: Valid datetime, UTC

**Derived From:** Execution of Injector.inject()

**Relationship:** One Injection ← One Command

**Lifetime:** Ephemeral — logged for debugging; not critical to persist

**Purpose:** Debug "why didn't injection work?" → look at injection history; which method was used?

**Example:**
```python
Injection(
    id=1,
    command_id=42,
    method="win32",
    platform="windows",
    success=True,
    error_message=None,
    timestamp=datetime(2026, 5, 24, 14, 35, 1)
)
```

---

### Shell

**Definition:** A supported shell whose history CmdPop reads.

**Enum:**
```python
class Shell(Enum):
    BASH = "bash"              # ~/.bash_history
    ZSH = "zsh"                # ~/.zsh_history
    FISH = "fish"              # ~/.local/share/fish/fish_history
    POWERSHELL = "powershell"  # PSReadLine history
    CMD = "cmd"                # Clink history (Windows)
```

**Validation:**
- Only these 5 shells are recognized
- Shell name is case-insensitive in input; normalized to lowercase

**Usage:** Tag on Command and HistoryEntry to indicate shell origin

**Detection:** Platform-specific auto-detection (see `utils/platform.py`)

---

### Config

**Definition:** User configuration loaded from `~/.cmdpop/config.toml`.

**Fields:**
```python
@dataclass
class Config:
    # Hotkey settings
    hotkey: str                # e.g., "ctrl+alt+h"
    
    # Storage settings
    max_history: int           # Max commands to keep (default: 10000)
    cleanup_days: int          # Auto-delete commands older than N days (default: 90)
    
    # Display settings
    theme: str                 # "dark" | "light" | "auto"
    height_percent: int        # TUI height as % (default: 60)
    width_percent: int         # TUI width as % (default: 50)
    position: str              # "center" | "top" | "bottom"
    show_timestamps: bool      # Show when command was run
    show_source_shell: bool    # Show which shell the command came from
    show_run_count: bool       # Show how many times command was run
    show_favorites: bool       # Show star on favorites
    
    # History settings
    sources: List[str]         # Which shells to read ("auto" or list)
    exclude_patterns: List[str]  # Command patterns to exclude
    
    # Injection settings
    inject_method: str         # "auto" | "clipboard" | "xdotool" | "win32"
    
    # Logging
    log_level: str             # "debug" | "info" | "warning" | "error"
```

**Validation:**
- `hotkey`: Valid key combo (parsed by pynput)
- `max_history`: 100 to 100,000
- `cleanup_days`: 0 to 365 (0 = no cleanup)
- `theme`: one of [dark, light, auto]
- `height_percent`, `width_percent`: 20 to 100
- `position`: one of [center, top, bottom]
- `exclude_patterns`: List of strings
- `inject_method`: one of [auto, clipboard, xdotool, win32]
- `log_level`: one of [debug, info, warning, error]

**Derived From:** TOML file at `~/.cmdpop/config.toml`

**Validation:** On load; if invalid, revert to defaults + warn user

**Example:**
```toml
[cmdpop]
hotkey = "ctrl+alt+h"
max_history = 10000
theme = "dark"
inject_method = "auto"

[history]
sources = ["auto"]
exclude_patterns = ["password", "secret", "token"]
cleanup_days = 90

[display]
height_percent = 60
width_percent = 50
position = "center"
show_timestamps = true
show_source_shell = true
```

---

### HistoryFile

**Definition:** A shell history file found on the user's system.

**Fields:**
```python
@dataclass
class HistoryFile:
    path: str                  # Absolute path to history file
    shell: str                 # Shell that wrote this file
    format: str                # "plaintext" | "extended_zsh" | "yaml_fish"
    last_modified: datetime    # File mtime (for caching)
    size_bytes: int            # File size
    is_readable: bool          # User has permission to read?
```

**Validation:**
- `path`: Absolute path; file must exist
- `shell`: One of the 5 supported shells
- `format`: One of [plaintext, extended_zsh, yaml_fish]
- `last_modified`: Valid datetime
- `size_bytes`: Integer >= 0

**Derived From:** OS filesystem scanning (during history read)

**Purpose:** Caching — avoid re-parsing unchanged files

**Example:**
```python
HistoryFile(
    path="/home/user/.bash_history",
    shell="bash",
    format="plaintext",
    last_modified=datetime(2026, 5, 24, 10, 0, 0),
    size_bytes=45321,
    is_readable=True
)
```

---

## Entity Relationships

```
HistoryFile (1) ──reads──> (N) HistoryEntry
                                     │
                                     │ deduplicate
                                     ↓
                              (1) Command ──┐
                                     │      │
                        ┌────────────┤      │
                        │            │      │
                   (1) Session       │      │
                        │            │      │
                        └──selects───┘      │
                                           │
                        ┌──────────────────┘
                        │
                        ↓
                    (1) Injection
```

**Flow:**
1. **Discover** HistoryFile from filesystem
2. **Read** HistoryFile → produce HistoryEntry objects
3. **Deduplicate** HistoryEntry objects → consolidate into Command
4. **Store** Command in database
5. **Display** Commands in Session (TUI picker)
6. **Select** Command from Session
7. **Inject** Command into terminal via Injection

---

## Invariants & Constraints

| Invariant | Reason |
|-----------|--------|
| Every Command has at least one shell origin | Can't have anonymous commands |
| Command text is unique in DB | Deduplication guarantees |
| last_used >= first_seen | Temporal consistency |
| run_count >= 1 | At least seen once |
| shells_used is non-empty | At least one shell origin |
| Session.ended_at is None or >= started_at | Time consistency |
| Injection.method matches platform | Logic consistency |

---

## Data Lifecycle

### Command

1. **Create** → HistoryEntry read from shell history file
2. **Aggregate** → Deduplicated with other HistoryEntry (same command)
3. **Store** → Inserted into `commands` table
4. **Update** → Periodically (on each resync), metadata refreshed
5. **Archive** → After cleanup_days (default: 90), old commands deleted
6. **Retain** → Favorites are never auto-deleted

### Session

1. **Create** → Picker window opened (hotkey pressed)
2. **Update** → User searches, navigates, edits
3. **Finalize** → Picker closed (selection or cancel)
4. **Discard** → Not persisted; used for debugging only

### Injection

1. **Attempt** → User selects command
2. **Execute** → Primary method tried
3. **Retry** → If failed, fallback method tried
4. **Log** → Success or failure recorded
5. **Discard** → Ephemeral; used for debugging only

---

## Extensibility

Future entity types (not in Sprint 0, but planned):

- **Tag**: User-created tags for organizing commands (e.g., "git", "docker")
- **Macro**: Parameterized commands (e.g., `git commit -m "{{message}}"`)
- **Session Sync**: Cross-device command sharing (deferred)
- **CommandStats**: Hourly/daily usage analytics (deferred)

---

> CmdPop Ontology · Sprint 0 · May 2026
