"""Event Importer - MCP server for importing structured event data from websites."""

__version__ = "0.1.0"
__author__ = "Event Importer Contributors"

# Package-level imports for convenience
from app.schemas import EventData, ImportResult
from app.engine import EventImportEngine
from app.config import Config

__all__ = [
    "EventData",
    "ImportResult",
    "EventImportEngine",
    "Config",
    "__version__",
]
