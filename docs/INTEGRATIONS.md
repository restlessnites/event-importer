# Integration Framework

The Event Importer features a powerful and extensible integration framework that allows you to send imported and enhanced event data to external services, such as calendar applications, databases, or third-party APIs.

## Overview

The integration system is designed to be modular and auto-discovering. You can add new integrations without modifying any of the core application code. Each integration is a self-contained module within the `app/integrations/` directory.

The framework is built on a few key components that work together to select, transform, and submit event data.

## Core Components

Each integration consists of four main Python classes, which inherit from base classes defined in `app/integrations/base.py`.

### 1. Selectors

- **Purpose**: To select which events should be processed by the integration.
- **Base Class**: `BaseSelector`
- **Method to Implement**: `select_events(self, db: Session, service_name: str) -> List[EventCache]`

Selectors query the database and return a list of `EventCache` objects. You can create multiple selectors for different use cases.

**Example (`UnsubmittedSelector`):**
Selects all events that have never been submitted to a specific service.

```python
class UnsubmittedSelector(BaseSelector):
    def select_events(self, db: Session, service_name: str) -> List[EventCache]:
        return (
            db.query(EventCache)
            .outerjoin(Submission, and_(
                Submission.event_cache_id == EventCache.id,
                Submission.service_name == service_name
            ))
            .filter(Submission.id == None)
            .all()
        )
```

### 2. Transformer

- **Purpose**: To transform the standardized `EventData` dictionary into the specific format required by the destination API.
- **Base Class**: `BaseTransformer`
- **Method to Implement**: `transform(self, event_data: Dict[str, Any]) -> Dict[str, Any]`

This class is responsible for all the data mapping and formatting logic.

**Example (`TicketFairyTransformer`):**
Converts an `EventData` object into the JSON payload expected by the TicketFairy API.

```python
class TicketFairyTransformer(BaseTransformer):
    def transform(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        # ... data mapping logic ...
        return {
            "data": {
                "attributes": {
                    "title": event_data.get("title"),
                    "venue": event_data.get("venue"),
                    # ... other transformed fields
                }
            }
        }
```

### 3. Client

- **Purpose**: To handle the actual HTTP communication with the external service's API.
- **Base Class**: `BaseClient`
- **Method to Implement**: `async submit(self, data: Dict[str, Any]) -> Dict[str, Any]`

The client is responsible for making the API call, handling authentication, and raising appropriate errors.

**Example (`TicketFairyClient`):**

```python
class TicketFairyClient(BaseClient):
    async def submit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
```

### 4. Submitter

- **Purpose**: To orchestrate the entire submission process for an integration.
- **Base Class**: `BaseSubmitter`

The submitter ties all the other components together. It initializes the selectors, transformer, and client. Its core `submit_events` method (provided by the base class) handles the workflow of selecting events, transforming them, and using the client to submit them, while also managing database records (`Submission` model) to track the status of each attempt.

**Example (`TicketFairySubmitter`):**

```python
class TicketFairySubmitter(BaseSubmitter):
    @property
    def service_name(self) -> str:
        return "ticketfairy"

    def _create_client(self) -> BaseClient:
        return TicketFairyClient()

    def _create_transformer(self) -> BaseTransformer:
        return TicketFairyTransformer()

    def _create_selectors(self) -> Dict[str, BaseSelector]:
        return {
            "unsubmitted": UnsubmittedSelector(),
            "failed": FailedSelector(),
        }
```

## Auto-Discovery and Interfaces

The framework can automatically register CLI commands and API endpoints for your integration.

- **CLI Commands**: If you create a `cli.py` file in your integration's directory, it will be automatically discovered. You can use this to add new subcommands to the main `event-importer` CLI. For example, `event-importer ticketfairy submit`.
- **API Routes**: If you create a `routes.py` file with a FastAPI `APIRouter`, its endpoints will be automatically included in the API server. For example, `POST /integrations/ticketfairy/submit`.

## How to Create a New Integration

1. **Create a Directory**: Add a new folder inside `app/integrations/`, for example, `app/integrations/my_service`.

2. **Add `__init__.py`**: This file can be empty, but it's required for the module to be discoverable.

3. **Implement Components**:
    - Create `selectors.py` and define your `Selector` classes.
    - Create `transformer.py` and define your `Transformer` class.
    - Create `client.py` and define your `Client` class.
    - Create `submitter.py` and define your `Submitter` class that wires everything together.

4. **Add Configuration**:
    - Add any required API keys or settings to `.env.example`.
    - Update `app/config.py` to load these new environment variables.

5. **(Optional) Add Interfaces**:
    - Create `cli.py` to add command-line functionality.
    - Create `routes.py` to add API endpoints.

6. **Run It**: Your new integration's commands and routes will be available automatically the next time you run the application.
