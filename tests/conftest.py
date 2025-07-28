"""Global test configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.shared.database.models import Base


@pytest.fixture(scope="session")
def test_database_url():
    """Use a separate test database."""
    # Use an in-memory SQLite database for tests
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session(test_database_url):
    """Create a test database session."""
    # Create engine and tables
    engine = create_engine(test_database_url)
    Base.metadata.create_all(engine)

    # Create session
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = test_session_local()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def mock_db_session(monkeypatch, db_session):
    """Automatically mock get_db_session for all tests."""
    def mock_get_db_session():
        return db_session

    monkeypatch.setattr("app.shared.database.connection.get_db_session", mock_get_db_session)


@pytest.fixture(autouse=True)
def test_environment(monkeypatch):
    """Set up test environment variables."""
    # Ensure we're in test mode
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    # Mock API keys to prevent accidental API calls
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "test-id")
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")

    # Mock TicketFairy config
    monkeypatch.setenv("TICKETFAIRY_API_URL", "http://test.local")
    monkeypatch.setenv("TICKETFAIRY_API_KEY", "test-key")
