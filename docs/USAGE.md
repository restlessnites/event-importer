# Usage Guide

This document provides detailed instructions for using the Event Importer through its three main interfaces: the Command Line Interface (CLI), the HTTP API Server, and the MCP Server for AI assistants.

---

## Command Line Interface

### Import Events

```bash
# Basic usage
event-importer events import "https://ra.co/events/1234567"

# With specific method and timeout
event-importer events import "https://example.com/event" --method web --timeout 120

# Force fresh import (ignore cache)
event-importer events import "https://ra.co/events/1234567" --ignore-cache

# Enable verbose logging
event-importer events import "https://ra.co/events/1234567" --verbose
```

### View Imported Events & Statistics

```bash
# Show database statistics
event-importer stats

# Show detailed statistics breakdown
event-importer stats --detailed

# Show combined statistics
event-importer stats --combined

# List recent events (default 10)
event-importer events list

# List specific number of events
event-importer events list --limit 20

# Filter events by source
event-importer events list --source "ra.co"

# Show details of a specific event by ID
event-importer events details 123
```

### Rebuild Event Data

Rebuild commands allow you to regenerate specific parts of event data using AI and search services. All rebuild operations return a preview only - use the update command to save changes.

```bash
# Rebuild event description (short or long)
event-importer events rebuild description 123 --type short
event-importer events rebuild description 123 --type long --context "Underground techno event"

# Rebuild event genres
event-importer events rebuild genres 123
event-importer events rebuild genres 123 --context "Four Tet, Floating Points"

# Rebuild event image (searches for best image)
event-importer events rebuild image 123
event-importer events rebuild image 123 --context "official poster 2024"
```

### Update Event Fields

```bash
# Update single field
event-importer events update 123 --title "New Event Title"

# Update multiple fields
event-importer events update 123 --title "New Title" --venue "New Venue" --date "2024-12-31"

# Update complex fields
event-importer events update 123 --genres "House,Techno,Electronic" --lineup "DJ Shadow,Cut Chemist"

# Update all supported fields
event-importer events update 123 \
  --title "Updated Title" \
  --venue "Updated Venue" \
  --date "2024-12-31" \
  --end-date "2025-01-01" \
  --short-description "Electronic music night" \
  --long-description "Join us for an unforgettable night..." \
  --genres "House,Techno" \
  --lineup "Main Act,Support Act" \
  --minimum-age "21+" \
  --cost "$30" \
  --ticket-url "https://tickets.com/event" \
  --promoters "Promoter1,Promoter2"
```

### Settings Management

```bash
# List all settings and their current values
event-importer settings list

# Get a specific setting value
event-importer settings get ANTHROPIC_API_KEY

# Set a setting value
event-importer settings set ANTHROPIC_API_KEY sk-ant-...
event-importer settings set update_url https://example.com/update.zip

# Available settings:
# - ANTHROPIC_API_KEY: Claude API key (primary LLM)
# - OPENAI_API_KEY: ChatGPT API key (fallback LLM)
# - ZYTE_API_KEY: Web scraping API key
# - TICKETMASTER_API_KEY: Ticketmaster API key
# - GOOGLE_API_KEY: Google API key for image/genre enhancement
# - GOOGLE_CSE_ID: Google Custom Search Engine ID
# - TICKETFAIRY_API_KEY: TicketFairy API key
# - update_url: URL to download updates from
```

### Integrations Framework

The integration framework allows interactions with external services.

#### TicketFairy

The TicketFairy integration provides commands under the main CLI.

```bash
# Check the status of the ticketfairy integration
event-importer ticketfairy stats

# Submit unsubmitted events to TicketFairy (dry run)
event-importer ticketfairy submit --dry-run

# Submit a specific URL to TicketFairy
event-importer ticketfairy submit --url "https://ra.co/events/1234567"

# Retry failed submissions for TicketFairy
event-importer ticketfairy retry-failed
```

---

## HTTP API Server

Run as a web service for integration with other applications. For full details, see the [HTTP API Guide](API.md).

```bash
# Start the server (default port 8000)
event-importer api
```

### API Endpoints

#### Event Management

