"""Core CLI class - cleaned up and using the theme system."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.progress import Progress

from app.interfaces.cli.components import (
    CodeBlock,
    DataTable,
    Header,
    Message,
    ProgressDisplay,
    Section,
    Spacer,
)
from app.interfaces.cli.error_capture import CLIErrorDisplay, get_error_capture
from app.interfaces.cli.formatters import (
    EventCardFormatter,
    ImportResultFormatter,
    ProgressUpdateFormatter,
)
from app.interfaces.cli.theme import Theme
from app.schemas import ImportResult


class CLI:
    """Main CLI interface with proper theming."""

    def __init__(self: CLI, width: int = 100, theme: Theme | None = None) -> None:
        """Initialize CLI with theme and components."""
        self.width = width
        self.theme = theme or Theme()
        self.console = Console(width=width)

        # Initialize components with theme
        self.header_component = Header(self.console, self.theme)
        self.section_component = Section(self.console, self.theme)
        self.message = Message(self.console, self.theme)
        self.table_component = DataTable(self.console, self.theme)
        self.progress_component = ProgressDisplay(self.console, self.theme)
        self.code_component = CodeBlock(self.console, self.theme)
        self.spacer = Spacer(self.console, self.theme)

        # Progress tracking
        self._progress: Progress | None = None
        self._task_id: Any | None = None

        # Error capture
        self.error_capture = get_error_capture()
        self.error_display = CLIErrorDisplay(self)

    # ============= Core Display Methods =============

    def header(self: CLI, title: str, subtitle: str | None = None) -> None:
        """Display a prominent header."""
        self.header_component.render(title, subtitle)

    def section(self: CLI, title: str) -> None:
        """Display a section header."""
        self.section_component.render(title)

    def info(self: CLI, message: str) -> None:
        """Display an info message."""
        self.message.info(message)

    def success(self: CLI, message: str) -> None:
        """Display a success message."""
        self.message.success(message)

    def error(self: CLI, message: str) -> None:
        """Display an error message."""
        self.message.error(message)

    def warning(self: CLI, message: str) -> None:
        """Display a warning message."""
        self.message.warning(message)

    # ============= Progress Methods =============

    @contextmanager
    def progress(self: CLI, description: str = "Processing") -> Iterator[CLI]:
        """Context manager for progress tracking."""
        progress = self.progress_component.create(description)
        self._progress = progress
        self._task_id = progress.add_task(description, total=100)

        with progress:
            yield self

        self._progress = None
        self._task_id = None

    def update_progress(self: CLI, percent: float, message: str | None = None) -> None:
        """Update progress bar."""
        if self._progress and self._task_id is not None:
            if message:
                self._progress.update(self._task_id, description=message)
            self._progress.update(self._task_id, completed=percent)

    @contextmanager
    def spinner(self: CLI, message: str) -> Iterator[None]:
        """Show a spinner for indeterminate progress."""
        with self.console.status(
            f"{self.theme.icons.spinner} {message}",
            spinner="dots",
            spinner_style=self.theme.typography.info_style,
        ):
            yield

    # ============= Data Display Methods =============

    def table(self: CLI, data: list[dict[str, Any]], title: str | None = None) -> None:
        """Display data in a table."""
        self.table_component.render(data, title)

    def json(self: CLI, data: dict, title: str | None = None) -> None:
        """Display JSON data with syntax highlighting."""
        self.code_component.render(
            json.dumps(data, indent=2, default=str),
            language="json",
            title=title,
        )

    def code(
        self: CLI,
        code: str,
        language: str = "python",
        title: str | None = None,
    ) -> None:
        """Display code with syntax highlighting."""
        self.code_component.render(code, language, title)

    def rule(self: CLI, title: str | None = None, style: str | None = None) -> None:
        """Draw a horizontal rule using theme spacing."""
        self.spacer.add(self.theme.spacing.before_rule)
        style = style or self.theme.typography.muted_style
        self.console.rule(title or "", style=style)
        self.spacer.add(self.theme.spacing.after_rule)

    def clear(self: CLI) -> None:
        """Clear the terminal."""
        self.console.clear()

    # ============= Error Capture Methods =============

    def clear_errors(self: CLI) -> None:
        """Clear captured errors."""
        self.error_capture.clear()

    def show_captured_errors(self: CLI, title: str = "Captured Errors") -> None:
        """Display any captured errors."""
        self.error_display.show_captured_errors(self.error_capture, title)

    # ============= Your existing event methods, now using theme =============

    def progress_update(self: CLI, update: dict) -> None:
        """Display a progress update from the import system."""
        formatter = ProgressUpdateFormatter(self.console, self.theme)
        formatter.render(update)

    def import_result(self: CLI, result: ImportResult, show_raw: bool = False) -> None:
        """Display import result with all details."""
        formatter = ImportResultFormatter(self.console, self.theme)
        formatter.render(result, show_raw)

    def event_card(self: CLI, event_data: dict) -> None:
        """Display event data in a nice card format."""
        formatter = EventCardFormatter(self.console, self.theme)
        formatter.render(event_data)
