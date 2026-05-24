# HITL Flow — CmdPop User Journey

**Version:** v0.1  
**Status:** DECIDED (Sprint 0)  
**Author:** Sprint 0 Team  

---

## Overview

CmdPop is a **standalone CLI daemon** that runs in the background and responds to a global hotkey. The user journey has 4 distinct phases:

1. **Daemon Startup** — User runs `cmdpop start` (or autostart on login)
2. **Hotkey Listen** — Daemon listens for `Ctrl+Alt+H` (or configured hotkey)
3. **Picker Overlay** — Hotkey triggers floating TUI with fuzzy search
4. **Command Injection** — User selects a command; it's typed into the active terminal

---

## Phase 1: Daemon Startup

**Entry Criteria:**
- User has installed CmdPop via `pipx install cmdpop` or `pip install -e .`
- User runs `cmdpop start` (or daemon is autostarted on login via OS-level configuration)

**Flow:**

```
User: cmdpop start
  ↓
Check if daemon is already running
  ├─ If running: Exit with "Daemon already running on PID {pid}"
  └─ If not running:
       ├─ Load config from ~/.cmdpop/config.toml (create with defaults if missing)
       ├─ Initialize SQLite DB at ~/.cmdpop/history.db (create schema if needed)
       ├─ Sync all shell history files into DB (bash, zsh, fish, powershell, cmd)
       ├─ Start pynput global hotkey listener on configured hotkey (default: Ctrl+Alt+H)
       ├─ Write PID to ~/.cmdpop/daemon.pid
       ├─ Detach from terminal (daemon mode on Unix; background service on Windows)
       └─ Log: "CmdPop daemon started on PID {pid}, listening for {hotkey}"
```

**Exit Criteria:**
- Daemon is running and listening for hotkey
- SQLite database is initialized with schema
- All shell history sources have been synced into DB at least once
- Process survives terminal close

**Error Handling:**
- **Config file corrupt:** Load hardcoded defaults, warn user, don't fail
- **SQLite locked:** Wait up to 5 seconds; if still locked, fail with clear message
- **Hotkey binding fails:** Fall back to alternative (or fail with platform-specific guidance)
- **History file not readable:** Log warning, continue with other shells

---

## Phase 2: Hotkey Listen (Long-Running)

**Entry Criteria:**
- Daemon is running and fully initialized
- Hotkey listener is active

**Flow:**

```
Daemon running in background, listening...
  
User presses Ctrl+Alt+H (or configured hotkey)
  ↓
pynput detects key combination
  ↓
Hotkey callback triggered
  ├─ Detect active window/terminal
  ├─ If no active terminal found:
  │   └─ Show error overlay: "No active terminal detected"
  └─ If terminal found:
       ├─ Open Textual TUI app (Phase 3)
       ├─ Keep reference to active window for later injection
       └─ Wait for user selection or cancel
```

**Exit Criteria:**
- Hotkey successfully opens picker in Phase 3, or shows error

**Error Handling:**
- **Window detection fails:** Show error overlay with platform-specific guidance
- **Another picker instance already open:** Focus existing picker, don't open new one
- **Terminal is minimized/hidden:** Still show picker (user can switch focus)

**Resilience:**
- Hotkey listener continues running even if one invocation fails
- Failed picker opens are logged but do not crash daemon

---

## Phase 3: Picker Overlay (Interactive TUI)

**Entry Criteria:**
- Hotkey triggered successfully
- Active terminal detected
- Textual TUI app initialized

**Display:**
```
╔══════════════════════════════════════════════════╗
║  ⌨  CmdPop — Command History      [Esc] to close ║
╠══════════════════════════════════════════════════╣
║  🔍  git commit -m "                             ║
╠══════════════════════════════════════════════════╣
║  ★  git commit -m "fix: auth"    bash  2m ago   ║
║     git commit -m "feat: login"  zsh   1h ago   ║
║     git commit -am "wip"         bash  3h ago   ║
║     git push origin main         ps    5h ago   ║
║     docker build -t app .        bash 1d ago    ║
║  ─────────────────────────────────────────────   ║
║  [↑/↓] Navigate  [Enter] Select  [F] Favorite   ║
║  [Del] Remove    [Esc] Close                    ║
╚══════════════════════════════════════════════════╝
```

**User Interactions:**

| Key | Action | Behavior |
|-----|--------|----------|
| `↑` / `↓` | Navigate | Scroll through command list |
| `Enter` | Select | Proceed to Phase 4 (injection) |
| `F` | Toggle Favorite | Mark/unmark with ★, persist to DB |
| `Delete` | Remove | Delete from history, update DB |
| `Esc` | Cancel | Close picker, return to terminal |
| `A` | Select All (in search) | Select all text in search box |
| Type | Fuzzy Search | Real-time filter as user types |

**Flow:**

