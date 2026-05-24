# Database Schema & Strategy — CmdPop

**Version:** v0.1  
**Status:** DECIDED (Sprint 0)  
**Focus:** SQLite schema, migrations, performance, backup  

---

## Database Location & Permissions

**Path:** `~/.cmdpop/history.db`

**Permissions:**
```bash
chmod 600 ~/.cmdpop/history.db   # Owner read/write only (no group/world access)
```

**Size:** ~1GB per 1M commands (rough estimate: 1KB per command)

---

## Schema (Version 1)

### Metadata Table

Tracks schema version for migrations.

```sql
CREATE TABLE _metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data
INSERT INTO _metadata (key, value) VALUES ('schema_version', '1');
INSERT INTO _metadata (key, value) VALUES ('last_sync', '1970-01-01T00:00:00Z');
```

### Commands Table

Core table storing all unique commands.

```sql
CREATE TABLE commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT UNIQUE NOT NULL,
    shell VARCHAR(20) NOT NULL,        -- "bash", "zsh", "fish", "powershell", "cmd"
    last_used TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP NOT NULL,
    run_count INTEGER NOT NULL DEFAULT 1,
    shells_used TEXT NOT NULL,         -- Comma-separated: "bash,zsh,fish"
    is_favorite BOOLEAN DEFAULT 0,
    source_files TEXT,                 -- Comma-separated file paths
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for fast queries
CREATE INDEX idx_commands_last_used ON commands(last_used DESC);
CREATE INDEX idx_commands_run_count ON commands(run_count DESC);
CREATE INDEX idx_commands_is_favorite ON commands(is_favorite);
CREATE INDEX idx_commands_shell ON commands(shell);
CREATE INDEX idx_commands_created_at ON commands(created_at DESC);
```

**Column Details:**

| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `command` | TEXT | UNIQUE NOT NULL | The shell command text (must be unique) |
| `shell` | VARCHAR(20) | NOT NULL | Which shell this command was last seen in |
| `last_used` | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | Most recent execution |
| `first_seen` | TIMESTAMP | NOT NULL | Earliest known execution |
| `run_count` | INTEGER | NOT NULL DEFAULT 1 | How many times this command appears in history |
| `shells_used` | TEXT | NOT NULL | All shells where command was found (e.g., "bash,zsh") |
| `is_favorite` | BOOLEAN | DEFAULT 0 | User marked as favorite? (1=yes, 0=no) |
| `source_files` | TEXT | NULL | Comma-separated file paths (for debugging) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When inserted into CmdPop DB |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time (for debugging) |

**Constraints:**
- UNIQUE on `command`: No duplicate command text
- NOT NULL on `command`, `shell`, `first_seen`, `run_count`, `shells_used`: Always have these
- `first_seen <= last_used`: Temporal consistency
- `run_count >= 1`: At least seen once

### Sessions Table (Optional, for debugging)

Track picker sessions for analytics and debugging.

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    selected_command_id INTEGER,       -- FOREIGN KEY to commands.id
    search_query TEXT,
    results_count INTEGER,
    injection_success BOOLEAN,
    source_pid INTEGER,
    FOREIGN KEY (selected_command_id) REFERENCES commands(id) ON DELETE SET NULL
);

CREATE INDEX idx_sessions_started_at ON sessions(started_at DESC);
```

**Purpose:** Optional tracking for debugging "why didn't injection work?"

**Retention:** Keep for ~30 days, then auto-delete (reduces bloat)

### Injections Table (Optional, for debugging)

Track injection attempts for diagnostics.

```sql
CREATE TABLE injections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id INTEGER NOT NULL,       -- FOREIGN KEY to commands.id
    method VARCHAR(20),                -- "win32", "osascript", "xdotool", "ydotool", "clipboard"
    platform VARCHAR(20),              -- "windows", "macos", "linux"
    success BOOLEAN NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (command_id) REFERENCES commands(id) ON DELETE CASCADE
);

CREATE INDEX idx_injections_timestamp ON injections(timestamp DESC);
CREATE INDEX idx_injections_success ON injections(success);
```

**Purpose:** Debug "which injection method failed?"

**Retention:** Keep for ~7 days, then auto-delete

---

## Normalization & Denormalization

### Why This Schema Is Denormalized

**Denormalized fields:**
- `shells_used` (TEXT) instead of separate `command_shells` table
- `source_files` (TEXT) instead of separate `command_sources` table

**Rationale:**
- Single-user tool; no need for full normalization
- Denormalization simplifies queries (no JOINs)
- Trades storage (small) for speed (significant)
- Sufficiently simple for 100k+ commands

### If We Were Multi-User (Future)

Would normalize:
```sql
CREATE TABLE command_shells (
    command_id INTEGER,
    shell VARCHAR(20),
    FOREIGN KEY (command_id) REFERENCES commands(id),
    PRIMARY KEY (command_id, shell)
);

