"""Core CLI class with the main API."""

from typing import Optional, List, Dict, Any, Callable, Awaitable
from contextlib import contextmanager
import json

from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.syntax import Syntax
from rich import box

from app.cli.theme import Theme
from app.cli.components import (
    Header,
    Section,
    Message,
    DataTable,
    ProgressDisplay,
    CodeBlock,
    StatusLine,
)
from app.cli.formatters import (
    EventCardFormatter,
    ImportResultFormatter,
    ProgressUpdateFormatter,
)


class CLI:
    """Main CLI interface with clean visual design."""

    def __init__(self, width: int = 100, theme: Optional[Theme] = None):
        """Initialize CLI with theme and components."""
        self.width = width
        self.theme = theme or Theme.default()
        self.console = Console(width=width)

        # Initialize components
        self.header_component = Header(self.console, self.theme)
        self.section_component = Section(self.console, self.theme)
        self.message = Message(self.console, self.theme)
        self.table_component = DataTable(self.console, self.theme)
        self.progress_component = ProgressDisplay(self.console, self.theme)
        self.code_component = CodeBlock(self.console, self.theme)

        # Initialize formatters
        self.event_formatter = EventCardFormatter(self.console, self.theme)
        self.import_formatter = ImportResultFormatter(self.console, self.theme)
        self.progress_formatter = ProgressUpdateFormatter(self.console, self.theme)

        # Progress tracking
        self._progress = None
        self._task_id = None

    # ============= Core Display Methods =============

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Display a prominent header."""
        self.header_component.render(title, subtitle)

    def section(self, title: str) -> None:
        """Display a section header."""
        self.section_component.render(title)

    def info(self, message: str) -> None:
        """Display an info message."""
        self.message.info(message)

    def success(self, message: str) -> None:
        """Display a success message."""
        self.message.success(message)

    def error(self, message: str) -> None:
        """Display an error message."""
        self.message.error(message)

    def warning(self, message: str) -> None:
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

    def update_progress(self, percent: float, message: Optional[str] = None) -> None:
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
            spinner_style=self.theme.colors.primary,
        ):
            yield

    # ============= Data Display Methods =============

    def table(self, data: List[Dict[str, Any]], title: Optional[str] = None) -> None:
        """Display data in a table."""
        self.table_component.render(data, title)

    def json(self, data: dict, title: Optional[str] = None) -> None:
        """Display JSON data with syntax highlighting."""
        self.code_component.render(
            json.dumps(data, indent=2, default=str), language="json", title=title
        )

    def code(
        self, code: str, language: str = "python", title: Optional[str] = None
    ) -> None:
        """Display code with syntax highlighting."""
        self.code_component.render(code, language, title)

    # ============= Event-Specific Methods =============

    def event_card(self, event_data: dict) -> None:
        """Display event data in a nice card format."""
        self.event_formatter.render(event_data)

    def progress_update(self, update: dict) -> None:
        """Display a progress update from the import system."""
        self.progress_formatter.render(update)

    def import_result(self, result, show_raw: bool = False) -> None:
        """Display import result with all details."""
        self.import_formatter.render(result, show_raw)

    def data_quality_check(self, event_data) -> None:
        """Display data quality/completeness check."""
        # This is now handled inside import_formatter
        pass

    def raw_data(self, data: dict, title: str = "Raw Data") -> None:
        """Display raw data."""
        # For now, just use JSON display
        self.json(data, title)

    def image_search_results(self, search_data: dict) -> None:
        """Display image search results."""
        # This is now handled inside import_formatter
        pass

    # ============= Utility Methods =============

    def rule(self, title: Optional[str] = None, style: str = "dim") -> None:
        """Draw a horizontal rule."""
        self.console.rule(title or "", style=style)

    def clear(self) -> None:
        """Clear the terminal."""
        self.console.clear()

    def _safe_str(self, value: Any) -> str:
        """Convert any value to string safely."""
        if value is None:
            return ""
        if hasattr(value, "__str__"):
            return str(value)
        return repr(value)