- **POST** `/api/v1/events/import` - Import an event
- **GET** `/api/v1/events/import/{id}/progress` - Check import progress
- **GET** `/api/v1/events` - List all events (with pagination)
- **GET** `/api/v1/events/{event_id}` - Get a specific event
- **POST** `/api/v1/events/{event_id}/rebuild/description` - Rebuild event description (long or short)
- **POST** `/api/v1/events/{event_id}/rebuild/genres` - Rebuild event genres
- **POST** `/api/v1/events/{event_id}/rebuild/image` - Search for and select best image
- **PATCH** `/api/v1/events/{event_id}` - Update event fields

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

# Rebuild event description
curl -X POST http://localhost:8000/api/v1/events/123/rebuild/description \
  -H "Content-Type: application/json" \
  -d '{
    "description_type": "short",
    "supplementary_context": "Electronic music festival"
  }'

# Rebuild event genres
curl -X POST http://localhost:8000/api/v1/events/123/rebuild/genres \
  -H "Content-Type: application/json" \
  -d '{
    "supplementary_context": "Four Tet, Floating Points"
  }'

# Rebuild event image
curl -X POST http://localhost:8000/api/v1/events/123/rebuild/image \
  -H "Content-Type: application/json" \
  -d '{
    "supplementary_context": "official poster"
  }'

# Update event fields
curl -X PATCH http://localhost:8000/api/v1/events/123 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Event Title",
    "venue": "New Venue Name",
    "time": {
      "start": "21:00",
      "end": "03:00",
      "timezone": "America/New_York"
    }
  }'

# Get statistics
curl http://localhost:8000/api/v1/statistics/combined

# Check health
curl http://localhost:8000/api/v1/health
```

**Python example**: See `scripts/api_example.py` for a complete example.

---

## MCP Server (for AI Assistants)

Use with Claude Desktop or other MCP-compatible AI assistants. For full details, see the [MCP Assistant Guide](MCP.md).

```bash
# Start MCP server
event-importer mcp
```

### Claude Desktop Configuration

Add the following to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "event-importer": {
      "command": "/full/path/to/uv",
      "args": [
        "--directory",
        "/full/path/to/event-importer",
        "run",
        "event-importer",
        "mcp"
      ],
    }
  }
}
```

Then use the `import_event` tool in Claude conversations.

---

## Statistics & Analytics

The Event Importer provides comprehensive statistics and analytics about your imported events and submission history.

### Via Command Line

```bash
# Show comprehensive database statistics
event-importer stats --detailed
```

This displays:

- **Event Statistics**: Total events, recent activity (today/this week), events with/without submissions
- **Integration Statistics**: Submission success rates, breakdowns by service and status
- **Historical Data**: When data is available from integrations

### Via HTTP API

```bash
# Get combined statistics
curl http://localhost:8000/api/v1/statistics/combined
```

---

## Error Visibility and Service Failures

The Event Importer now provides better visibility into non-fatal service failures that occur during import. When optional services fail (like image enhancement or genre detection), the import can still succeed with the core event data.

### Service Failure Reporting

When you import an event, the response includes a `service_failures` array that lists any non-fatal errors:

```json
{
  "success": true,
  "data": { /* event data */ },
  "method_used": "web",
  "import_time": 11.5,
  "service_failures": [
    {
      "service": "GoogleImageSearch",
      "error": "Request contains an invalid argument",
      "detail": "Check GOOGLE_CSE_ID configuration"
    },
    {
      "service": "GenreEnhancement",
      "error": "OpenAI API key not configured"
    }
  ]
}
```

### Common Service Failures

- **GoogleImageSearch**: Usually indicates invalid or missing GOOGLE_API_KEY or GOOGLE_CSE_ID
- **GenreEnhancement**: Typically means OpenAI API key is not configured
- **ZyteService**: May timeout or fail due to rate limits
- **ImageEnhancement**: Can fail if image URLs are inaccessible or too large

### Viewing Service Failures

#### CLI

```bash
# Service failures are displayed as warnings after import
event-importer events import https://example.com/event
# Output includes:
# ⚠ Some optional services were not available:
# • GoogleImageSearch: Invalid CSE ID
# • GenreEnhancement: OpenAI API key not configured
```

#### API

The HTTP API includes service failures in the response JSON (see example above).

#### MCP

When using with Claude Desktop, service failures are included in the tool response for visibility.
