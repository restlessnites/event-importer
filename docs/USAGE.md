# Usage Guide

This document provides detailed instructions for using the Event Importer through its three main interfaces: the Command Line Interface (CLI), the HTTP API Server, and the MCP Server for AI assistants.

---

## Command Line Interface

All CLI commands are available through the `event-importer` command.

### Import Events

```bash
# Basic usage
event-importer import-event "https://ra.co/events/1234567"

# With specific method and timeout
event-importer import-event "https://example.com/event" --method web --timeout 120

# Force fresh import (ignore cache)
event-importer import-event "https://ra.co/events/1234567" --ignore-cache

# Enable verbose logging
event-importer import-event "https://ra.co/events/1234567" --verbose
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
event-importer list-events

# List specific number of events
event-importer list-events --limit 20

# Filter events by source
event-importer list-events --source "ra.co"

# Show details of a specific event by ID
event-importer event-details 123
```

### Integrations Framework

The integration framework allows interactions with external services.

#### TicketFairy

The `ticketfairy-submit` command provides a separate CLI for TicketFairy operations.

```bash
# Check the status of the ticketfairy integration
ticketfairy-submit status

# Submit unsubmitted events to TicketFairy (dry run)
ticketfairy-submit submit --dry-run

# Submit a specific URL to TicketFairy
ticketfairy-submit submit --url "https://ra.co/events/1234567"

# Retry failed submissions for TicketFairy
ticketfairy-submit retry-failed
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
