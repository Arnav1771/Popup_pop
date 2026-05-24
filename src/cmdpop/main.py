"""CmdPop CLI entry point and hotkey daemon."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def sync_history() -> None:
    """Sync shell history files into CmdPop database."""
    print("Syncing shell history...")

    from cmdpop.config.settings import Settings
    from cmdpop.history.bash_reader import BashReader
    from cmdpop.history.cmd_reader import CmdReader
    from cmdpop.history.fish_reader import FishReader
    from cmdpop.history.powershell_reader import PowerShellReader
    from cmdpop.history.zsh_reader import ZshReader
    from cmdpop.storage.db import CommandDatabase

    settings = Settings()
    db = CommandDatabase()
    await db.init()

    readers = [
        BashReader(),
        ZshReader(),
        FishReader(),
        PowerShellReader(),
        CmdReader(),
    ]

    all_entries = []
    for reader in readers:
        try:
            entries = reader.read()
            all_entries.extend(entries)
            if entries:
                print(f"  {reader.__class__.__name__}: {len(entries)} commands")
        except Exception as e:
            logger.warning(f"Failed to read history from {reader.__class__.__name__}: {e}")

    # Upsert commands to database
    exclude_patterns = settings.get_exclude_patterns()
    await db.upsert_commands(all_entries, exclude_patterns)

    print(f"✓ Synced {len(all_entries)} command entries")


async def open_picker() -> None:
    """Open the command picker immediately."""
    print("Opening CmdPop picker...")

    from cmdpop.app import CmdPopApp
    from cmdpop.config.settings import Settings
    from cmdpop.injector import get_injector
    from cmdpop.storage.db import CommandDatabase

    # Sync history first
    await sync_history()

    settings = Settings()
    db = CommandDatabase()
    await db.init()

    app = CmdPopApp(db)
    selected = await app.open_picker()

    if selected:
        print(f"Selected: {selected}")
        injector = get_injector()
        injector.inject_with_fallback(selected)
    else:
        print("Cancelled")


def start_daemon() -> None:
    """Start the CmdPop hotkey daemon."""
    from cmdpop.config.settings import Settings

    try:
        from pynput.keyboard import GlobalHotKeys
    except ImportError as e:
        print(f"Error: pynput not available or platform not supported: {e}", file=sys.stderr)
        print("Run 'cmdpop open' manually to use the picker", file=sys.stderr)
        sys.exit(1)

    print("Starting CmdPop daemon...")

    settings = Settings()
    hotkey = settings.get_hotkey()

    print(f"Listening for hotkey: {hotkey}")
    print("Press Ctrl+C to exit")

    # Parse hotkey into pynput format
    # Convert "ctrl+alt+h" to "<ctrl>+<alt>+h"
    hotkey_formatted = "<" + hotkey.replace("+", ">+<") + ">"

    def on_hotkey() -> None:
        """Handle hotkey activation."""
        try:
            asyncio.run(open_picker())
        except Exception as e:
            logger.error(f"Error opening picker: {e}")

    try:
        with GlobalHotKeys({hotkey_formatted: on_hotkey}) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\nDaemon stopped")


def show_config() -> None:
    """Show current configuration."""
    from cmdpop.config.settings import Settings

    settings = Settings()

    print("CmdPop Configuration")
    print("=" * 50)
    print(f"Config file: {settings.config_path}")
    print()

    for section, values in settings.data.items():
        print(f"[{section}]")
        for key, value in values.items():
            print(f"  {key} = {value}")
        print()


def generate_tests() -> None:
    """Generate tests from fixtures."""
    try:
        from tests.generate_tests import main as generate_main

        generate_main()
    except Exception as e:
        print(f"Error generating tests: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="cmdpop",
        description="Cross-platform terminal command history picker",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("start", help="Start CmdPop hotkey daemon")
    subparsers.add_parser("open", help="Open picker manually (no daemon)")
    subparsers.add_parser("sync", help="Sync shell history files into CmdPop DB now")
    subparsers.add_parser("generate-tests", help="Regenerate test suite from fixtures")
    subparsers.add_parser("config", help="Print current config path and values")

    args = parser.parse_args()

    try:
        match args.command:
            case "start" | None:
                start_daemon()
            case "open":
                asyncio.run(open_picker())
            case "sync":
                asyncio.run(sync_history())
            case "generate-tests":
                generate_tests()
            case "config":
                show_config()
            case _:
                parser.print_help()
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
