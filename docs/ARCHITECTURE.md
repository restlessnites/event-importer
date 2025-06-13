# Event Importer Architecture

This document describes the clean architecture implementation of the Event Importer, which supports multiple interfaces (CLI, MCP, and HTTP API) while maintaining separation of concerns.

## Architecture Overview

The application follows **Hexagonal Architecture** (Ports and Adapters pattern) with clear separation between:

- **Core/Domain Layer**: Business logic and domain models (`EventImporter`, `Router`).
- **Service Layer**: External integrations and services (`LLMService`, `ZyteService`, `ImageService`).
- **Interface Layer**: Different ways to interact with the system (CLI, API, MCP).
- **Integration Layer**: A pluggable system for submitting imported events to external services (e.g., TicketFairy).
- **Shared Layer**: Common utilities used across the application.

## Directory Structure

```plaintext
app/
├── __init__.py                 # Package exports
├── main.py                     # Application factory and entry point router
├── config.py                   # Configuration management
├── schemas.py                  # Shared data models (Pydantic)
├── errors.py                   # Custom exceptions and error handling
├──
├── core/                       # Core business logic (domain layer)
│   ├── importer.py             # Main business logic orchestrator
│   └── ...
│
├── services/                   # External service integrations
│   ├── llm.py                  # Fallback LLM service (Claude/OpenAI)
│   ├── claude.py               # Claude AI service
│   ├── openai.py               # OpenAI service
│   ├── genre.py                # Genre enhancement service
│   ├── image.py                # Image processing service
│   └── zyte.py                 # Web scraping service
│
├── agents/                     # Import agents for different sources
│   ├── ra_agent.py             # Resident Advisor agent
│   ├── ticketmaster_agent.py   # Ticketmaster agent
│   └── ...
│
├── integrations/               # Pluggable output integrations
│   ├── __init__.py             # Auto-discovery of integrations
│   ├── base.py                 # Base classes (Submitter, Transformer, etc.)
│   └── ticketfairy/            # Example: TicketFairy integration
│       ├── __init__.py
│       ├── client.py           # API client for TicketFairy
│       ├── transformer.py      # Transforms event data to TicketFairy format
│       ├── selectors.py        # Selects which events to submit
│       ├── submitter.py        # Orchestrates the submission process
│       ├── cli.py              # Adds CLI commands (e.g., `uv run event-importer ticketfairy submit`)
│       └── routes.py           # Adds API routes (e.g., `/integrations/ticketfairy/submit`)
│
├── interfaces/                 # User-facing interfaces
│   ├── cli/                    # Command-line interface
│   ├── mcp/                    # MCP server interface for AI assistants
│   └── api/                    # HTTP REST API interface
│
└── shared/                     # Shared utilities across layers
    ├── http.py                 # HTTP client utility
    ├── agent.py                # Agent base class
    ├── statistics.py           # Statistics and analytics service
    └── database/               # Database connection and models
        ├── connection.py       # Database session management
        ├── models.py           # SQLAlchemy models (EventCache, Submission)
        └── utils.py            # Caching and DB helpers
```

## Core Concepts

### 1. The Import Flow

The import process is orchestrated by `EventImporter` in `app/core/importer.py`.

1. **Agent Selection**: Based on the URL, an `Agent` (e.g., `ResidentAdvisorAgent`, `WebAgent`) is selected.
2. **Data Fetching**: The agent fetches raw data (API response, HTML, image).
3. **AI Extraction**: The data is passed to the `LLMService`, which uses a primary AI provider (Claude) to extract structured `EventData`. If the primary fails, it automatically retries with a fallback provider (OpenAI).
4. **AI Enhancement**: The structured `EventData` is enhanced:
    - `ImageService`: Finds better flyer/poster images.
    - `GenreService`: Finds relevant music genres for the artists.
    - `LLMService`: Generates descriptions if they are missing.
5. **Caching**: The final `EventData` is cached in the database.

### 2. LLM Service with Fallback

The `LLMService` (`app/services/llm.py`) provides a resilient AI backend.

- It wraps both `ClaudeService` and `OpenAIService`.
- For any given operation (e.g., `extract_event_data`), it first tries the primary provider (Claude).
- If the primary provider fails for any reason (API error, timeout), the `LLMService` automatically retries the operation with the fallback provider (OpenAI).
- This ensures high availability for critical AI-powered features.

### 3. Integration Framework

The `app/integrations` directory contains a pluggable framework for sending imported event data to external services. This allows for easy extension without modifying the core import logic.

The key components are:

- **`BaseSubmitter`**: The main orchestrator for an integration (e.g., `TicketFairySubmitter`). It coordinates getting events, transforming them, and submitting them.
- **`BaseSelector`**: Defines which events to select from the database for submission (e.g., `UnsubmittedSelector`, `FailedSelector`).
- **`BaseTransformer`**: Converts the standard `EventData` format into the specific format required by the destination API (e.g., `TicketFairyTransformer`).
- **`BaseClient`**: A simple wrapper around the external service's API (e.g., `TicketFairyClient`).

Integrations are **auto-discovered** at startup. If an integration provides `cli.py` or `routes.py`, its CLI commands and API endpoints are automatically registered with the main application.

### 4. Database Models

The system uses two primary SQLAlchemy models in `app/shared/database/models.py`:

- **`EventCache`**: Stores the structured `EventData` for every successfully imported event. This acts as the central source of truth for all events known to the system. It uses a hash to detect if data from a source URL has changed.
- **`Submission`**: Tracks the status of sending an event from `EventCache` to an external service via the integration framework. It records which service it was sent to, the status (`success`, `failed`), and any error messages. This prevents duplicate submissions and allows for retrying failed attempts.

## Dependency Flow

The dependencies flow inward, with interfaces depending on the core, and the core depending on services. The `integrations` layer is a special case that reads from the database and interacts with external services.

```plaintext
Interfaces (CLI, API, MCP) → Core (Importer) → Services (LLMs, Zyte)
              ↑                    ↑                   ↑
            Shared utilities (DB, HTTP, etc.) are used by all layers
              │
Integrations Framework (reads from DB, uses HTTP)
```

## Development Guidelines

### Adding a New Integration

1. Create a new directory under `app/integrations/`, e.g., `app/integrations/my_service/`.
2. Implement the required classes inheriting from the base classes in `app/integrations/base.py`:
    - A `Client` to communicate with the service's API.
    - A `Transformer` to map `EventData` to the service's format.
    - One or more `Selector`s to query events from the database.
    - A `Submitter` to orchestrate the process.
3. (Optional) Add a `cli.py` to define custom CLI commands or `routes.py` to add API endpoints.
4. The integration will be auto-discovered and available. Add any required API data to `env.example` and `config.py`.

### Adding a New Import Source

1. Create a new `Agent` class in `app/agents/` inheriting from `app.shared.agent.Agent`.
2. Implement the `import_event` method to fetch and process data from the new source.
3. Update the `URLAnalyzer` in `app/shared/url_analyzer.py` to recognize URLs for the new source.
4. Add the new agent to the list in `app/core/importer.py`.
