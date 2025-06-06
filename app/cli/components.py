"""Reusable CLI components."""

from typing import List, Dict, Any, Optional
from datetime import datetime

from rich.console import Console, Group
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.syntax import Syntax

from app.cli.theme import Theme
from app.cli.styles import (
    TABLE_STYLE,
    COMPACT_TABLE_STYLE,
    PANEL_STYLE,
    ERROR_PANEL_STYLE,
    SUCCESS_PANEL_STYLE,
    format_timestamp,
    truncate,
)


class StatusLine:
    """Single line status display."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def render(
        self,
        icon: str,
        status: str,
        message: str,
        timestamp: Optional[str] = None,
        progress: Optional[float] = None,
        style: str = "default",
    ) -> None:
        """Render a status line."""
        parts = []

        # Timestamp
        if timestamp:
            parts.append(f"[{self.theme.colors.text_muted}]{timestamp}[/]")

        # Icon and status
        parts.append(f"[{self.theme.colors.style(style)}]{icon}[/]")
        parts.append(f"[{self.theme.colors.style(style)}]{status:8}[/]")

        # Progress
        if progress is not None:
            parts.append(f"[{self.theme.colors.text_muted}]{progress:3.0f}%[/]")

        # Message
        parts.append(message)

        self.console.print(" ".join(parts))


class ProgressDisplay:
    """Enhanced progress display."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def create(self, description: str = "Processing") -> Progress:
        """Create a progress bar."""
        return Progress(
            SpinnerColumn(spinner_name="dots", style=self.theme.colors.primary),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                complete_style=self.theme.colors.primary_bright,
                finished_style=self.theme.colors.success_bright,
                pulse_style=self.theme.colors.info,
            ),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )


class DataTable:
    """Enhanced table display."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def render(
        self,
        data: List[Dict[str, Any]],
        title: Optional[str] = None,
        compact: bool = False,
    ) -> None:
        """Render a data table."""
        if not data:
            return

        style = COMPACT_TABLE_STYLE if compact else TABLE_STYLE
        table = Table(title=title, **style)

        # Add columns
        for key in data[0].keys():
            table.add_column(
                key, style=self.theme.colors.text if compact else "default"
            )

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

        self.console.print(table)


class Header:
    """Header component."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def render(self, title: str, subtitle: Optional[str] = None) -> None:
        """Render a header."""
        # Clear any previous content with spacing
        self.console.print()

        # Title
        self.console.print(Text(title.upper(), style=self.theme.colors.style("header")))

        # Subtitle
        if subtitle:
            self.console.print(Text(subtitle, style=self.theme.colors.text_muted))

        # Separator
        self.console.print(Rule(style=self.theme.colors.text_muted))
        self.console.print()


class Section:
    """Section divider."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def render(self, title: str) -> None:
        """Render a section divider."""
        # Add spacing based on theme
        for _ in range(self.theme.spacing.md):
            self.console.print()

        # Section title (left-aligned, no centering!)
        self.console.print(
            Text(title.upper(), style=self.theme.colors.style("section"))
        )
        self.console.print("─" * len(title), style=self.theme.colors.text_muted)
        self.console.print()


class Message:
    """Status messages (info, success, error, warning)."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def info(self, text: str) -> None:
        """Info message."""
        self.console.print(
            f"{self.theme.icons.info} {text}", style=self.theme.colors.info
        )

    def success(self, text: str) -> None:
        """Success message."""
        self.console.print(
            f"{self.theme.icons.success} {text}",
            style=self.theme.colors.style("success"),
        )

    def error(self, text: str) -> None:
        """Error message."""
        self.console.print(
            f"{self.theme.icons.error} {text}", style=self.theme.colors.style("error")
        )

    def warning(self, text: str) -> None:
        """Warning message."""
        self.console.print(
            f"{self.theme.icons.warning} {text}",
            style=self.theme.colors.style("warning"),
        )


class CodeBlock:
    """Code display with syntax highlighting."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def render(
        self, code: str, language: str = "python", title: Optional[str] = None
    ) -> None:
        """Render code with syntax highlighting."""
        if title:
            self.console.print()
            self.console.print(Text(title, style=self.theme.colors.style("label")))

        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            background_color="default",
        )
        self.console.print(syntax)
        self.console.print()
