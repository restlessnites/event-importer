"""Core CLI class - cleaned up and using the theme system."""

from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import json

from rich.console import Console

from app.interfaces.cli.theme import Theme
from app.interfaces.cli.formatters import (
    ProgressUpdateFormatter,
    ImportResultFormatter,
    EventCardFormatter,
)

from app.interfaces.cli.components import (
    Header,
    Section,
    Message,
    DataTable,
    ProgressDisplay,
    CodeBlock,
    Spacer,
)
from app.interfaces.cli.error_capture import CLIErrorDisplay, get_error_capture


class CLI:
    """Main CLI interface with proper theming."""

    def __init__(self, width: int = 100, theme: Optional[Theme] = None):
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
        self._progress = None
        self._task_id = None

        # Error capture
        self.error_capture = get_error_capture()
        self.error_display = CLIErrorDisplay(self)

    # ============= Core Display Methods =============

    def header(self, title: str, subtitle: Optional[str] = None):
        """Display a prominent header."""
        self.header_component.render(title, subtitle)

    def section(self, title: str):
        """Display a section header."""
        self.section_component.render(title)

    def info(self, message: str):
        """Display an info message."""
        self.message.info(message)

    def success(self, message: str):
        """Display a success message."""
        self.message.success(message)

    def error(self, message: str):
        """Display an error message."""
        self.message.error(message)

    def warning(self, message: str):
        """Display a warning message."""
        self.message.warning(message)

    # ============= Progress Methods =============

    @contextmanager
    def progress(self, description: str = "Processing"):
        """Context manager for progress tracking."""
        progress = self.progress_component.create(description)
        self._progress = progress
        self._task_id = progress.add_task(description, total=100)

        with progress:
            yield self

        self._progress = None
        self._task_id = None

    def update_progress(self, percent: float, message: Optional[str] = None):
        """Update progress bar."""
        if self._progress and self._task_id is not None:
            if message:
                self._progress.update(self._task_id, description=message)
            self._progress.update(self._task_id, completed=percent)

    @contextmanager
    def spinner(self, message: str):
        """Show a spinner for indeterminate progress."""
        with self.console.status(
            f"{self.theme.icons.spinner} {message}",
            spinner="dots",
            spinner_style=self.theme.typography.info_style,
        ):
            yield

    # ============= Data Display Methods =============

    def table(self, data: List[Dict[str, Any]], title: Optional[str] = None):
        """Display data in a table."""
        self.table_component.render(data, title)

    def json(self, data: dict, title: Optional[str] = None):
        """Display JSON data with syntax highlighting."""
        self.code_component.render(
            json.dumps(data, indent=2, default=str), language="json", title=title
        )

    def code(self, code: str, language: str = "python", title: Optional[str] = None):
        """Display code with syntax highlighting."""
        self.code_component.render(code, language, title)

    def rule(self, title: Optional[str] = None, style: Optional[str] = None):
        """Draw a horizontal rule using theme spacing."""
        self.spacer.add(self.theme.spacing.before_rule)
        style = style or self.theme.typography.muted_style
        self.console.rule(title or "", style=style)
        self.spacer.add(self.theme.spacing.after_rule)

    def clear(self):
        """Clear the terminal."""
        self.console.clear()

    # ============= Error Capture Methods =============

    def clear_errors(self):
        """Clear captured errors."""
        self.error_capture.clear()

    def show_captured_errors(self, title: str = "Captured Errors"):
        """Display any captured errors."""
        self.error_display.show_captured_errors(self.error_capture, title)

    # ============= Your existing event methods, now using theme =============

    def progress_update(self, update: dict):
        """Display a progress update from the import system."""

        formatter = ProgressUpdateFormatter(self.console, self.theme)
        formatter.render(update)

    def import_result(self, result, show_raw: bool = False):
        """Display import result with all details."""

        formatter = ImportResultFormatter(self.console, self.theme)
        formatter.render(result, show_raw)

    def event_card(self, event_data: dict):
        """Display event data in a nice card format."""

        formatter = EventCardFormatter(self.console, self.theme)
        formatter.render(event_data)
