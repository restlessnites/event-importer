import pytest
import pytest_asyncio
from app.interfaces.cli import get_cli
from app.shared.http import HTTPService
from app.services.claude import ClaudeService
from app.config import get_config, Config


@pytest.fixture(scope="session")
def cli():
    """Provides a CLI instance for tests."""
    return get_cli()


@pytest.fixture(scope="session")
def config() -> Config:
    """Provides a config instance for tests."""
    return get_config()


@pytest_asyncio.fixture(scope="function")
async def http_service(config: Config):
    """Provides a single HTTPService instance for the entire test session."""
    service = HTTPService(config)
    yield service
    await service.close()


@pytest.fixture(scope="session")
def claude_service(config: Config):
    """Provides a ClaudeService instance for tests."""
    return ClaudeService(config)
