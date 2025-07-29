# Development Guide

This document provides a technical overview for developers working on the Event Importer.

---

## Getting Started

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/restlessnites/event-importer.git
    cd event-importer
    ```

2. **Set Up the Environment**:

    ```bash
    make dev-setup
    ```

    This command will install all dependencies using `uv` and set up pre-commit hooks.

3. **Configure API Keys**:

    ```bash
    cp env.example .env
    # Now edit .env with your favorite editor
    ```

---

## Testing

The project uses `pytest` for testing.

```bash
# Run all tests with coverage
make test

# For a quicker run without coverage, you can use:
make quick

# Generate an HTML coverage report
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## Configuration

The application uses a hierarchical configuration system that is designed to work seamlessly for both packaged app users and developers running from source.

### Configuration Hierarchy

Settings are loaded from the following sources, in order of precedence (where 1 overrides 2, and 2 overrides 3):

1. **`.env` file (for Developers)**: A `.env` file located in the project root. This is the primary way for developers to configure the application and override any global settings for local testing.
2. **SQLite Storage (for Users)**: Settings are stored in an SQLite database located in the user's application data directory. This is the primary configuration storage for the packaged application. Falls back to `config.json` if SQLite storage fails.
3. **Default Values**: Default values are hardcoded in the `app.config.Config` class.

### File Locations

The application stores its persistent data in the standard user data directory for the operating system.

- **macOS**: `~/Library/Application Support/EventImporter/`
- **Linux**: `~/.local/share/EventImporter/`

Within this directory, you will find:

- `events.db`: The SQLite database containing all imported event data and application settings.
- `config.json`: Legacy configuration file (automatically migrated to SQLite storage).

### Security

Settings are stored in the SQLite database with appropriate file permissions to protect your API keys.

### Developer Workflow

To get started, copy the `env.example` file to `.env`:

```bash
cp env.example .env
```

Now, you can edit the `.env` file with your API keys. Any values you set in this file will override the settings in the global SQLite storage, allowing you to easily switch between different configurations for development and testing without affecting your main setup.

---

## Packaging for Distribution

The application is packaged into a standalone macOS application using PyInstaller. For detailed information on the build process and how the application discovers integrations, see the [Build and Distribution Guide](BUILD_PROCESS.md).

To create the package, run the following command:

```bash
make package
```

This will create an `Event Importer.app` bundle in the `dist/` directory.

---

## Project Structure

```plaintext
app/
├── core/               # Business logic
├── interfaces/         # CLI, API, MCP interfaces
├── services/           # External service integrations (LLMs, Zyte, etc.)
├── agents/             # Import agents for different sources
├── integrations/       # Integrations (e.g., TicketFairy)
├── shared/             # Shared utilities
└── data/               # Reference data

config/                 # Shared configuration system
├── settings.py         # Pydantic settings definitions
└── storage.py          # SQLite settings storage

installer/              # Standalone installer
├── components/         # Installer components
├── main.py            # Installer entry point
├── downloader.py      # App download functionality
└── paths.py           # Path utilities
```

For detailed architecture information, see [docs/ARCHITECTURE.md](ARCHITECTURE.md).
