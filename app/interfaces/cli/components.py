"""Reusable CLI components that properly use the theme."""

from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax

from app.interfaces.cli.theme import Theme


class Spacer:
    """Helper to add consistent spacing."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def add(self, lines: int):
        """Add specific number of empty lines."""
        for _ in range(lines):
            self.console.print()


class Header:
    """Header component with proper spacing and styling."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.spacer = Spacer(console, theme)

    def render(self, title: str, subtitle: Optional[str] = None):
        """Render a header with theme-based styling."""
        # Add spacing before
        self.spacer.add(self.theme.spacing.before_header)

        # Transform and style title
        title_text = self.theme.transform_text(
            title, self.theme.typography.header_transform
        )
        self.console.print(Text(title_text, style=self.theme.typography.header_style))

        # Subtitle if provided
        if subtitle:
            subtitle_text = self.theme.transform_text(
                subtitle, self.theme.typography.subheader_transform
            )
            self.console.print(
                Text(subtitle_text, style=self.theme.typography.subheader_style)
            )
        # Add spacing after
        self.spacer.add(self.theme.spacing.after_header)


class Section:
    """Section divider with consistent spacing."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.spacer = Spacer(console, theme)

    def render(self, title: str):
        """Render a section divider."""
        # Add spacing before
        self.spacer.add(self.theme.spacing.before_section)

        # Transform and style title
        title_text = self.theme.transform_text(
            title, self.theme.typography.section_transform
        )
        self.console.print(Text(title_text, style=self.theme.typography.section_style))

        # Underline only under text
        if self.theme.typography.section_underline:
            underline_length = len(title_text)
            self.console.print(
                self.theme.typography.section_underline * underline_length,
                style=self.theme.typography.muted_style,
            )

        # Add spacing after
        self.spacer.add(self.theme.spacing.after_section)


class Message:
    """Status messages with consistent icon and styling."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def info(self, text: str):
        """Info message."""
        self.console.print(
            f"{self.theme.icons.info} {text}", style=self.theme.typography.info_style
        )

    def success(self, text: str):
        """Success message."""
        self.console.print(
            f"{self.theme.icons.success} {text}",
            style=self.theme.typography.success_style,
        )

    def error(self, text: str):
        """Error message."""
        self.console.print(
            f"{self.theme.icons.error} {text}", style=self.theme.typography.error_style
        )

    def warning(self, text: str):
        """Warning message."""
        self.console.print(
            f"{self.theme.icons.warning} {text}",
            style=self.theme.typography.warning_style,
        )


class DataTable:
    """Table display using theme settings."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.spacer = Spacer(console, theme)

    def render(self, data: List[Dict[str, Any]], title: Optional[str] = None):
        """Render a data table."""
        if not data:
            return

        table = Table(
            title=title,
            title_justify="left",
            box=self.theme.layout.table_box,
            border_style=self.theme.layout.table_border_style,
            padding=(0, 1),
            show_header=True,
            header_style="bold",
        )

        # Add columns
        for key in data[0].keys():
            table.add_column(key)

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

        self.console.print(table)
        self.spacer.add(self.theme.spacing.after_table)


class ProgressDisplay:
    """Progress display using theme colors."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def create(self, description: str = "Processing") -> Progress:
        """Create a progress bar."""
        return Progress(
            SpinnerColumn(spinner_name="dots", style=self.theme.typography.info_style),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                complete_style=self.theme.typography.info_style,
                finished_style=self.theme.typography.success_style,
            ),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )


class CodeBlock:
    """Code display with syntax highlighting."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.spacer = Spacer(console, theme)

    def render(self, code: str, language: str = "python", title: Optional[str] = None):
        """Render code with syntax highlighting."""
        if title:
            self.console.print(Text(title, style=self.theme.typography.label_style))

        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            background_color="default",
        )
        self.console.print(syntax)
        self.spacer.add(self.theme.spacing.between_items)
