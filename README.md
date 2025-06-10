# Event Importer

A tool that extracts structured event data from websites, images, and APIs. Use it as a **command-line tool**, **HTTP API server**, or **MCP server** for AI assistants.

## What It Does

- **Import from anywhere**: Resident Advisor, Ticketmaster, any event website, or even images of flyers
- **AI-powered enhancement**: Automatically finds genres, improves images, and generates descriptions
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
   cp .env.example .env
   # Edit .env with your API keys (see Getting API Keys below)
   ```

### Getting API Keys

You need at least these two keys to get started:

- **Anthropic API Key** (required): Sign up at [console.anthropic.com](https://console.anthropic.com)
- **Zyte API Key** (required): Sign up at [zyte.com](https://www.zyte.com)

Optional keys for more features:

- **Ticketmaster**: Free at [developer.ticketmaster.com](https://developer.ticketmaster.com)
- **Google Search**: Setup at [developers.google.com/custom-search](https://developers.google.com/custom-search)

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

# List recent events with limit
uv run event-importer list --limit 10

# Search for specific events
uv run event-importer list --search "artist name"

# Show detailed view
uv run event-importer list --details

# Show specific event by ID
uv run event-importer show 123
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
      "command": "uv",
      "args": [
        "--directory",
        "/full/path/to/event-importer",
        "run",
        "event-importer-mcp"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "KEY",
        "ZYTE_API_KEY": "KEY",
        "TICKETMASTER_API_KEY": "KEY",
        "GOOGLE_API_KEY": "KEY",
        "GOOGLE_CSE_ID": "ID"
      }
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

# Test AI enhancements (requires Google API keys)
uv run python scripts/test_genre_enhancer.py
uv run python scripts/test_image_enhancer.py

# Test API integration
uv run python scripts/api_example.py
```

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
ZYTE_API_KEY=...

# Optional - enables more features  
TICKETMASTER_API_KEY=...
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...

# Advanced settings
HTTP_TIMEOUT=30                    # Request timeout in seconds
ZYTE_USE_RESIDENTIAL_PROXY=false   # For heavily protected sites
ZYTE_GEOLOCATION=US                # Geolocation for requests
DEBUG=false                        # Enable debug logging
LOG_LEVEL=INFO                     # Logging level
```

### Feature Requirements

| Feature           | Required Keys                       | Description                |
|-------------------|-------------------------------------|----------------------------|
| Basic imports     | `ANTHROPIC_API_KEY`, `ZYTE_API_KEY` | Core functionality         |
| Ticketmaster      | `TICKETMASTER_API_KEY`              | Official API access        |
| Genre enhancement | `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`   | AI-powered genre discovery |
| Image enhancement | `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`   | AI-powered image search    |

## Additional Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - Technical architecture and development guide
- **[Genre Enhancement](docs/GENRE_ENHANCER.md)** - How AI genre discovery works
- **[Image Enhancement](docs/IMAGE_ENHANCER.md)** - How AI image enhancement works

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
├── core/                # Business logic
├── interfaces/          # CLI, API, MCP interfaces  
├── services/           # External service integrations
├── agents/             # Import agents for different sources
├── shared/             # Shared utilities
└── data/               # Reference data
```

For detailed architecture information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## AI Enhancement Features

The Event Importer goes beyond basic extraction:

- **Genre Discovery**: Uses Google Search + Claude AI to find accurate music genres
- **Image Enhancement**: Finds high-quality event images using AI-powered search  
- **Description Generation**: Creates natural event descriptions when missing
- **Smart Extraction**: Handles complex event pages with fallback methods

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
