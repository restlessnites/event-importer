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
config/
├── __init__.py                 # Main configuration orchestrator
├── api.py                      # API key settings
├── http.py                     # HTTP client settings
├── loader.py                   # Configuration loading logic
├── paths.py                    # Path-related settings
├── processing.py               # Data processing settings
├── retry.py                    # Retry settings for HTTP requests
├── runtime.py                  # Runtime behavior settings
└── settings.py                 # Pydantic models for different settings groups

app/
├── __init__.py                 # Package exports and version
├── main.py                     # Application factory and entry point router
├── core/                       # Core business logic (domain layer)
│   ├── importer.py             # Main business logic orchestrator
│   ├── router.py               # Request routing logic
│   ├── progress.py             # Progress tracking for imports
│   ├── schemas.py              # Core data models and schemas
│   ├── errors.py               # Core error handling
│   ├── error_messages.py       # Error message constants
│   └── startup.py              # Application startup checks
│
├── services/                   # External service integrations
│   ├── llm/                    # LLM service layer
│   │   ├── service.py          # Main LLM service with fallback logic
│   │   ├── base.py             # Base LLM provider interface
│   │   ├── prompts.py          # LLM prompts for extraction
│   │   └── providers/          # LLM provider implementations
│   │       ├── claude.py       # Claude AI provider
│   │       └── openai.py       # OpenAI provider
│   ├── genre.py                # Genre enhancement service
│   ├── image.py                # Image processing service
│   ├── security_detector.py    # Security detection service
│   ├── zyte.py                 # Web scraping service
│   └── integration_discovery.py # Dynamic integration discovery
│
├── extraction_agents/          # Import agents for different sources
│   ├── base.py                 # Base extraction agent
│   └── providers/              # Agent implementations
│       ├── ra.py               # Resident Advisor agent
│       ├── ticketmaster.py     # Ticketmaster agent
│       ├── dice.py             # Dice.fm agent
│       ├── web.py              # Generic web scraping agent
│       └── image.py            # Direct image import agent
│
├── integrations/               # Pluggable output integrations
│   ├── __init__.py             # Auto-discovery of integrations
│   ├── base.py                 # Base classes (Submitter, Transformer, etc.)
│   └── ticketfairy/            # Example: TicketFairy integration
│
├── interfaces/                 # User-facing interfaces
│   ├── cli/                    # Command-line interface
│   ├── mcp/                    # MCP server interface for AI assistants
│   └── api/                    # HTTP REST API interface
│
└── shared/                     # Shared utilities across layers
    ├── http.py                 # HTTP client utility
    ├── statistics.py           # Statistics and analytics service
    ├── timezone.py             # Timezone handling utilities
    ├── url_analyzer.py         # URL analysis and agent routing
    ├── service_errors.py       # Service error collection and formatting
    ├── constants/              # Application-wide constants
    ├── database/               # Database layer
    │   ├── connection.py       # Database session management
    │   ├── models.py           # SQLAlchemy models (EventCache, Submission)
    │   └── utils.py            # Caching and DB helpers
    └── data/                   # Static data
        └── genres.py           # Genre mappings and validation
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

The `LLMService` (`app/services/llm/service.py`) provides a resilient AI backend.

- It wraps both `Claude` and `OpenAI`.
- For any given operation (e.g., `extract_event_data`), it first tries the primary provider (Claude).
- If the primary provider fails for any reason (API error, timeout), the `LLMService` automatically retries the operation with the fallback provider (OpenAI).
- This ensures high availability for critical AI-powered features.

### 3. Integration Framework

The `app/integrations` directory contains a pluggable framework for sending imported event data to external services. This allows for easy extension without modifying the core import logic.

- **Auto-Discovery**: Integrations are discovered at startup using `importlib.metadata` to find any packages registered under the `"app.integrations"` entry point group in `pyproject.toml`.
- **Dynamic Loading**: The core application **does not** directly import integration code. Instead, components like MCP tools or API routes are loaded on-demand by the relevant interface (e.g., the MCP server or the API server). This is achieved by calling methods on the integration's main class (e.g., `integration.get_mcp_tools()`), which then dynamically imports the necessary module.
- **Decoupling**: This approach decouples the core application from the integrations, preventing dependency conflicts during installation and ensuring that integrations are self-contained.

The key components are:

- **`Integration`**: The main entry point class for an integration.
- **`BaseSubmitter`**: The main orchestrator for an integration (e.g., `TicketFairySubmitter`). It coordinates getting events, transforming them, and submitting them.
- **`BaseSelector`**: Defines which events to select from the database for submission (e.g., `UnsubmittedSelector`, `FailedSelector`).
- **`BaseTransformer`**: Converts the standard `EventData` format into the specific format required by the destination API (e.g., `TicketFairyTransformer`).
- **`BaseClient`**: A simple wrapper around the external service's API (e.g., `TicketFairyClient`).

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
2. Create a `base.py` file with a main integration class inheriting from `app.integrations.base.Integration`.
3. Implement the required `Selector`, `Transformer`, `Client`, and `Submitter` classes.
4. (Optional) Add interface files like `mcp_tools.py`, `routes.py`, or `cli.py`.
5. Register the main integration class as an entry point in `pyproject.toml` under the `[project.entry-points."app.integrations"]` group.
6. The integration will be auto-discovered and its components loaded on-demand. Add any required API data to `env.example` and `config.py`.

### Adding a New Import Source

1. Create a new agent class in `app/extraction_agents/providers/` inheriting from `app.extraction_agents.base.BaseExtractionAgent`.
2. Implement the `_perform_extraction` method to fetch and process data from the new source.
3. Update the `URLAnalyzer` in `app/shared/url_analyzer.py` to recognize URLs for the new source.
4. Add the new agent to the agent mapping in `app/core/importer.py`.

## Agent Descriptions

- **`ResidentAdvisor`** (`app/extraction_agents/providers/ra.py`): Uses the RA GraphQL API.
- **`Ticketmaster`** (`app/extraction_agents/providers/ticketmaster.py`): Uses the Ticketmaster Discovery API.
- **`Dice`** (`app/extraction_agents/providers/dice.py`): Uses the Dice.fm search API to find event details.
- **`Web`** (`app/extraction_agents/providers/web.py`): The fallback agent. Uses Zyte for web scraping and screenshotting, then uses an LLM to extract data from the HTML or image.
- **`Image`** (`app/extraction_agents/providers/image.py`): For direct image URLs. Downloads the image and uses an LLM to extract data.

The `EventImporter`'s `_determine_agent` method uses the `URLAnalyzer` to decide which agent to use for a given URL.
