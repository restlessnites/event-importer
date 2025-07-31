# Event Importer HTTP API

Welcome to the Event Importer API! This document provides a detailed guide on how to use the HTTP API to import event data and interact with integrations.

## Getting Started

### Running the API Server

To use the API, you first need to run the server. Make sure you have completed the installation steps in the main `README.md`.

```bash
# Start the server on localhost, port 8000
event-importer api

# Note: The current CLI doesn't support custom port/host options.
# The server will run on 127.0.0.1:8000 by default.
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
  - `ignore_cache` (optional): If `true`, bypasses the cache and forces a fresh import. Defaults to `false`.

- **Success Response (200 OK)**:

  ```json
  {
    "success": true,
    "data": { /* EventData object, see below */ },
    "method_used": "web",
    "import_time": 5.43,
    "service_failures": [
      {
        "service": "GoogleImageSearch",
        "error": "Invalid CSE ID",
        "detail": "Check GOOGLE_CSE_ID configuration"
      }
    ]
  }
  ```

  **Note**: The `service_failures` array lists any non-fatal errors from optional services. The import is still considered successful if the core event data was extracted.

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

### Event Updates and Rebuilding

#### Rebuild Event Description

- **Endpoint**: `POST /api/v1/events/{event_id}/rebuild/description`
- **Description**: Regenerate the event description using AI. Does not save automatically - returns preview only.
- **Request Body**:

  ```json
  {
    "description_type": "string (required: 'short' or 'long')",
    "supplementary_context": "string (optional)"
  }
  ```

  **Parameters**:
  - `description_type`: Which description to regenerate - either "short" (100 chars) or "long" (detailed).
  - `supplementary_context`: Additional context to help the AI generate a better description.

- **Success Response (200 OK)**:

  ```json
  {
    "success": true,
    "event": { /* EventData object with regenerated description */ }
  }
  ```

- **Example**:

  ```bash
  curl -X POST http://localhost:8000/api/v1/events/123/rebuild/description \
    -H "Content-Type: application/json" \
    -d '{
      "description_type": "short",
      "supplementary_context": "Underground techno event"
    }'
  ```

#### Rebuild Event Genres

- **Endpoint**: `POST /api/v1/events/{event_id}/rebuild/genres`
- **Description**: Re-analyze and regenerate event genres using AI and search. Does not save automatically - returns preview only.
- **Request Body**:

  ```json
  {
    "supplementary_context": "string (optional, required if event has no lineup)"
  }
  ```

  **Parameters**:
  - `supplementary_context`: Additional context to help identify genres. Required if the event has no lineup (e.g., provide artist names).

- **Success Response (200 OK)**:

  ```json
  {
    "success": true,
    "genres": ["Electronic", "House", "Techno"],
    "service_failures": [
      {
        "service": "GoogleSearch",
        "error": "API key not configured"
      }
    ]
  }
  ```

- **Example**:

  ```bash
  curl -X POST http://localhost:8000/api/v1/events/123/rebuild/genres \
    -H "Content-Type: application/json" \
    -d '{
      "supplementary_context": "Four Tet, Floating Points"
    }'
  ```

#### Rebuild Event Image

- **Endpoint**: `POST /api/v1/events/{event_id}/rebuild/image`
- **Description**: Search for and select the best image for the event. Does not save automatically - returns preview only.
- **Request Body**:

  ```json
  {
    "supplementary_context": "string (optional)"
  }
  ```

  **Parameters**:
  - `supplementary_context`: Additional context to help find better images (e.g., "festival poster 2024").

- **Success Response (200 OK)**:

  ```json
  {
    "success": true,
    "image_candidates": [
      {
        "url": "https://example.com/image1.jpg",
        "score": 0.9,
        "source": "Event Website",
        "dimensions": "1200x630",
        "reason": "High quality official event poster"
      }
    ],
    "best_image": {
      "url": "https://example.com/image1.jpg",
      "score": 0.9,
      "source": "Event Website",
      "dimensions": "1200x630",
      "reason": "High quality official event poster"
    },
    "service_failures": []
  }
  ```

- **Example**:

  ```bash
  curl -X POST http://localhost:8000/api/v1/events/123/rebuild/image \
    -H "Content-Type: application/json" \
    -d '{
      "supplementary_context": "official event poster"
    }'
  ```

#### Update Event Fields

- **Endpoint**: `PATCH /api/v1/events/{event_id}`
- **Description**: Update specific fields of a cached event.
- **Request Body**:

  ```json
  {
    "title": "string (optional)",
    "venue": "string (optional)",
    "date": "string (optional, YYYY-MM-DD)",
    "end_date": "string (optional, YYYY-MM-DD)",
    "time": {
      "start": "string (HH:MM)",
      "end": "string (HH:MM)",
      "timezone": "string (IANA timezone)"
    },
    "lineup": ["array of strings (optional)"],
    "genres": ["array of strings (optional)"],
    "short_description": "string (optional, max 200 chars)",
    "long_description": "string (optional)",
    "cost": "string (optional)",
    "minimum_age": "string (optional)",
    "ticket_url": "string (optional)",
    "images": {
      "full": "string (optional)",
      "thumbnail": "string (optional)"
    },
    "location": {
      "city": "string (optional)",
      "state": "string (optional)",
      "country": "string (optional)",
      "coordinates": {
        "lat": "number (optional)",
        "lng": "number (optional)"
      }
    }
  }
  ```

  **Important Notes**:
  - Only include fields you want to update
  - `date` is the start date, `end_date` is for multi-day events
  - Timezone must be a valid IANA timezone identifier (e.g., 'America/Los_Angeles', 'Europe/London')
  - Updates are saved immediately to the database

- **Success Response (200 OK)**:

  ```json
  {
    "success": true,
    "event": { /* Updated EventData object */ }
  }
  ```

- **Example**:

  ```bash
  # Update multiple fields
  curl -X PATCH http://localhost:8000/api/v1/events/123 \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Updated Event Title",
      "venue": "New Venue",
      "time": {
        "start": "21:00",
        "end": "03:00",
        "timezone": "America/New_York"
      },
      "genres": ["House", "Techno"]
    }'
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
  "end_date": "2025-01-01",
  "time": {
    "start": "22:00",
    "end": "04:00",
    "timezone": "America/Los_Angeles"
  },
  "lineup": ["Main Artist", "Support Act"],
  "genres": ["Electronic", "House"],
  "short_description": "Electronic music night featuring...",
  "long_description": "Join us for an unforgettable night of electronic music...",
  "images": {
    "full": "https://high-quality-image.jpg",
    "thumbnail": "https://thumbnail.jpg"
  },
  "location": {
    "city": "Los Angeles",
    "state": "CA",
    "country": "USA",
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
