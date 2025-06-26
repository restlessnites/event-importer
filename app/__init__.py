"""Event Importer - MCP server for importing structured event data from websites."""

__version__ = "0.1.0"
__author__ = "Event Importer Contributors"

# Package-level imports for convenience
from app.config import Config
from app.core.importer import EventImporter
from app.schemas import EventData, ImportResult

__all__ = [
    "Config",
    "EventData",
    "EventImporter",
    "ImportResult",
    "__version__",
]
