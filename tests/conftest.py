"""Pytest configuration for the test suite."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.genre import GenreService
from app.services.image import ImageService
from app.services.llm.providers.claude import Claude
from app.services.llm.providers.openai import OpenAI
from app.services.llm.service import LLMService
from app.shared.database.connection import (
    get_db_session,
    init_db,
)
from app.shared.database.models import Base
from app.shared.http import HTTPService
from config import config

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


@pytest.fixture(scope="function")
def http_service() -> HTTPService:
    """Return an HTTPService instance."""
    return HTTPService(config)


@pytest.fixture(scope="function")
def claude_service() -> Claude:
    """Return a Claude instance."""
    return Claude(config)


@pytest.fixture(scope="function")
def openai_service() -> OpenAI:
    """Return an OpenAI instance."""
    return OpenAI(config)


@pytest.fixture(scope="function")
def llm_service() -> LLMService:
    """Return an LLMService instance."""
    return LLMService(config)


@pytest.fixture(scope="function")
def genre_service(http_service: HTTPService, llm_service: LLMService) -> GenreService:
    """Return a GenreService instance."""
    return GenreService(config, http_service, llm_service)


@pytest.fixture(scope="function")
def image_service(http_service: HTTPService) -> ImageService:
    """Return an ImageService instance."""
    return ImageService(config, http_service)


@pytest.fixture
def run_startup_checks() -> None:
    """Ensure startup checks are run."""
    init_db()


@pytest.fixture
def mock_db_session(monkeypatch) -> None:
    """Mock the database session for tests."""
    monkeypatch.setattr("app.shared.database.connection.SessionLocal", get_db_session)
