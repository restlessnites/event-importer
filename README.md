# Event Importer

A Model Context Protocol (MCP) server that imports structured event data from various sources including direct API access, web scraping, and image extraction.

## Features

- **Multiple Import Methods**:
  - **API Import**: Direct access to Resident Advisor GraphQL and Ticketmaster Discovery APIs
  - **Web Import**: Smart web scraping with HTML and screenshot fallback
  - **Image Import**: Extract event details from flyers and posters using vision AI
  
- **Intelligent Enhancement**:
  - Automatic image search and quality rating for better event images
  - Structured data validation with Pydantic
  - Progress tracking for long-running imports

- **MCP Integration**: Full Model Context Protocol server implementation for use with AI assistants

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/event-importer.git
   cd event-importer
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Configure environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your API keys:

   ```env
   # Required
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ZYTE_API_KEY=your_zyte_api_key
   
   # Optional (enables additional features)
   TICKETMASTER_API_KEY=your_ticketmaster_consumer_key
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_CSE_ID=your_google_custom_search_engine_id
   ```

### Getting API Keys

- **Anthropic**: Sign up at [console.anthropic.com](https://console.anthropic.com)
- **Zyte**: Get web scraping API access at [zyte.com](https://www.zyte.com)
- **Ticketmaster**: Register for free at [developer.ticketmaster.com](https://developer.ticketmaster.com)
- **Google Search**: Set up Custom Search at [developers.google.com/custom-search](https://developers.google.com/custom-search)

## Usage

### As an MCP Server

1. Run the server directly:

   ```bash
   uv run event-importer
   ```

2. Or configure in your MCP client (e.g., Claude Desktop):

   ```json
   {
     "mcpServers": {
       "event-importer": {
         "command": "uv",
         "args": ["run", "event-importer"],
         "cwd": "/path/to/event-importer"
       }
     }
   }
   ```

### Using the MCP Tool

Once connected, use the `import_event` tool:

```json
{
  "tool": "import_event",
  "arguments": {
    "url": "https://ra.co/events/1234567",
    "timeout": 60
  }
}
```

### Testing

Run the test script:

```bash
# Test with example URLs
uv run python scripts/test_import.py

# Test specific URL
uv run python scripts/test_import.py "https://ra.co/events/1234567"
```

## Supported Sources

### 1. Resident Advisor (RA.co)

- **URLs**: `https://ra.co/events/1234567`
- **Method**: Direct GraphQL API
- **No API key required**

### 2. Ticketmaster & Affiliates

- **URLs**: `ticketmaster.com`, `livenation.com`, `ticketweb.com`
- **Method**: Discovery API v2
- **Requires API key** (free tier: 5000 requests/day)

### 3. Direct Image URLs

- **Formats**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- **Method**: Vision AI extraction
- **Best for**: Event flyers and posters

### 4. Any Other Event Page

- **Method**: Intelligent web scraping
- **Process**: HTML extraction → Screenshot fallback → Image enhancement

## Output Schema

The importer returns structured event data:

```python
{
  "title": "Event Name",
  "venue": "Venue Name", 
  "date": "2024-12-31",  # ISO format
  "time": {
    "start": "22:00",
    "end": "04:00"
  },
  "lineup": ["Artist 1", "Artist 2"],
  "promoters": ["Promoter Name"],
  "genres": ["Electronic", "House"],
  "long_description": "Full event description...",
  "short_description": "Brief summary...",
  "location": {
    "address": "123 Main St",
    "city": "Los Angeles",
    "state": "CA",
    "country": "United States",
    "coordinates": {"lat": 34.0522, "lng": -118.2437}
  },
  "images": {
    "full": "https://...",
    "thumbnail": "https://..."
  },
  "image_search": {  # For web imports only
    "original": {"url": "...", "score": 75},
    "selected": {"url": "...", "score": 150}
  },
  "minimum_age": "21+",
  "cost": "$20",
  "ticket_url": "https://...",
  "source_url": "https://...",
  "imported_at": "2024-01-01T00:00:00Z"
}
```

## Architecture

```plaintext
event-importer/
├── app/
│   ├── __init__.py          # Package exports
│   ├── server.py            # MCP server entry point
│   ├── config.py            # Configuration management
│   ├── errors.py            # Error handling
│   ├── http.py              # Shared HTTP client
│   ├── schemas.py           # Pydantic data models
│   ├── url_analyzer.py      # URL routing logic
│   ├── agent.py             # Base agent class
│   ├── engine.py            # Import orchestration
│   ├── progress.py          # Progress tracking
│   ├── router.py            # Request routing
│   ├── services/            # External service integrations
│   │   ├── claude.py        # Claude AI extraction
│   │   ├── image.py         # Image processing
│   │   └── zyte.py          # Web scraping
│   └── agents/              # Import agents
│       ├── ra_agent.py      # Resident Advisor
│       ├── ticketmaster_agent.py
│       ├── web_agent.py     # Generic web
│       └── image_agent.py   # Direct images
├── scripts/                 # Test scripts
├── pyproject.toml          # Project config
└── README.md
```

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
ZYTE_API_KEY=...

# Optional
TICKETMASTER_API_KEY=...  # Enables Ticketmaster imports
GOOGLE_API_KEY=...        # Enables image search
GOOGLE_CSE_ID=...         # Google Custom Search Engine ID

# Advanced
HTTP_TIMEOUT=30                    # Request timeout in seconds
ZYTE_USE_RESIDENTIAL_PROXY=false   # For heavily protected sites
ZYTE_GEOLOCATION=US                # Geolocation for requests
DEBUG=false                        # Enable debug logging
LOG_LEVEL=INFO                     # Logging level
```

### Features by Configuration

| Feature           | Required Keys                      |
| ----------------- | ---------------------------------- |
| Resident Advisor  | None (always available)            |
| Ticketmaster      | `TICKETMASTER_API_KEY`             |
| Image Enhancement | `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` |
| Web Scraping      | `ZYTE_API_KEY`                     |

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test
uv run pytest tests/test_engine.py
```

### Code Quality

```bash
# Format code
uv run black app tests

# Lint
uv run ruff app tests

# Type check
uv run mypy app
```

## Error Handling

The importer handles various failure scenarios:

- **Invalid URLs**: Returns clear error messages
- **Network timeouts**: Configurable timeout with retry logic
- **API rate limits**: Respects rate limits with backoff
- **Extraction failures**: Falls back from HTML → Screenshot → Error

## Acknowledgments

- Built for the Model Context Protocol (MCP) ecosystem
- Powered by Claude AI for intelligent extraction
- Web scraping via Zyte's cloud browser infrastructure