CREATE TABLE command_sources (
    command_id INTEGER,
    source_file TEXT,
    FOREIGN KEY (command_id) REFERENCES commands(id),
    PRIMARY KEY (command_id, source_file)
);
```

But for now, denormalization is correct choice.

---

## Query Patterns

### Most Recent Commands (Default View)

```sql
SELECT * FROM commands
WHERE is_favorite = 0
ORDER BY last_used DESC
LIMIT 100;
```

**Index used:** `idx_commands_last_used`

**Latency:** < 10ms (1000 rows or 10k rows)

### Favorites First

```sql
SELECT * FROM commands
ORDER BY
    is_favorite DESC,
    last_used DESC
LIMIT 100;
```

**Index used:** `idx_commands_is_favorite` + `idx_commands_last_used`

**Latency:** < 10ms

### Fuzzy Search with Ranking

```python
# Query top 1000 most recent (in Python, apply fuzzy matching)
SELECT * FROM commands
ORDER BY last_used DESC
LIMIT 1000;

# Then in Python (using RapidFuzz):
ranked = search_engine.search(query, results)
```

**Why 1000 limit:** Fuzzy matching 1000 items is fast enough; full-text search on 10k+ is slow

**Latency:** < 50ms query + < 100ms fuzzy ranking = < 150ms total

### Most Frequently Used Commands

```sql
SELECT * FROM commands
ORDER BY run_count DESC
LIMIT 100;
```

**Index used:** `idx_commands_run_count`

**Latency:** < 10ms

### Commands by Shell

```sql
SELECT * FROM commands
WHERE shell = 'bash'
ORDER BY last_used DESC
LIMIT 100;
```

**Index used:** `idx_commands_shell`

**Latency:** < 10ms

### Auto-Cleanup: Remove Old Commands

```sql
DELETE FROM commands
WHERE
    is_favorite = 0
    AND last_used < datetime('now', '-90 days');
```

**Safety:** Favorites are never deleted

**Frequency:** Run weekly (background job)

### Update on Resync: Increment Run Count

```sql
UPDATE commands
SET
    run_count = run_count + 1,
    last_used = ?,
    shells_used = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE command = ?;
```

---

## Migrations Strategy

**Version 1 (Current):**
- Initial schema with commands, sessions, injections tables

**Version 2 (Example, future):**
```sql
ALTER TABLE commands ADD COLUMN tags TEXT;  -- For command tagging
```

**Implementation:**

```python
# src/cmdpop/storage/migrations.py

MIGRATIONS = {
    1: """
        CREATE TABLE commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ... (full schema)
        );
        CREATE INDEX idx_commands_last_used ON commands(last_used DESC);
        ...
    """,
    2: """
        ALTER TABLE commands ADD COLUMN tags TEXT;
        CREATE INDEX idx_commands_tags ON commands(tags);
    """,
}

async def apply_migrations(db: CommandDB):
    """Apply pending migrations."""
    current_version = await db.get_schema_version()
    target_version = max(MIGRATIONS.keys())
    
    for version in range(current_version + 1, target_version + 1):
        sql = MIGRATIONS[version]
        await db.execute(sql)
        await db.set_schema_version(version)
```

**Safety:**
- Never drop columns (backward compatibility)
- Always reversible migrations (at least in theory)
- Run migrations on daemon startup (idempotent)

---

## Backup & Recovery

### Automatic Backup

```python
# Run daily (or on startup if backup is missing)
async def backup_database():
    shutil.copy(
        os.path.expanduser("~/.cmdpop/history.db"),
        os.path.expanduser("~/.cmdpop/history.db.backup")
    )
```

**Location:** `~/.cmdpop/history.db.backup`

**Retention:** Keep latest backup only

### Recovery

```bash
# If DB is corrupted:
cp ~/.cmdpop/history.db.backup ~/.cmdpop/history.db

# If that fails, user can always resync:
cmdpop sync  # Re-read all shell history files
```

### Corruption Detection

```python
async def is_db_valid():
    try:
        async with self.db.cursor() as cursor:
            await cursor.execute("PRAGMA integrity_check;")
            result = await cursor.fetchone()
            return result[0] == "ok"
    except Exception:
        return False
```

**On startup:** Check DB integrity; if corrupt, fall back to backup

---

## Performance Tuning

### PRAGMA Statements

```sql
-- Speed up writes (at risk of data loss on crash)
PRAGMA synchronous = NORMAL;

