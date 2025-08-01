"""Test helpers and utilities."""

from app.config import Config
from app.core.importer import EventImporter


def create_test_importer(config: Config, service_mocks: dict | None = None) -> EventImporter:
    """Create an EventImporter instance with optional service mocks.

    Args:
        config: Configuration object
        service_mocks: Dictionary of service name -> mock object

    Returns:
        EventImporter instance with mocked services
    """
    importer = EventImporter(config)

    if service_mocks:
        for service_name, mock_service in service_mocks.items():
            if service_name in importer.services:
                importer.services[service_name] = mock_service

    return importer
