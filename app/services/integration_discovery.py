"""Integration discovery system."""

import importlib
import sys
import traceback
from importlib.metadata import entry_points
from pathlib import Path

from app.integrations.base import Integration


def get_available_integrations() -> dict[str, type]:
    """Auto-discover integrations via entry points or directory scanning"""
    # Check if we're running in a packaged app
    if getattr(sys, "frozen", False):
        # In packaged app, scan the integrations directory
        integrations_dir = Path(__file__).parent.parent / "integrations"
        return _discover_from_directory(integrations_dir)
    # In development, use entry points
    return _discover_from_entry_points()


def _discover_from_directory(integrations_dir: Path) -> dict[str, type]:
    """Discover integrations by scanning directory."""
    integrations = {}

    for path in integrations_dir.iterdir():
        if path.is_dir() and not path.name.startswith("__"):
            base_module_path = path / "base.py"
            if base_module_path.exists():
                try:
                    # Import the base module
                    module = importlib.import_module(
                        f"app.integrations.{path.name}.base"
                    )
                    # Look for Integration subclasses
                    for item_name in dir(module):
                        item = getattr(module, item_name)
                        if (
                            isinstance(item, type)
                            and issubclass(item, Integration)
                            and item is not Integration
                            and item.__module__ == module.__name__
                        ):
                            integrations[path.name] = item
                except Exception as e:
                    print(
                        f"Failed to load integration from {path.name}: {e}",
                        file=sys.stderr,
                    )
                    traceback.print_exc(file=sys.stderr)

    return integrations


def _discover_from_entry_points() -> dict[str, type]:
    """Discover integrations from entry points."""
    integrations = {}

    try:
        eps = entry_points(group="app.integrations")
        for ep in eps:
            try:
                integration = ep.load()
                integrations[ep.name] = integration
            except ImportError as e:
                print(f"Failed to load integration {ep.name}: {e}")
    except Exception as e:
        print(f"Error discovering integrations: {e}")

    return integrations
