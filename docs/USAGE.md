# Usage Guide

This document provides detailed instructions for using the Event Importer through its three main interfaces: the Command Line Interface (CLI), the HTTP API Server, and the MCP Server for AI assistants.

---

## Command Line Interface

The `Makefile` provides simple shortcuts for all common command-line tasks.

### Import Events

```bash
# Basic usage
make import URL="https://ra.co/events/1234567"

# You can pass any arguments from the command line
make run-cli ARGS="import https://example.com/event --method web --timeout 120"
```

### View Imported Events & Statistics

```bash
# Show database statistics and analytics
make db-stats

# List all events
make run-cli ARGS="list"

# List recent events with a limit
make run-cli ARGS="list --limit 10"

# Search for specific events
make run-cli ARGS="list --search \"artist name\""

# Show detailed view
make run-cli ARGS="list --details"

# Show specific event by ID
make run-cli ARGS="show 123"
```

### Update the Application

```bash
# Check for updates and install the latest version
make update
```

### Integrations Framework

The integration framework allows interactions with external services.

#### TicketFairy

The `ticketfairy` integration lets you submit events to TicketFairy.

```bash
# Check the status of the ticketfairy integration
make run-cli ARGS="ticketfairy status"

# Submit unsubmitted events to TicketFairy (dry run)
make run-cli ARGS="ticketfairy submit --dry-run"

# Submit a specific URL to TicketFairy
make run-cli ARGS="ticketfairy submit --url https://ra.co/events/1234567"

# Retry failed submissions for TicketFairy
make run-cli ARGS="ticketfairy retry-failed"
```

---

## HTTP API Server

Run as a web service for integration with other applications. For full details, see the [HTTP API Guide](API.md).

```bash
# Start the server
make run-api

# To run on a different port, you can use the cli command
make run-cli ARGS="api --port 8001"
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
make run-mcp
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
make db-stats
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