```
TUI loads
  ├─ Query DB: SELECT * FROM commands ORDER BY last_used DESC LIMIT 1000
  ├─ Render list with timestamps, source shells
  └─ Focus search input
  
User types in search
  ├─ Real-time fuzzy filter (rapidfuzz)
  ├─ Re-rank by recency + frequency + fuzzy score
  └─ Update list view
  
User navigates / edits
  ├─ F toggles favorite in DB
  ├─ Delete removes from DB
  └─ List updates immediately
  
User presses Enter on a command
  └─ Go to Phase 4 (injection)
  
User presses Esc
  ├─ Close TUI
  ├─ Daemon returns to Phase 2 (hotkey listen)
  └─ Return focus to original terminal
```

**Exit Criteria:**
- User either:
  - Selects a command (Enter) → Phase 4
  - Cancels (Esc) → Back to Phase 2
  - Closes the window → Back to Phase 2

**Error Handling:**
- **Empty database:** Show helpful message "No commands yet. Run `cmdpop sync` to import history."
- **Search returns no results:** Show "No matches found. Try a simpler search."
- **DB query slow:** Show spinner, limit results to top 1000 most recent

---

## Phase 4: Command Injection

**Entry Criteria:**
- User selected a command from picker
- Selected command is known (in database)

**Flow:**

```
User selected: "git commit -m "fix: auth bug""
  ↓
Close TUI, return focus to original terminal
  ↓
Detect OS platform (Windows / macOS / Linux)
  ↓
Try primary injection method for platform:
  
  ┌─ WINDOWS:
  │   ├─ Try pywin32 SendKeys API (most reliable)
  │   └─ Fallback: pyautogui.write() + clipboard
  │
  ├─ MACOS:
  │   ├─ Try osascript AppleScript key typing
  │   └─ Fallback: pyautogui + clipboard
  │
  └─ LINUX:
      ├─ Try xdotool (X11)
      ├─ Try ydotool (Wayland)
      └─ Fallback: pyautogui + clipboard

If injection succeeds:
  ├─ Update DB: SET last_used = NOW(), run_count += 1
  ├─ Command ready in terminal (user hits Enter to execute)
  └─ Close picker overlay
  
If all injection methods fail:
  ├─ Copy command to clipboard
  ├─ Show overlay: "Command copied to clipboard (injection failed on {platform})"
  ├─ Wait 3 seconds or user presses any key
  └─ Close picker overlay
```

**Exit Criteria:**
- Command is in terminal input buffer, ready to run
- Picker is closed and focus is on terminal
- Database updated with run count and timestamp
- User can now press Enter to execute, or edit the command first

**Error Handling:**

| Scenario | Behavior |
|----------|----------|
| Special chars in command (quotes, backslashes) | Escape properly per platform |
| Very long command (>1000 chars) | Use clipboard fallback to avoid buffer overflow |
| Terminal window lost focus | Attempt injection anyway; may fail silently |
| Injection succeeds but command not visible | Log warning; user can still press Enter to execute |

**Platform-Specific Notes:**

- **Windows CMD:** Limited history support (Clink required); injection via SendKeys
- **Windows PowerShell:** Full history support; injection via SendKeys or clipboard
- **macOS Terminal/iTerm:** AppleScript injection; works reliably
- **Linux X11:** xdotool; works reliably on most terminals
- **Linux Wayland:** ydotool (requires uinput permissions); may require user setup
- **zsh/bash/fish:** Compatible with all platforms above

---

## Daemon Management Commands

### Start daemon
```bash
cmdpop start
```

### Stop daemon
```bash
cmdpop stop
# or
pkill -f "cmdpop"
```

### Check daemon status
```bash
cmdpop status
# Output: Daemon running on PID {pid}, listening for {hotkey}
# or
# Output: Daemon not running
```

### Sync history manually
```bash
cmdpop sync
# Immediately read all shell history files and import into DB
# Useful after installing a new shell or to force refresh
```

### View current config
```bash
cmdpop config
# Output location and all settings
```

---

## Resilience & Recovery

### Daemon Crash Recovery
- If daemon crashes, it will not auto-restart
- User runs `cmdpop start` again
- On startup, daemon checks if DB is intact and recovers if needed

### Stale PID File
- If daemon crashes but PID file remains, next `cmdpop start` detects stale PID and cleans up

### Hotkey Conflicts
- If another application claims the hotkey, CmdPop will fail to bind
- Clear error message guides user to reconfigure in `~/.cmdpop/config.toml`

### Database Corruption
- SQLite is robust, but if DB is corrupted:
  - Daemon falls back to in-memory DB (no persistence)
  - User is warned; history is not lost (can be re-imported via `cmdpop sync`)

---

## Accessibility & Keyboard-Only Mode

All operations work via keyboard:
- Hotkey to open picker
- Fuzzy search via typing
- Navigation via arrow keys
- Selection via Enter
- All other actions via single-key shortcuts

Mouse support is optional (nice-to-have but not required).

---

## Success Metrics

By end of Phase 1 implementation:
- [ ] Daemon starts without errors
- [ ] Hotkey opens picker within 500ms
- [ ] User can search and select a command
- [ ] Selected command appears in terminal
- [ ] Daemon survives terminal close and continues listening

---

> CmdPop HITL Flow · Sprint 0 · May 2026
