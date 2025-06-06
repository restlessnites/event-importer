"""Visual style definitions and utilities."""

from typing import Optional
from rich import box


# Table styles
TABLE_STYLE = {
    "box": box.SIMPLE_HEAD,
    "show_header": True,
    "header_style": "bold",
    "title_style": "bold blue",
    "border_style": "bright_black",
    "row_styles": ["none", "dim"],
    "pad_edge": False,
    "padding": (0, 1),
}

COMPACT_TABLE_STYLE = {
    **TABLE_STYLE,
    "box": box.SIMPLE,
    "show_header": False,
    "padding": (0, 1, 0, 0),
}

# Progress bar styles
PROGRESS_STYLE = {
    "complete_style": "bright_blue",
    "finished_style": "bright_green",
    "pulse_style": "cyan",
}

# Panel styles
PANEL_STYLE = {
    "box": box.ROUNDED,
    "border_style": "bright_black",
    "padding": (0, 1),
}

ERROR_PANEL_STYLE = {
    **PANEL_STYLE,
    "border_style": "red",
    "title_style": "bold red",
}

SUCCESS_PANEL_STYLE = {
    **PANEL_STYLE,
    "border_style": "green",
    "title_style": "bold green",
}


def format_timestamp(dt) -> str:
    """Format datetime for display."""
    if hasattr(dt, "strftime"):
        return dt.strftime("%H:%M:%S")
    elif isinstance(dt, str):
        # Try to parse ISO format
        try:
            from datetime import datetime

            return datetime.fromisoformat(dt.replace("Z", "+00:00")).strftime(
                "%H:%M:%S"
            )
        except:
            return "??:??:??"
    return "??:??:??"


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def humanize_number(num: float) -> str:
    """Format number for human reading."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(int(num))


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """Pluralize a word based on count."""
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"
