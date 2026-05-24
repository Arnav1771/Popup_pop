# CmdPop — Terminal Command History Picker

**Like Windows+V for your terminal** — a cross-platform floating TUI that brings your command history to your fingertips, zero shell plugins required.

## What is CmdPop?

CmdPop is a standalone CLI tool that:

- ✅ Works in **any terminal** on Windows, Mac, and Linux
- ✅ Supports **all major shells**: bash, zsh, fish, PowerShell, CMD+Clink
- ✅ Needs **zero shell plugins** — reads history files directly
- ✅ Shows a **floating overlay** with fuzzy search over your command history
- ✅ Injects selected commands back into your active terminal
- ✅ Persists history across sessions with SQLite
- ✅ Configurable hotkey (default: `Ctrl+Alt+H`)

## Installation

### Via pipx (recommended)

```bash
pipx install cmdpop
```

### From source

```bash
git clone https://github.com/Arnav1771/Popup_pop.git
cd Popup_pop
pip install -e .
```

## Usage

### Start the daemon

```bash
cmdpop start
```

This runs in the background and listens for the hotkey (`Ctrl+Alt+H` by default).

### Open the picker manually

```bash
cmdpop open
```

### Sync shell history

```bash
cmdpop sync
```

Immediately read all shell history files and import them into CmdPop's database.

### View configuration

```bash
cmdpop config
```

Prints the current config location and all active settings.

### Regenerate tests

```bash
cmdpop generate-tests
```

Rebuilds the test suite from fixture files.

## Configuration

Configuration is stored in `~/.cmdpop/config.toml`. On first run, a default config is created.

### Example config

```toml
[cmdpop]
hotkey = "ctrl+alt+h"
max_history = 10000
theme = "dark"

[history]
sources = ["auto"]
exclude_patterns = ["password", "passwd", "secret", "token", "apikey", "api_key"]

[display]
height_percent = 60
width_percent = 50
position = "center"
show_timestamps = true
show_source_shell = true
```

### Configuration options

| Setting | Section | Type | Default | Description |
|---------|---------|------|---------|-------------|
| `hotkey` | cmdpop | string | `ctrl+alt+h` | Global hotkey to open picker |
| `max_history` | cmdpop | int | 10000 | Maximum commands to store |
| `theme` | cmdpop | string | `dark` | UI theme: dark, light, auto |
| `sources` | history | list | `["auto"]` | Which shells to read: auto or ["bash", "zsh", "fish", "powershell", "cmd"] |
| `exclude_patterns` | history | list | `[...]` | Command keywords to exclude from storage (case-insensitive) |
| `height_percent` | display | int | 60 | Popup height as % of terminal |
| `width_percent` | display | int | 50 | Popup width as % of terminal |
| `position` | display | string | `center` | Popup position: center, top, bottom |
| `show_timestamps` | display | bool | `true` | Show command timestamps |
| `show_source_shell` | display | bool | `true` | Show which shell the command came from |

## Supported Shells

| Shell | Platform | History File | Support |
|-------|----------|-------------|---------|
| **bash** | All | `~/.bash_history` | ✅ Full |
| **zsh** | All | `~/.zsh_history` | ✅ Full (including EXTENDED_HISTORY) |
| **fish** | All | `~/.local/share/fish/fish_history` | ✅ Full |
| **PowerShell** | Windows/Linux/Mac | `%APPDATA%\...\ConsoleHost_history.txt` | ✅ Full |
| **CMD** | Windows | `%LOCALAPPDATA%\clink\.history` | ⚠️ Requires Clink |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate command list |
| `Enter` | Select and inject command |
| `Ctrl+A` | Select all text in search box |
| `F` or `Ctrl+D` | Toggle favorite ⭐ |
| `Delete` | Remove command from history |
| `Escape` | Close without selecting |

## How It Works

1. **Read**: CmdPop reads history files from all installed shells
2. **Store**: Commands are deduplicated and stored in SQLite (`~/.cmdpop/history.db`)
3. **Listen**: When started with `cmdpop start`, listens globally for the hotkey
4. **Show**: Hotkey opens a floating TUI overlay with fuzzy search
5. **Inject**: Selected command is typed back into the active terminal
6. **Remember**: Favorite commands and run counts persist across sessions

