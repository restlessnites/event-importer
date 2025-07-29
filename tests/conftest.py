"""Pytest configuration for the test suite."""

from __future__ import annotations

import pytest
from app.interfaces.cli.core import CLI
from rich.console import Console
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_config
from app.services.claude import ClaudeService
from app.services.llm import LLMService
from app.services.openai import OpenAIService
from app.shared.database.connection import (
    get_db_session,
    init_db,
)
from app.shared.database.models import Base
from app.shared.http import HTTPService

TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    return create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a test database session for each test function."""
    connection = engine.connect()
    transaction = connection.begin()
    Base.metadata.create_all(bind=connection)
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    Base.metadata.drop_all(bind=connection)
    connection.close()


@pytest.fixture
def http_service() -> HTTPService:
    """Return an HTTPService instance."""
    return HTTPService(get_config())


@pytest.fixture(scope="session")
def claude_service() -> ClaudeService:
    """Return a ClaudeService instance."""
    return ClaudeService(get_config())


@pytest.fixture(scope="session")
def openai_service(http_service: HTTPService) -> OpenAIService:
    """Return an OpenAIService instance."""
    return OpenAIService(get_config(), http_service)


@pytest.fixture(scope="session")
def llm_service(
    claude_service: ClaudeService, openai_service: OpenAIService
) -> LLMService:
    """Return an LLMService instance."""
    return LLMService(get_config(), claude_service, openai_service)


@pytest.fixture
def run_startup_checks() -> None:
    """Ensure startup checks are run."""
    init_db()


@pytest.fixture
def mock_db_session(monkeypatch) -> None:
    """Mock the database session for tests."""
    monkeypatch.setattr("app.shared.database.connection.SessionLocal", get_db_session)


@pytest.fixture
def cli() -> CLI:
    """Return a CLI instance, forcing interactive mode for consistent testing."""
    # Force interactive mode to ensure all rich components are rendered
    # This is crucial for consistent coverage between local and CI environments
    console = Console(force_terminal=True, legacy_windows=False)
    return CLI(console=console)


@pytest.fixture(autouse=True)
def mock_get_cli(monkeypatch: pytest.MonkeyPatch, cli: CLI) -> None:
    """Ensure all calls to get_cli() return the test CLI instance."""
    monkeypatch.setattr("app.interfaces.cli.runner.get_cli", lambda: cli)
