"""
Provides a centralized console object for consistent UI output.
"""

from rich.console import Console

_console: Console | None = None


def get_console() -> Console:
    """Gets a singleton Console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console