## Security

- ✅ **No network calls** — fully local, no cloud sync
- ✅ **Sensitive filtering** — commands with keywords like "password", "token", "secret" are never stored
- ✅ **SQLite database** — stored at `~/.cmdpop/history.db` with user-only permissions
- ✅ **No plaintext logging** of commands

## Development

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
python tests/generate_tests.py  # Generate test fixtures
pytest tests/ -v                 # Run test suite
```

### Type checking

```bash
mypy src/cmdpop/
```

### Linting

```bash
ruff check src/ tests/
```

## Architecture

```
src/cmdpop/
├── main.py                  # CLI entry point, hotkey daemon
├── app.py                   # Textual TUI application
├── history/                 # Shell history readers
│   ├── base.py             # HistoryEntry & HistoryReader base class
│   ├── bash_reader.py      # ~/.bash_history parser
│   ├── zsh_reader.py       # ~/.zsh_history parser (handles EXTENDED_HISTORY)
│   ├── fish_reader.py      # ~/.local/share/fish/fish_history parser
│   ├── powershell_reader.py # PSReadLine history parser
│   └── cmd_reader.py       # Clink history parser
├── injector/               # Cross-platform command injection
│   ├── base.py            # Injector base class
│   ├── windows.py         # pyautogui + win32 injection
│   ├── linux.py           # xdotool / ydotool injection
│   └── mac.py             # AppleScript injection
├── storage/
│   └── db.py              # SQLite database layer
├── config/
│   └── settings.py        # TOML config loader
└── utils/
    └── platform.py        # OS/shell detection
```

## Testing

CmdPop features **self-generating tests**: the `generate_tests.py` script:

1. Reads real shell history samples from `tests/fixtures/history_samples/`
2. Detects edge cases (timestamps, multi-line, special chars, unicode)
3. Generates parametrized pytest test cases automatically
4. Is idempotent (safe to run multiple times)

All tests are async-first (using `pytest-asyncio`) and include:

- **test_history_readers.py** — auto-generated + manual parsing tests
- **test_storage.py** — SQLite CRUD and search tests
- **test_fuzzy_search.py** — fuzzy matching and ranking tests
- **test_dedup.py** — deduplication logic
- **test_injector.py** — command injection (mocked OS calls)

## Requirements

- **Python 3.11+**
- **Core**:
  - `textual` — modern TUI framework
  - `rapidfuzz` — fuzzy search
  - `aiosqlite` — async SQLite
  - `pynput` — global hotkey listener
  - `pyautogui` — command injection fallback
  - `pyperclip` — clipboard fallback
  - `rich` — terminal formatting

- **Platform-specific**:
  - **Windows**: `pywin32` (for better window detection)
  - **Linux**: optional `xdotool` or `ydotool` (fallback to pyautogui)
  - **Mac**: optional (uses `osascript` from system)

- **Dev**: `pytest`, `pytest-asyncio`, `ruff`, `mypy`

## Troubleshooting

### Hotkey not working

Check if the hotkey is correctly configured:

```bash
cmdpop config | grep hotkey
```

If the daemon is running, try `cmdpop open` manually to test the picker.

### Commands not appearing

Sync history first:

```bash
cmdpop sync
```

Then check if your shell's history file is readable:

```bash
cat ~/.bash_history
cat ~/.zsh_history
cat ~/.local/share/fish/fish_history
```

### Injection not working

Try the clipboard fallback manually:

```bash
echo "git status" | xclip -selection clipboard  # Linux
echo "git status" | pbcopy                       # Mac
```

If that works, your shell may need special handling. File an issue!

## Contributing

Contributions welcome! Areas for enhancement:

- [ ] More shell support (ksh, tcsh, nushell)
- [ ] Theme customization
- [ ] Command tagging and filtering
- [ ] Command history sync across machines
- [ ] Better Wayland support
- [ ] Performance optimization for very large histories

## License

MIT — see LICENSE file

## Acknowledgments

CmdPop stands on the shoulders of:

- **textual** — amazing modern Python TUI framework
- **rapidfuzz** — blazing fast fuzzy matching
- **pynput** — cross-platform keyboard control
- **fzf**, **Atuin**, **McFly** — for inspiration