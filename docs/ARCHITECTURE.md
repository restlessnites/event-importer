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
│   │   ├── events.py           # Event management commands  
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
│       │   ├── statistics.py   # Statistics and analytics endpoints
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
│   ├── agent.py                # Agent base class
│   ├── statistics.py           # Statistics and analytics service
│   └── database/               # Database connection and models
│       ├── __init__.py
│       ├── connection.py       # Database connection management
│       └── models.py           # SQLAlchemy models
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
uv run event-importer --help
uv run event-importer cli <url>
uv run event-importer mcp
uv run event-importer api --port 8000

# Direct entry points
uv run event-importer-cli <url>
uv run event-importer-mcp
uv run event-importer-api --port 8000
```

### CLI Interface

```bash
# Import an event via CLI
uv run event-importer cli "https://example.com/event"
uv run event-importer cli "https://example.com/event" --method web --timeout 120

# Using direct entry point
uv run event-importer-cli "https://example.com/event"
```

### HTTP API Interface

```bash
# Start the API server
uv run event-importer api --host 0.0.0.0 --port 8000 --reload

# Using direct entry point
uv run event-importer-api --port 8000
```

API endpoints:

**Event Management:**

- `POST /api/v1/events/import` - Import an event
- `GET /api/v1/events/import/{request_id}/progress` - Get import progress

**Statistics & Analytics:**

- `GET /api/v1/statistics/events` - Get event statistics
- `GET /api/v1/statistics/submissions` - Get submission statistics
- `GET /api/v1/statistics/combined` - Get combined statistics
- `GET /api/v1/statistics/trends?days=N` - Get event trends over time
- `GET /api/v1/statistics/detailed` - Get comprehensive statistics with trends

**System:**

- `GET /api/v1/health` - Health check
- `GET /api/v1/statistics/health` - Statistics service health check

### MCP Server Interface

```bash
# Start MCP server
uv run event-importer mcp

# Using direct entry point  
uv run event-importer-mcp
```

## Architecture Principles

### Dependency Flow

```plaintext
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

## Statistics & Analytics System

### Overview

The Event Importer includes a comprehensive statistics and analytics system that provides insights into:

- **Event Statistics**: Import activity, event counts, recent activity
- **Submission Statistics**: Integration success rates, service breakdowns
- **Historical Trends**: Daily import patterns and activity over time

### Architecture Components

#### StatisticsService (`app/shared/statistics.py`)

Core service providing various statistical calculations:

```python  
class StatisticsService:
    def get_event_statistics() -> Dict[str, Any]
    def get_submission_statistics() -> Dict[str, Any] 
    def get_combined_statistics() -> Dict[str, Any]
    def get_event_trends(days: int) -> Dict[str, Any]
    def get_detailed_statistics() -> Dict[str, Any]
```

**Event Statistics:**

- Total event count
- Recent activity (today, this week)
- Events with/without submissions
- Timestamp tracking

**Submission Statistics:**

- Success rates by service and status
- Integration performance metrics
- Service-specific breakdowns

**Trend Analysis:**

- Daily activity patterns
- Historical import volume
- Configurable time periods (1-365 days)

#### CLI Interface (`app/interfaces/cli/events.py`)

```bash
# Show comprehensive database statistics
uv run event-importer stats
```

Displays formatted statistics tables with:

- Event counts and recent activity
- Integration success rates (when available)
- Service breakdowns and performance metrics

#### HTTP API Interface (`app/interfaces/api/routes/statistics.py`)

RESTful endpoints for programmatic access:

- `GET /api/v1/statistics/events` - Core event statistics
- `GET /api/v1/statistics/submissions` - Integration performance
- `GET /api/v1/statistics/combined` - All statistics together
- `GET /api/v1/statistics/trends?days=N` - Historical trends
- `GET /api/v1/statistics/detailed` - Comprehensive analytics
- `GET /api/v1/statistics/health` - Service health check

#### Database Integration

Statistics are calculated from:

- **EventCache table**: Stores imported event data with timestamps
- **Submission table**: Tracks integration attempts and results

The service uses SQLAlchemy queries with aggregation functions for efficient statistical calculations.

### Usage Patterns

#### Development & Debugging

```bash
uv run event-importer stats  # Quick overview
```

#### Monitoring & Operations

```bash
curl http://localhost:8000/api/v1/statistics/detailed
```

#### Integration Monitoring

```bash
curl http://localhost:8000/api/v1/statistics/submissions
```

#### Trend Analysis

```bash
curl http://localhost:8000/api/v1/statistics/trends?days=30
```

This architecture ensures that the Event Importer remains maintainable, testable, and scalable while supporting multiple interaction methods.
