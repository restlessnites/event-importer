"""Integrations."""

from importlib.metadata import entry_points


def get_available_integrations() -> dict[str, type]:
    """Auto-discover integrations via entry points"""
    integrations = {}

    try:
        # Get integrations from entry points
        eps = entry_points(group="app.integrations")
        for ep in eps:
            try:
                integration = ep.load()
                integrations[ep.name] = integration
            except ImportError as e:
                print(f"Failed to load integration {ep.name}: {e}")
    except (ValueError, TypeError, KeyError) as e:
        print(f"Error discovering integrations: {e}")

    return integrations
