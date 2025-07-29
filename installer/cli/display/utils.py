"""Display utility functions."""

import os


def clear_terminal():
    """Clear the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")  # noqa: S605
