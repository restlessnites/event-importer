""" Integrations. """

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


def get_integration(name: str) -> type:
    """Get a specific integration by name"""
    integrations = get_available_integrations()
    if name not in integrations:
        error_msg = f"Integration '{name}' not found. Available: {list(integrations.keys())}"
        raise ValueError(error_msg)
    return integrations[name]
