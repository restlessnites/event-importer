"""Utility functions for the CLI."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse


def format_timestamp(dt: datetime | str) -> str:
    """Format datetime for display."""
    if hasattr(dt, "strftime"):
        return dt.strftime("%H:%M:%S")
    if isinstance(dt, str):
        # Try to parse ISO format
        try:
            return datetime.fromisoformat(dt.replace("Z", "+00:00")).strftime(
                "%H:%M:%S",
            )
        except (ValueError, TypeError):
            return "??:??:??"
    return "??:??:??"


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """Pluralize a word based on count."""
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"


def format_status(status: str) -> str:
    """Format a status string (remove enum cruft)."""
    # Handle "ImportStatus.RUNNING" -> "Running"
    if "." in status:
        status = status.split(".")[-1]
    return status.replace("_", " ").title()


def format_url_for_display(url: str, style: str = "full") -> str:
    """Unified URL formatting.

    Styles:
    - 'full': Complete URL
    - 'domain': Just the domain
    - 'compact': Domain + shortened path
    """
    if style == "full":
        return url

    parsed = urlparse(url)
    domain = parsed.netloc or "unknown"

    if style == "domain":
        return domain

    if style == "compact":
        path = parsed.path
        if len(path) > 30:
            path = f"{path[:15]}...{path[-10:]}"
        return f"{domain}{path}"

    return url
