# Event Importer Installer

This installer provides an automated setup process for the Event Importer on macOS.

## Architecture

The installer follows a clean architecture with clear separation of concerns:

```plaintext
installer/
├── __main__.py              # Entry point for python -m installer
├── constants.py             # Configuration constants (Pydantic models)
├── cli/                     # All UI/display logic
│   ├── app.py              # Main CLI orchestration
│   ├── themes.py           # Terminal themes
│   └── display/            # Display modules
│       ├── directories.py  # Directory setup display
│       ├── download.py     # Download progress display
│       ├── launch.py       # App launching display
│       ├── shell.py        # Shell configuration display
│       └── utils.py        # General utilities
├── components/             # Required installer components
│   └── claude_desktop.py   # Claude Desktop configuration
├── operations/             # High-level orchestration
│   ├── configure.py        # Configuration operations
│   ├── download.py         # Download orchestration
│   └── migrate.py          # Migration orchestration
├── services/               # Business logic (NO UI)
│   ├── directory_service.py    # Directory management
│   ├── download_service.py     # Download functionality
│   ├── migration_service.py    # Migration logic
│   ├── settings_service.py     # Settings management
│   ├── shell_service.py        # PATH configuration
│   ├── update_service.py       # Update functionality
│   └── validation_service.py   # Installation validation
└── utils/                  # Shared utilities
    ├── paths.py           # Path utilities
    └── system.py          # System checks
```

## Design Principles

1. **Separation of Concerns**: Business logic is completely separated from UI
2. **No Mixed Responsibilities**: Services contain NO display logic
3. **Callback-Based Progress**: Services use callbacks for progress reporting
4. **Pydantic Configuration**: Type-safe configuration with validation
5. **Modular Display**: Each display concern has its own module

## Key Components

### CLI Layer (`cli/`)

- Handles all user interaction
- Uses `clicycle` for consistent terminal UI
- Organized into focused display modules
- Main orchestration in `app.py`

### Services Layer (`services/`)

- Pure business logic - no UI imports
- Returns data/status, not formatted strings
- Uses callbacks for progress updates
- Each service has a single responsibility

### Operations Layer (`operations/`)

- Thin orchestration layer
- Bridges services and CLI
- Handles service composition

### Components (`components/`)

- Required installer components (e.g., Claude Desktop)
- Self-contained functionality

## Installation Flow

1. **Initialize**: Clear terminal, configure theme
2. **Setup Directories**: Create installation and data directories
3. **Migration**: Check for and migrate from previous installations
4. **Configure API Keys**: Set up required API keys
5. **Download App**: Download with progress reporting
6. **Claude Desktop**: Configure integration if available
7. **Shell PATH**: Configure terminal access
8. **Validation**: Verify installation integrity
9. **Launch**: Optionally launch the app

## Usage

```bash
# Run the installer
python -m installer

# Or directly
python installer/__main__.py
```

## Key Patterns

### Progress Callbacks

Services use callbacks instead of direct UI:

```python
# Service
async def download(self, destination, progress_callback=None):
    if progress_callback:
        progress_callback(downloaded, total)

# CLI
def create_progress_callback():
    # Returns a callback that updates clicycle progress
```

### Status Returns

Services return tuples for status:

```python
def migrate_from_path(self, path) -> tuple[bool, str]:
    return success, message
```

### No UI in Services

Services NEVER import or use clicycle/display functions.

## Extension Points

To add new functionality:

1. **New Service**: Add to `services/` with pure business logic
2. **New Display**: Add to `cli/display/` for UI concerns
3. **New Operation**: Add to `operations/` if orchestration needed
4. **Update Flow**: Modify `cli/app.py` to include in flow

## Testing

The clean separation makes testing straightforward:

- Services can be tested without UI
- Display modules can be tested with mock data
- Operations can be tested with mock services

## Error Handling

- Services raise exceptions or return error tuples
- CLI layer handles display of errors
- Consistent error reporting through clicycle
