# Integration Framework

The Event Importer features a powerful and extensible integration framework that allows you to send imported and enhanced event data to external services, such as calendar applications, databases, or third-party APIs.

## Overview

The integration system is designed to be modular and auto-discovering. You can add new integrations without modifying any of the core application code. Each integration is a self-contained module within the `app/integrations/` directory.

The framework is built on a few key components that work together to select, transform, and submit event data.

## Core Components

Each integration consists of several Python classes, which inherit from base classes defined in `app/integrations/base.py`.

### 1. `Integration` Class

This is the main entry point for an integration. It must inherit from `app.integrations.base.Integration` and implement the `name` property.

**Example (`TicketFairyIntegration`):**

```python
from app.integrations.base import Integration

class TicketFairyIntegration(Integration):
    @property
    def name(self) -> str:
        return "ticketfairy"
```

The system uses this class to discover and load the other components of the integration dynamically.

### 2. Selectors

- **Purpose**: To select which events should be processed by the integration.
- **Base Class**: `BaseSelector`
- **Method to Implement**: `select_events(self, db: Session, service_name: str) -> List[EventCache]`

Selectors query the database and return a list of `EventCache` objects. You can create multiple selectors for different use cases.

**Example (`UnsubmittedSelector`):**
Selects all events that have never been submitted to a specific service.

```python
class UnsubmittedSelector(BaseSelector):
    def select_events(self, db: Session, service_name: str) -> List[EventCache]:
        # ... implementation ...
```

### 3. Transformer

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
```

### 4. Client

- **Purpose**: To handle the actual HTTP communication with the external service's API.
- **Base Class**: `BaseClient`
- **Method to Implement**: `async submit(self, data: Dict[str, Any]) -> Dict[str, Any]`

The client is responsible for making the API call, handling authentication, and raising appropriate errors.

### 5. Submitter

- **Purpose**: To orchestrate the entire submission process for an integration.
- **Base Class**: `BaseSubmitter`

The submitter ties all the other components together. It initializes the selectors, transformer, and client. Its core `submit_events` method (provided by the base class) handles the workflow of selecting events, transforming them, and using the client to submit them, while also managing database records (`Submission` model) to track the status of each attempt.

## Auto-Discovery of Interface Components

The framework can automatically discover and register components for different interfaces (like MCP, CLI, and API) if they are placed in conventional file names within your integration's directory.

- **MCP Tools**: If you create an `mcp_tools.py` file, the MCP server will automatically load the `TOOLS` and `TOOL_HANDLERS` from it.
- **API Routes**: An `routes.py` file containing a FastAPI `APIRouter` will be automatically registered with the API server.
- **CLI Commands**: A `cli.py` file can be used to add custom commands to the main CLI.

This is handled by the `get_mcp_tools()` and `get_routes()` methods on the base `Integration` class, which use dynamic importing to load these modules on demand. This prevents dependency issues during installation while allowing seamless extension of the application's interfaces.

## How to Create a New Integration

1. **Create a Directory**: Add a new folder inside `app/integrations/`, for example, `app/integrations/my_service`.

2. **Implement the `Integration` Class**: Create a `base.py` file and define your main integration class, inheriting from `app.integrations.base.Integration`.

    ```python
    from app.integrations.base import Integration

    class MyServiceIntegration(Integration):
        @property
        def name(self) -> str:
            return "my_service"
    ```

3. **Implement Components**:
    - Create `selectors.py` and define your `Selector` classes.
    - Create `transformer.py` and define your `Transformer` class.
    - Create `client.py` and define your `Client` class.
    - Create `submitter.py` and define your `Submitter` class that wires everything together.

4. **Add Configuration**:
    - Add any required API keys or settings to `.env.example`.
    - Update `app/config.py` to load these new environment variables.

5. **Register the Entry Point**: Open `pyproject.toml` and add your new integration class to the `app.integrations` entry points group.

    ```toml
    [project.entry-points."app.integrations"]
    ticketfairy = "app.integrations.ticketfairy.base:TicketFairyIntegration"
    my_service = "app.integrations.my_service.base:MyServiceIntegration"
    ```

6. **(Optional) Add Interfaces**:
    - Create `mcp_tools.py` to add custom tools to the MCP server.
    - Create `routes.py` to add API endpoints.
    - Create `cli.py` to add command-line functionality.

7. **Run It**: Your new integration's tools, routes, and commands will be available automatically the next time you run the application.
