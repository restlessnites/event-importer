"""Error formatting and display for CLI."""

from typing import Optional
from dataclasses import dataclass

from rich.console import Console

from app.cli.theme import Theme
from app.cli.components import Spacer
from app.cli.utils import format_timestamp


@dataclass
class ErrorDetails:
    """Store error details for later display."""

    error_type: str
    message: str
    url: Optional[str] = None
    service: Optional[str] = None
    status_code: Optional[int] = None
    timestamp: Optional[str] = None
    context: Optional[str] = None


class ErrorFormatter:
    """Format errors for CLI display."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.spacer = Spacer(console, theme)

    def format_inline_error(
        self, error_type: str, service: Optional[str] = None
    ) -> str:
        """Format an error for inline display during progress."""
        # Common expected errors get friendly messages
        friendly_errors = {
            "403": "Access blocked (expected)",
            "404": "Page not found",
            "429": "Rate limited",
            "timeout": "Request timed out",
        }

        if str(error_type) in friendly_errors:
            message = friendly_errors[str(error_type)]
        else:
            message = f"Error: {error_type}"

        if service:
            message = f"{service}: {message}"

        return message

    def render_progress_error(self, error_details: ErrorDetails, progress: float = 0):
        """Render an error as part of progress updates."""
        timestamp = error_details.timestamp or format_timestamp("now")

        # Build status line that matches progress format
        parts = []

        # Timestamp in brackets
        parts.append(f"[{self.theme.typography.dim_style}][{timestamp}][/]")

        # Warning icon for non-fatal errors
        parts.append(
            f"[{self.theme.typography.warning_style}]{self.theme.icons.warning}[/]"
        )

        # Status
        parts.append(f"[{self.theme.typography.warning_style}]Note      [/]")

        # Progress percentage
        parts.append(f"[{self.theme.typography.muted_style}]{progress:3.0f}%[/]")

        # Friendly message
        message = self.format_inline_error(
            error_details.status_code or error_details.error_type, error_details.service
        )
        parts.append(message)

        self.console.print(" ".join(parts))