-- Speed up reads
PRAGMA query_only = FALSE;

-- Cache size (in pages; 2000 pages ~ 8MB RAM)
PRAGMA cache_size = 2000;

-- WAL mode (Write-Ahead Logging) for concurrent access
PRAGMA journal_mode = WAL;
```

**When Applied:** On `CommandDB.__init__()`

**Impact:**
- WAL mode: Faster writes, better concurrency
- PRAGMA synchronous = NORMAL: Faster writes (default is FULL which is slower)
- cache_size: Larger cache = more RAM, faster repeated queries

### Index Strategy

```sql
-- These indices exist:
CREATE INDEX idx_commands_last_used ON commands(last_used DESC);
CREATE INDEX idx_commands_run_count ON commands(run_count DESC);
CREATE INDEX idx_commands_is_favorite ON commands(is_favorite);
CREATE INDEX idx_commands_shell ON commands(shell);

-- Why these? They cover the most common queries:
-- 1. ORDER BY last_used (default view)
-- 2. ORDER BY run_count (frequency-based sorting)
-- 3. WHERE is_favorite (favorites view)
-- 4. WHERE shell (shell-specific view)

-- Avoided:
-- - Composite indices (would bloat DB with little benefit)
-- - Indices on TEXT columns (like `command`) - only UNIQUE constraint
```

### Benchmark Targets

| Query | Latency Target | Scale | Index |
|-------|---|---|---|
| Top 100 recent | < 10ms | 100k commands | idx_last_used |
| Top 100 frequent | < 10ms | 100k commands | idx_run_count |
| Favorites | < 10ms | 10k commands | idx_is_favorite |
| Add command | < 50ms | N/A | UNIQUE(command) |
| Fuzzy search | < 150ms | 100k commands | Sort by last_used, limit 1000, then fuzzy |

---

## Concurrency & Locking

### Single-Writer (Daemon)

- Only one daemon process at a time (ensured by PID file)
- No multi-process concurrency issues

### Single-Reader (TUI)

- TUI runs in same process as daemon (async)
- Uses `aiosqlite` for async DB access
- No blocking queries

### HistoryFile Locking

Shell history files may be written by shell while CmdPop reads:
```python
# Use file-level read lock (if available)
# Or just handle read errors gracefully (current approach)
```

**Current approach:** If history file is locked, skip and try again next sync

---

## Disaster Recovery

### Scenario: DB is completely corrupted

1. Rename corrupted DB: `mv ~/.cmdpop/history.db ~/.cmdpop/history.db.corrupted`
2. Daemon will create new DB on next startup (empty)
3. Run: `cmdpop sync` to re-import all shell history
4. All commands reappear (no permanent data loss)

### Scenario: User accidentally deletes history

1. Shell history files still exist on disk (separate from CmdPop DB)
2. Run: `cmdpop sync` to restore

### Scenario: User changes hotkey and can't remember it

1. Config is in plaintext: `~/.cmdpop/config.toml`
2. User edits config and resets to default: `hotkey = "ctrl+alt+h"`
3. Run: `cmdpop stop` and `cmdpop start` to apply

---

## Testing Strategy

### Unit Tests

```python
# test_storage.py
async def test_add_command():
    db = CommandDB(":memory:")  # In-memory for tests
    await db.add_command(Command(...))
    result = await db.get_command_by_id(1)
    assert result.command == "git status"

async def test_dedup_update():
    # If same command added twice, run_count increments
    await db.add_command(Command(command="git status", ...))
    await db.add_command(Command(command="git status", ...))
    result = await db.get_command_by_id(1)
    assert result.run_count == 2
```

### Integration Tests

```python
# test_integration.py
async def test_full_pipeline():
    # Read bash history → deduplicate → store → search
    db = CommandDB(":memory:")
    reader = BashReader()
    entries = await reader.read()
    deduped = deduplicate(entries)
    for entry in deduped:
        await db.add_command(entry)
    results = await db.search("git")
    assert len(results) > 0
```

### Snapshot Tests

- Not applicable to database (DB is not visual)
- But test that schema snapshot never changes (PRAGMA schema_version)

---

## Future Enhancements (Deferred)

- **Full-text search:** Add FTS5 extension for better search (deferred to Sprint 2)
- **Vector search:** Add embeddings + pgvector-like search (deferred to Sprint 3)
- **Replication:** Multi-device sync (deferred to future)
- **Analytics:** Hourly/daily usage stats (deferred)
- **Tagging:** User-created command tags (deferred)

---

> CmdPop Database Schema & Strategy · Sprint 0 · May 2026
