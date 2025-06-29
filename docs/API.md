# Event Importer HTTP API

Welcome to the Event Importer API! This document provides a detailed guide on how to use the HTTP API to import event data and interact with integrations.

## Getting Started

### Running the API Server

To use the API, you first need to run the server. Make sure you have completed the installation steps in the main `README.md`.

```bash
# Start the server on localhost, port 8000
uv run event-importer api --port 8000

# For development, run with auto-reload
uv run event-importer api --port 8000 --reload
```

The API will be available at `http://localhost:8000`. All endpoints are prefixed with `/api/v1`.

### Authentication

The API itself does not require authentication tokens in headers. However, it relies on API keys for backend services (like Anthropic, Zyte, Google) which must be configured in your `.env` file. Integrations may also require their own API keys. See the main `README.md` for details on setting up these keys.

## Core API Endpoints

These endpoints are part of the core application.

### Event Management

#### Import an Event

This is the primary endpoint for importing an event. The server processes the request and returns the result upon completion.

- **Endpoint**: `POST /api/v1/events/import`
- **Description**: Submits a URL for event data extraction.
- **Request Body**:

  ```json
  {
    "url": "string",
    "force_method": "string (optional: 'api', 'web', 'image')",
    "include_raw_data": "boolean (optional, default: false)",
    "timeout": "integer (optional, default: 60)"
  }
  ```

  **Parameters**:
  - `url` (required): The full URL of the event page or image.
  - `force_method` (optional): Force a specific import method.
    - `api`: Use a direct API if available (e.g., Resident Advisor, Ticketmaster).
    - `web`: Use web scraping (HTML or screenshot).
    - `image`: Treat the URL as a direct link to an image.
  - `include_raw_data` (optional): If `true`, the response will include the raw, unprocessed data from the source. Defaults to `false`.
  - `timeout` (optional): Maximum time in seconds to wait for the import to complete. Defaults to 60.

- **Success Response (200 OK)**:

  ```json
  {
    "success": true,
    "data": { /* EventData object, see below */ },
    "method_used": "web",
    "import_time": 5.43
  }
  ```

- **Error Response (200 OK with `success: false`)**:

  ```json
  {
    "success": false,
    "error": "Import timed out after 60s",
    "method_used": "web"
  }
  ```

- **Example**:

  ```bash
  curl -X POST http://localhost:8000/api/v1/events/import \
    -H "Content-Type: application/json" \
    -d '{"url": "https://ra.co/events/1234567"}'
  ```

#### Check Import Progress

Since importing is asynchronous, you can poll this endpoint to get progress updates.

- **Endpoint**: `GET /api/v1/events/import/{request_id}/progress`
- **Description**: Get the progress of an import request.
- **Note**: While the server currently processes requests synchronously and returns the full result in the `POST /import` call, this endpoint is available for clients that may operate in a non-blocking fashion in the future.

- **URL Parameters**:
  - `request_id`: The `request_id` associated with the import.

- **Response**:

  ```json
  {
    "request_id": "...",
    "updates": [
      {
        "request_id": "...",
        "status": "running",
        "message": "Starting import",
        "progress": 0.0,
        "timestamp": "...",
        "data": null,
        "error": null
      },
      {
        "request_id": "...",
        "status": "success",
        "message": "Successfully imported event",
        "progress": 1.0,
        "timestamp": "...",
        "data": { /* EventData object */ },
        "error": null
      }
    ]
  }
  ```

### Statistics

These endpoints provide analytics about the events stored in the local database.

- **GET `/api/v1/statistics/events`**: Get basic event statistics.
- **GET `/api/v1/statistics/submissions`**: Get statistics about submissions to external services.
- **GET `/api/v1/statistics/combined`**: Get all statistics combined.
- **GET `/api/v1/statistics/trends?days=7`**: Get event import trends over a period of time.
- **GET `/api/v1/statistics/detailed`**: Get comprehensive statistics with trends.

- **Example**:

  ```bash
  curl http://localhost:8000/api/v1/statistics/combined
  ```

### System

- **GET `/api/v1/health`**: Health check endpoint.
- **GET `/api/v1/statistics/health`**: Statistics service health check.

- **Example**:

  ```bash
  curl http://localhost:8000/api/v1/health
  ```

## Integration API Endpoints

Integrations can automatically add their own API endpoints. These are typically prefixed with `/integrations/`. The following endpoints are available for the `ticketfairy` integration.

### TicketFairy Integration

#### Submit Events to TicketFairy

- **Endpoint**: `POST /integrations/ticketfairy/submit`
- **Description**: Submits events from the database to TicketFairy based on a selector.
- **Request Body**:

  ```json
  {
    "selector": "string (default: 'unsubmitted')",
    "url": "string (optional)",
    "dry_run": "boolean (optional, default: false)"
  }
  ```

  **Parameters**:
  - `selector`: Which events to submit. Can be `unsubmitted`, `failed`, `pending`, or `all`.
  - `url`: If provided, submits only the event matching this source URL.
  - `dry_run`: If `true`, the submission process will run without actually sending data to the TicketFairy API. Useful for testing transformations.

- **Example**:

  ```bash
  # Perform a dry run of submitting unsubmitted events
  curl -X POST http://localhost:8000/integrations/ticketfairy/submit \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true}'
  ```

#### Get TicketFairy Submission Status

- **Endpoint**: `GET /integrations/ticketfairy/status`
- **Description**: Retrieves statistics about submissions to TicketFairy.
- **Example**:

  ```bash
  curl http://localhost:8000/integrations/ticketfairy/status
  ```

#### Retry Failed Submissions

- **Endpoint**: `POST /integrations/ticketfairy/retry-failed`
- **Description**: Attempts to re-submit all events that previously failed to submit to TicketFairy.
- **Request Body**:

  ```json
  {
    "dry_run": "boolean (optional, default: false)"
  }
  ```

- **Example**:

  ```bash
  curl -X POST http://localhost:8000/integrations/ticketfairy/retry-failed \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true}'
  ```

## Data Structures

### EventData Object

This is the core object representing structured event data.

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

## Further Examples

For a complete, runnable Python example of how to interact with the API, see the `scripts/api_example.py` file in this project.
