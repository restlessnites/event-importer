# Event Importer Architecture

This document describes the clean architecture implementation of the Event Importer, which supports multiple interfaces (CLI, MCP, and HTTP API) while maintaining separation of concerns.

## Architecture Overview

The application follows **Hexagonal Architecture** (Ports and Adapters pattern) with clear separation between:

- **Core/Domain Layer**: Business logic and domain models
- **Service Layer**: External integrations and services  
- **Interface Layer**: Different ways to interact with the system
- **Shared Layer**: Common utilities used across interfaces

## Directory Structure

```plaintext
app/
├── __init__.py                 # Package exports
├── main.py                     # Application factory and entry point router
├── config.py                   # Configuration management
├── schemas.py                  # Shared data models
├── errors.py                   # Error handling
├── 
├── core/                       # Core business logic (domain layer)
│   ├── __init__.py
│   ├── importer.py             # Main business logic
│   ├── router.py               # Request routing
│   └── progress.py             # Progress tracking
│
├── services/                   # External service integrations
│   ├── __init__.py
│   ├── claude.py               # Claude AI service
│   ├── genre.py                # Genre enhancement service
│   ├── image.py                # Image processing service
│   └── zyte.py                 # Web scraping service
│
├── interfaces/                 # Interface implementations
│   ├── __init__.py
│   ├── cli/                    # CLI interface
│   │   ├── __init__.py
│   │   ├── core.py             # CLI core functionality
│   │   ├── components.py       # UI components
│   │   ├── formatters.py       # Data formatters
│   │   ├── theme.py            # Visual theme
│   │   ├── utils.py            # CLI utilities
│   │   └── error_capture.py    # Error handling
│   │
│   ├── mcp/                    # MCP server interface
│   │   ├── __init__.py
│   │   └── server.py           # MCP server implementation
│   │
│   └── api/                    # HTTP REST API interface
│       ├── __init__.py
│       ├── server.py           # FastAPI application
│       ├── routes/             # API route definitions  
│       │   ├── __init__.py
│       │   ├── events.py       # Event import endpoints
│       │   └── health.py       # Health check endpoints
│       ├── middleware/         # API middleware
│       │   ├── __init__.py
│       │   ├── cors.py         # CORS configuration
│       │   └── logging.py      # Request logging
│       └── models/             # API-specific request/response models
│           ├── __init__.py
│           ├── requests.py     # Request models
│           └── responses.py    # Response models
│
├── shared/                     # Shared utilities across interfaces
│   ├── __init__.py
│   ├── http.py                 # HTTP utilities
│   ├── url_analyzer.py         # URL analysis
│   └── agent.py                # Agent base class
│
├── agents/                     # Import agents for different sources
│   ├── __init__.py
│   ├── ra_agent.py             # Resident Advisor agent
│   ├── ticketmaster_agent.py   # Ticketmaster agent
│   ├── web_agent.py            # Generic web agent
│   └── image_agent.py          # Image-based agent
│
└── data/                       # Data and static files
    └── (existing content)
```

## Usage

### Multiple Entry Points

The application provides multiple ways to run different interfaces:

```bash
# Main entry point with interface selection
event-importer --help
event-importer cli <url>
event-importer mcp
event-importer api --port 8000

# Direct entry points
event-importer-cli <url>
event-importer-mcp
event-importer-api --port 8000
```

### CLI Interface

```bash
# Import an event via CLI
event-importer cli "https://example.com/event"
event-importer cli "https://example.com/event" --method web --timeout 120

# Using direct entry point
event-importer-cli "https://example.com/event"
```

### HTTP API Interface

```bash
# Start the API server
event-importer api --host 0.0.0.0 --port 8000 --reload

# Using direct entry point
event-importer-api --port 8000
```

API endpoints:

- `POST /api/v1/events/import` - Import an event
- `GET /api/v1/events/import/{request_id}/progress` - Get import progress
- `GET /api/v1/health` - Health check

### MCP Server Interface

```bash
# Start MCP server
event-importer mcp

# Using direct entry point  
event-importer-mcp
```

## Architecture Principles

### Dependency Flow

```
Interfaces → Core → Services
     ↓        ↓        ↓
   Shared ← Shared ← Shared
```

### Interface Isolation

- Each interface has its own directory with interface-specific code
- Interfaces only depend on core business logic, not on each other
- Interface-specific models and utilities are kept separate

### Core Business Logic

- Contains the main domain logic and business rules
- Independent of any specific interface or external service
- Uses dependency injection for external services

### Shared Components

- Common utilities that are used across multiple layers
- HTTP client, URL analysis, base classes
- No business logic, only utility functions

## Development Guidelines

### Adding a New Interface

1. Create a new directory under `app/interfaces/`
2. Implement interface-specific models and handlers
3. Use `app/core/router.Router` for business logic
4. Add entry point to `pyproject.toml`
5. Update `app/main.py` to include the new interface

### Adding New Business Logic

1. Add logic to appropriate module in `app/core/`
2. Update `app/core/router.Router` if needed
3. All interfaces automatically get access to new functionality

### Adding External Services

1. Create service class in `app/services/`
2. Inject service into core business logic
3. Service is available to all interfaces

This architecture ensures that the Event Importer remains maintainable, testable, and scalable while supporting multiple interaction methods.
