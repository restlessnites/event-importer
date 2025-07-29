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
    ├── dependencies.py    # System dependency management
    ├── environment.py     # Python environment setup
    ├── api_keys.py       # API key configuration
    ├── claude_desktop.py  # Claude Desktop integration
    ├── updater_config.py  # Update configuration
    └── updater.py         # Application update logic
```

## Design Principles

1. **Modular Components**: Each major functionality is isolated in its own module
2. **Consistent Error Handling**: All components use the same error handling patterns
3. **User-Friendly Output**: Color-coded console output with clear progress indicators
4. **Validation**: Comprehensive post-installation validation
5. **Rollback Support**: Configuration backups before modifications

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

#### DependencyInstaller

- Checks and installs Homebrew
- Installs uv package manager
- Handles PATH configuration

#### EnvironmentSetup

- Creates .env from template
- Manages Python dependencies via uv
- Validates environment structure

#### APIKeyManager

- Interactive API key configuration
- Distinguishes required vs optional keys
- Secure input handling

#### ClaudeDesktopConfig

- Auto-detects Claude Desktop installation
- Configures MCP server integration
- Backs up existing configurations

#### UpdaterConfig

- Prompts user for the update zip file URL
- Saves configuration to the `.env` file

#### UpdateManager

- Downloads and verifies the update package
- Manages the backup and file replacement process
- Provides clear, user-friendly status updates

### Validators

- Comprehensive post-installation checks
- Detailed error reporting
- Distinguishes errors from warnings

## Usage

The installer is run from the project root via the Makefile:

```bash
make install
```

The installer will:

1. Check system requirements
2. Install missing dependencies
3. Configure the environment
4. Set up API keys interactively
5. Configure Claude Desktop automatically
6. Validate the installation

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
