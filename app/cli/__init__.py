"""CLI interface for event importer."""

from app.cli.core import CLI

# Global instance
_cli: CLI | None = None


def get_cli() -> CLI:
    """Get the global CLI instance."""
    global _cli
    if _cli is None:
        _cli = CLI()
    return _cli


__all__ = ["get_cli", "CLI"]
