# Event Importer

A tool that extracts structured event data from websites, images, and APIs. Use it as a **command-line tool**, **HTTP API server**, or **MCP server** for AI assistants.

## What It Does

- **Import from anywhere**: Resident Advisor, Ticketmaster, Dice.fm, any event website, or even images of flyers
- **Flexible AI backend**: Supports both Claude and OpenAI for extraction and enhancement, with automatic fallback.
- **AI-powered enhancement**: Automatically finds genres, improves images, and generates descriptions
- **Extensible Integration Framework**: Easily add new integrations (e.g., to submit events to external calendars or databases) using a simple, modular system.
- **Multiple interfaces**: CLI for developers, HTTP API for web apps, MCP for AI assistants
- **Smart extraction**: Handles APIs, web scraping, and image text extraction
- **Analytics & insights**: Comprehensive statistics about imports, success rates, and trends

## Quick Start

### Installation

1. **Install Homebrew** (if you don't have it):

   ```bash
   # macOS/Linux
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install uv** (if you don't have it):

   ```bash
   # macOS
   brew install uv
   
   # Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows  
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Install GitHub CLI** (if you don't have it and want to use it):

   ```bash
   # macOS
   brew install gh

   # Ubuntu/Debian
   sudo apt install gh

   # Windows
   winget install GitHub.cli
   ```

4. **Clone and setup**:

   ```bash
   # macOS, Windows
   cd Documents
   ```

   NOTE: If you are an experienced developer, clone the repository to your preferred location.

   ```bash
   # Using GitHub CLI
   gh repo clone restlessnites/event-importer
   cd event-importer
   uv sync

   # Using git
   git clone https://github.com/restlessnites/event-importer.git
   cd event-importer
   uv sync
   ```

5. **Configure API keys**:

   ```bash
   cp env.example .env
   # Edit .env with your API keys (see Getting API Keys below)
   ```

### Getting API Keys

You need API keys for the core functionality.

**Required (at least one of):**

- **Anthropic API Key**: Sign up at [console.anthropic.com](https://console.anthropic.com)
- **OpenAI API Key**: Sign up at [platform.openai.com](https://platform.openai.com)

**Required for web scraping:**

- **Zyte API Key**: Sign up at [zyte.com](https://www.zyte.com)

**Optional (for more features):**

- **Ticketmaster**: Free at [developer.ticketmaster.com](https://developer.ticketmaster.com)
- **Google Search**: Setup at [developers.google.com/custom-search](https://developers.google.com/custom-search) (for AI-powered image and genre enhancement)
- **TicketFairy API Key**: For submitting events to TicketFairy.

## Interfaces

This tool provides multiple ways to interact with it, depending on your needs.

- **[Command Line Interface](#command-line-interface)**: Best for developers, testing, and manual imports.
- **[HTTP API Server](docs/API.md)**: Ideal for integrating the importer into a web application or another service.
- **[MCP Server for AI Assistants](docs/MCP.md)**: Perfect for using the importer conversationally within AI assistants like Claude Desktop.

For detailed documentation on the API and MCP interfaces, please see the `docs` folder.

## Command Line Interface

Perfect for testing and local development:

### Import Events

```bash
# Basic usage
uv run event-importer import "https://ra.co/events/1234567"

# Force a specific method
uv run event-importer import "https://example.com/event" --method web

# Adjust timeout
uv run event-importer import "https://example.com/event" --timeout 120
```

### View Imported Events & Statistics

```bash
# Show database statistics and analytics
uv run event-importer stats

# List all events
uv run event-importer list

# List recent events with a limit
uv run event-importer list --limit 10

# Search for specific events
uv run event-importer list --search "artist name"

# Show detailed view
uv run event-importer list --details

# Show specific event by ID
uv run event-importer show 123
```

### Integrations Framework

The integration framework allows interactions with external services.

#### TicketFairy

The `ticketfairy` integration lets you submit events to TicketFairy.

```bash
# Check the status of the ticketfairy integration
uv run event-importer ticketfairy status

# Submit unsubmitted events to TicketFairy (dry run)
uv run event-importer ticketfairy submit --dry-run

# Submit a specific URL to TicketFairy
uv run event-importer ticketfairy submit --url "https://ra.co/events/1234567"

# Retry failed submissions for TicketFairy
uv run event-importer ticketfairy retry-failed
```

## HTTP API Server

Run as a web service for integration with other applications:

```bash
# Start the server
uv run event-importer api --port 8000

# With custom host and auto-reload
uv run event-importer api --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### Event Management

- **POST** `/api/v1/events/import` - Import an event
- **GET** `/api/v1/events/import/{id}/progress` - Check import progress  

#### Statistics

- **GET** `/api/v1/statistics/events` - Get event statistics (counts, recent activity)
- **GET** `/api/v1/statistics/submissions` - Get submission/integration statistics
- **GET** `/api/v1/statistics/combined` - Get all statistics combined
- **GET** `/api/v1/statistics/trends?days=7` - Get event trends over time
- **GET** `/api/v1/statistics/detailed` - Get comprehensive statistics with trends

#### Integrations

- **POST** `/integrations/ticketfairy/submit` - Submit events to TicketFairy
- **GET** `/integrations/ticketfairy/status` - Get TicketFairy submission status
- **POST** `/integrations/ticketfairy/retry-failed` - Retry failed submissions

#### System

- **GET** `/api/v1/health` - Health check
- **GET** `/api/v1/statistics/health` - Statistics service health check

### Example API Usage

```bash
# Import an event
curl -X POST http://localhost:8000/api/v1/events/import \
  -H "Content-Type: application/json" \
  -d '{"url": "https://ra.co/events/1234567"}'

# Get statistics
curl http://localhost:8000/api/v1/statistics/combined
curl http://localhost:8000/api/v1/statistics/trends?days=30

# Check health
curl http://localhost:8000/api/v1/health
```

**Python example**: See `scripts/api_example.py` for a complete example.

## MCP Server (for AI Assistants)

Use with Claude Desktop or other MCP-compatible AI assistants:

```bash
# Start MCP server
uv run event-importer-mcp
```

### Claude Desktop Configuration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "event-importer": {
      "command": "/full/path/to/uv",
      "args": [
        "--directory",
        "/full/path/to/event-importer",
        "run",
        "event-importer-mcp"
      ],
    }
  }
}
```

Then use the `import_event` tool in Claude conversations.

## Statistics & Analytics

The Event Importer provides comprehensive statistics and analytics about your imported events and submission history:

### Via Command Line

```bash
# Show comprehensive database statistics
uv run event-importer stats
```

This displays:

- **Event Statistics**: Total events, recent activity (today/this week), events with/without submissions
- **Integration Statistics**: Submission success rates, breakdowns by service and status
- **Historical Data**: When data is available from integrations

### Via HTTP API

```bash
# Get combined statistics
curl http://localhost:8000/api/v1/statistics/combined

# Get event trends over time
curl http://localhost:8000/api/v1/statistics/trends?days=30

# Get detailed statistics with trends
curl http://localhost:8000/api/v1/statistics/detailed
```

### Statistics Data Structure

```json
{
  "events": {
    "total_events": 1250,
    "events_today": 15,
    "events_this_week": 89,
    "events_with_submissions": 432,
    "unsubmitted_events": 818,
    "last_updated": "2024-01-15T10:30:00"
  },
  "submissions": {
    "total_submitted_events": 432,
    "by_status": {
      "success": 389,
      "failed": 43
    },
    "by_service": {
      "restless_api": 432
    },
    "success_rate": 90.05
  },
  "trends": {
    "daily_counts": [...],
    "total_in_period": 89,
    "average_per_day": 12.7
  }
}
```

## What You Get

The importer returns structured JSON with enhanced data:

```json
{
  "title": "Artist Name at Venue",
  "venue": "The Venue Name",
  "date": "2024-12-31",
  "time": {"start": "22:00", "end": "04:00"},
  "lineup": ["Main Artist", "Support Act"],
  "genres": ["Electronic", "House"],
  "description": "AI-generated event description...",
  "images": {
    "full": "https://high-quality-image.jpg",
    "thumbnail": "https://thumbnail.jpg"
  },
  "location": {
    "city": "Los Angeles",
    "state": "CA",
    "coordinates": {"lat": 34.0522, "lng": -118.2437}
  },
  "cost": "$20",
  "minimum_age": "21+",
  "ticket_url": "https://tickets.com/event",
  "source_url": "https://original-event-page.com"
}
```

## Supported Sources

- **Resident Advisor** (`ra.co`) - Full API access, no key needed
- **Dice.fm** (`dice.fm`) - API access, no key needed
- **Ticketmaster** family (`ticketmaster.com`, `livenation.com`) - Requires free API key
- **Any event website** - Smart web scraping
- **Image URLs** - AI extracts text from flyers/posters

## Testing

Test the system with example scripts:

```bash
# Test basic functionality
uv run python scripts/test_importer.py

# Test with a specific URL
uv run python scripts/test_importer.py "https://ra.co/events/1234567"
uv run python scripts/test_importer.py "https://dice.fm/event/carl-cox-presents-excel-o2zx"

# Test AI enhancements (requires Google API keys)
uv run python scripts/test_genre_enhancer.py
uv run python scripts/test_image_enhancer.py

# Test API integration
uv run python scripts/api_example.py
```

Check the `scripts/` folder for more examples.

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Required for web scraping
ZYTE_API_KEY=...

# Optional - enables more features  
OPENAI_API_KEY=sk-...
TICKETMASTER_API_KEY=...
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...

# Integrations
TICKETFAIRY_API_KEY=...

# Advanced settings
HTTP_TIMEOUT=30                    # Request timeout in seconds
ZYTE_USE_RESIDENTIAL_PROXY=false   # For heavily protected sites
ZYTE_GEOLOCATION=US                # Geolocation for requests
DEBUG=false                        # Enable debug logging
LOG_LEVEL=INFO                     # Logging level
```

### Feature Requirements

| Feature           | Required Keys                       | Description                  |
|-------------------|-------------------------------------|------------------------------|
| Primary LLM       | `ANTHROPIC_API_KEY`                 | Core functionality           |
| Web scraping      | `ZYTE_API_KEY`                      | Core functionality           |
| Fallback LLM      | `OPENAI_API_KEY`                    | Redundancy                   |
| Ticketmaster      | `TICKETMASTER_API_KEY`              | Official API access          |
| Genre enhancement | `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`   | AI-powered genre discovery   |
| Image enhancement | `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`   | AI-powered image search      |
| TicketFairy       | `TICKETFAIRY_API_KEY`               | Submit events to TicketFairy |

## Additional Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - Technical architecture and development guide
- **[HTTP API Guide](docs/API.md)** - How to use the HTTP API for web integration
- **[MCP Assistant Guide](docs/MCP.md)** - How to use the importer with AI assistants
- **[Genre Enhancement](docs/GENRE_ENHANCER.md)** - How AI genre discovery works
- **[Image Enhancement](docs/IMAGE_ENHANCER.md)** - How AI image enhancement works
- **[Integrations](docs/INTEGRATIONS.md)** - How to build and use integrations

## Development

### Entry Points

The application provides multiple entry points:

```bash
# Main router (shows help by default)
uv run event-importer

# Direct interface access
uv run event-importer-cli "https://example.com"
uv run event-importer-api --port 8000  
uv run event-importer-mcp
```

### Project Structure

```plaintext
app/
├── core/               # Business logic
├── interfaces/         # CLI, API, MCP interfaces
├── services/           # External service integrations (LLMs, Zyte, etc.)
├── agents/             # Import agents for different sources
├── integrations/       # Integrations (e.g., TicketFairy)
├── shared/             # Shared utilities
└── data/               # Reference data
```

For detailed architecture information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## AI Enhancement Features

The Event Importer goes beyond basic extraction:

- **Flexible LLM Backend**: Automatically uses a primary LLM provider (e.g., Claude) and falls back to a secondary (e.g., OpenAI) if the primary fails, ensuring reliability.
- **Genre Discovery**: Uses Google Search + AI to find accurate music genres.
- **Image Enhancement**: Finds high-quality event images using AI-powered search.
- **Description Generation**: Creates natural event descriptions when missing.
- **Smart Extraction**: Handles complex event pages with fallback methods.

## Troubleshooting

### Common Issues

1. **Import fails**: Check that required API keys are set in `.env`
2. **Timeout errors**: Increase timeout with `--timeout 120`  
3. **API server won't start**: Make sure the port isn't already in use
4. **MCP connection issues**: Verify the working directory path in MCP client config

### Getting Help

- Check the test scripts in `scripts/` for working examples
- Review the [Architecture documentation](docs/ARCHITECTURE.md) for technical details
- Examine log output for specific error messages

---

Built for the Restless events community. Extract structured data from anywhere, enhance it with AI, and use it however you need.
