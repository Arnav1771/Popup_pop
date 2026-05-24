"""Textual TUI application for CmdPop."""

import logging
from datetime import datetime

from textual.app import ComposeResult, RenderableType
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, ListItem, ListView, Static, Label
from textual.reactive import reactive

from cmdpop.storage.db import CommandDatabase, CommandRow

logger = logging.getLogger(__name__)


class CommandItem(ListItem):
    """A single command item in the list."""

    def __init__(self, row: CommandRow):
        """Initialize a command item.
        
        Args:
            row: CommandRow from database
        """
        super().__init__()
        self.row = row

    def render(self) -> RenderableType:
        """Render the command item."""
        from rich.text import Text

        # Build display string
        favorite_marker = "★ " if self.row.is_favorite else "  "
        command_text = self.row.command[:60]
        if len(self.row.command) > 60:
            command_text += "…"

        # Add source shell badge
        shell_badge = ""
        if self.row.source_shell:
            shell_badge = f" [{self.row.source_shell}]"

        # Add time
        time_str = ""
        if self.row.last_seen:
            time_str = f" {self._relative_time(self.row.last_seen)}"

        text = f"{favorite_marker}{command_text}{shell_badge}{time_str}"
        return Text(text)

    @staticmethod
    def _relative_time(dt: datetime) -> str:
        """Format time relative to now."""
        if dt is None:
            return ""

        now = datetime.now()
        delta = now - dt

        seconds = delta.total_seconds()
        if seconds < 60:
            return "now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days}d ago"
        else:
            weeks = int(seconds / 604800)
            return f"{weeks}w ago"


class PreviewPanel(Static):
    """Panel showing command details."""

    current_command: reactive[str | None] = reactive(None)

    def render(self) -> RenderableType:
        """Render the preview panel."""
        from rich.text import Text

        if not self.current_command:
            return Text("No command selected")

        return Text(f"Command: {self.current_command}")


class CmdPopApp:
    """Textual app for CmdPop command picker."""

    def __init__(self, db: CommandDatabase):
        """Initialize the app.
        
        Args:
            db: CommandDatabase instance
        """
        self.db = db
        self.selected_command: str | None = None

    async def open_picker(self) -> str | None:
        """Open the command picker overlay.
        
        Returns:
            Selected command, or None if cancelled.
        """
        from textual.app import App

        class CommandPickerApp(App):
            """The actual Textual app."""

            def __init__(self, db: CommandDatabase):
                super().__init__()
                self.db = db
                self.selected_command: str | None = None
                self.search_query = ""
                self.commands: list[CommandRow] = []

            def compose(self) -> ComposeResult:
                """Compose the UI."""
                yield Vertical(
                    Input(id="search", placeholder="Search commands..."),
                    ListView(id="commands"),
                    PreviewPanel(id="preview"),
                    id="container",
                )

            async def on_mount(self) -> None:
                """Initialize on mount."""
                # Load all commands
                self.commands = await self.db.get_all(limit=500)
                await self._update_list()

                # Focus search input
                search = self.query_one("#search", Input)
                search.focus()

            async def _update_list(self, query: str = "") -> None:
                """Update command list based on search query."""
                if query:
                    self.commands = await self.db.search(query, limit=100)
                else:
                    self.commands = await self.db.get_all(limit=100)

                list_view = self.query_one("#commands", ListView)
                list_view.clear()

                for row in self.commands:
                    list_view.append(CommandItem(row))

            async def on_input_changed(self, event):
                """Handle search input change."""
                if event.input.id == "search":
                    self.search_query = event.value
                    await self._update_list(event.value)

            def on_list_view_selected(self, event):
                """Handle command selection."""
                item = event.item
                if isinstance(item, CommandItem):
                    self.selected_command = item.row.command
                    self.exit()

            def on_key(self, event):
                """Handle keyboard shortcuts."""
                if event.key == "escape":
                    self.exit()
                elif event.key == "f":
                    # Toggle favorite
                    list_view = self.query_one("#commands", ListView)
                    if list_view.index is not None and list_view.index < len(self.commands):
                        command = self.commands[list_view.index].command
                        # Schedule async operation
                        self.call_later(self._toggle_favorite, command)
                elif event.key == "delete":
                    # Delete command
                    list_view = self.query_one("#commands", ListView)
                    if list_view.index is not None and list_view.index < len(self.commands):
                        command = self.commands[list_view.index].command
                        self.call_later(self._delete_command, command)

            async def _toggle_favorite(self, command: str) -> None:
                """Toggle favorite status."""
                await self.db.toggle_favorite(command)
                await self._update_list(self.search_query)

            async def _delete_command(self, command: str) -> None:
                """Delete a command."""
                await self.db.delete_command(command)
                await self._update_list(self.search_query)

        app = CommandPickerApp(self.db)
        await app.run_async()
        return app.selected_command
