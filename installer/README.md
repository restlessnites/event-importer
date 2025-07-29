# Event Importer Installer

This installer provides an automated setup process for the Event Importer on macOS.

## Architecture

The installer is built with modularity and maintainability in mind:

```plaintext
installer/
├── core.py                 # Main orchestrator
├── utils.py               # Shared utilities
├── validators.py          # Installation validation
└── components/            # Modular components
    ├── environment.py     # Python environment setup
    ├── api_keys.py       # API key configuration
    ├── claude_desktop.py  # Claude Desktop integration
    └── updater.py         # Application update logic
```

## Design Principles

1.  **Modular Components**: Each major functionality is isolated in its own module
2.  **Consistent Error Handling**: All components use the same error handling patterns
3.  **User-Friendly Output**: Color-coded console output with clear progress indicators
4.  **Validation**: Comprehensive post-installation validation
5.  **Rollback Support**: Configuration backups before modifications

## Components

### Core (core.py)

- Orchestrates the entire installation flow
- Manages component lifecycle
- Provides top-level error handling

### Utils (utils.py)

- `Console`: Consistent colored output and user interaction
- `SystemCheck`: Platform and command detection
- `ProcessRunner`: Safe subprocess execution
- `FileUtils`: File operations with backup support
- `Downloader`: Handles file downloads with Google Drive support

### Component Details

#### EnvironmentSetup

- Creates .env from template
- Manages Python dependencies via uv (for development)

#### APIKeyManager

- Interactive API key configuration
- Distinguishes required vs optional keys
- Secure input handling

#### ClaudeDesktopConfig

- Auto-detects Claude Desktop installation
- Configures MCP server integration
- Backs up existing configurations

#### UpdateManager

- Downloads and verifies the update package
- Manages the backup and file replacement process
- Provides clear, user-friendly status updates

### Validators

- Comprehensive post-installation checks
- Detailed error reporting
- Distinguishes errors from warnings

## Usage

The installer is run from the project root via the Makefile for development, or by running the packaged application for end-users.

```bash
# Development
make install

# Packaged App
./EventImporter setup
```

The installer will:

1. Check system requirements (for development)
2. Configure the environment
3. Set up API keys interactively
4. Configure Claude Desktop automatically
5. Validate the installation

## Extension Points

To add new functionality:

1. Create a new component in `components/`
2. Follow the existing component patterns
3. Add to the main flow in `core.py`
4. Update validation in `validators.py`

## Error Handling

- All components return boolean success indicators
- Errors are logged with context
- User-friendly error messages
- Option to continue on non-critical failures
