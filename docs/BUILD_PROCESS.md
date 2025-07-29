# Build and Distribution Process

This document outlines the process for building the Event Importer application into a distributable macOS package using PyInstaller. It also explains the mechanism for how the application discovers and loads integrations.

## PyInstaller Build Process

The application is packaged into a standalone macOS application bundle (`.app`) using PyInstaller. This allows non-technical users to install and run the application without needing to set up a Python environment.

### Prerequisites

- A working Python environment (managed by `uv`).
- All development dependencies installed (`make dev-setup`).

### Building the Application

The build process is handled by the `Makefile` and can be initiated with a single command:

```bash
make package
```

This command performs the following steps:

1.  **`clean`**: Removes any old build artifacts from previous runs to ensure a clean build.
2.  **`scripts/sync_version.py`**: Synchronizes the version number from `pyproject.toml` into a `.version` file in the project root. This allows the packaged application to know its own version for update checks.
3.  **`pyinstaller`**: Runs PyInstaller using the `event-importer.spec` file as its configuration. This file contains all the specific instructions for PyInstaller, including:
    - The main entry point (`app/main.py`).
    - The application name.
    - Data files to be included (like `.env.example`).
    - Hidden imports that PyInstaller might not detect automatically.

The final output is a `Event Importer.app` bundle located in the `dist/` directory.

## Integration Discovery (`entry_points`)

The application is designed to be extensible, allowing new integrations (like TicketFairy, Dice, etc.) to be added without modifying the core application code. This is achieved using Python's `entry_points` mechanism, which is defined in `pyproject.toml`.

### How It Works

1.  **Definition**: In `pyproject.toml`, under the `[project.entry-points."event_importer.integrations"]` section, each integration is defined with a unique name and a path to its module.

    ```toml
    [project.entry-points."event_importer.integrations"]
    dice = "app.agents.dice_agent:DiceAgent"
    ra = "app.agents.ra_agent:ResidentAdvisorAgent"
    ticketmaster = "app.agents.ticketmaster_agent:TicketmasterAgent"
    web = "app.agents.web_agent:WebAgent"
    image = "app.agents.image_agent:ImageAgent"
    ticketfairy = "app.integrations.ticketfairy.submitter:TicketFairySubmitter"
    ```

2.  **Discovery**: At startup, the application uses the `importlib.metadata` module to find all packages installed in the environment that have registered an entry point under the `event_importer.integrations` group.

3.  **Loading**: The application then iterates through these entry points and loads the specified modules (e.g., `app.agents.dice_agent:DiceAgent`). This allows the core application to be aware of all available integrations without having to import them directly.

### Tool Discovery (MCP and CLI)

A similar mechanism is used to discover tools for the MCP (Claude) and CLI interfaces.

-   **MCP Tools**: For an integration to expose a tool to Claude, it must contain an `mcp_tools.py` file that defines a `TOOLS` list. The MCP server discovers and loads these `TOOLS` lists from all available integrations at startup.
-   **CLI Commands**: For an integration to expose a command to the main CLI, it must contain a `cli.py` file with a `main` function. The main CLI router discovers and loads these `main` functions as sub-commands at startup.