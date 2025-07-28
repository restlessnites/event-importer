"""Pytest configuration for the test suite."""

from __future__ import annotations

import pytest
from app.config import get_config
from app.interfaces.cli.core import CLI
from app.services.claude import ClaudeService
from app.services.llm import LLMService
from app.services.openai import OpenAIService
from app.shared.database.connection import (
    get_db_session,
    init_db,
)
from app.shared.database.models import Base
from app.shared.http import HTTPService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Return the test database URL."""
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def db_session(test_database_url: str) -> Session:
    """Create a test database session."""
    engine = create_engine(test_database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


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
    """Return a CLI instance."""
    return CLI()
