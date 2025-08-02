# Event Importer

## v1.3.7

[![Tests](https://github.com/restlessnites/event-importer/actions/workflows/tests.yml/badge.svg)](https://github.com/restlessnites/event-importer/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-54.7%25-green)](https://github.com/restlessnites/event-importer)

A tool that extracts structured event data from websites, images, and APIs. Use it as a **command-line tool**, **HTTP API server**, or **MCP server** for AI assistants.

---

## Installation

### For Most Users (Recommended)

Download and run the installer for a guided setup experience.

1. **Download**: Get the latest `event-importer-installer.zip` from [Dropbox](https://www.dropbox.com/scl/fi/aqldz7tbym0tla2js7bdp/event-importer-installer.zip?rlkey=ocmjxmtiauk8enswm6j1vz2u2&st=pftsjs2h&dl=1)

2. **Extract and Run**:
   - Double-click the downloaded zip file to extract it
   - Double-click the `event-importer-installer` file to run it

The installer will automatically:

- Create the `~/Applications/event-importer` directory
- Move itself to the proper location
- Clean up downloaded files
- Download the latest Event Importer application
- Guide you through API key configuration
- Set up Claude Desktop integration (if installed)
- Configure your shell PATH (optional)

After installation, Event Importer will be available at:

```bash
~/Applications/event-importer/event-importer
```

### For Developers (From Source)

Clone and run from source for development:

```bash
# Clone the repository
git clone https://github.com/restlessnites/event-importer.git
cd event-importer

# Set up the development environment
make dev-setup

# Configure API keys
cp env.example .env
# Edit .env with your API keys
```

---

## Updating

### Manual Updates

1. **Download** the latest installer from [Dropbox](https://www.dropbox.com/scl/fi/aqldz7tbym0tla2js7bdp/event-importer-installer.zip?rlkey=ocmjxmtiauk8enswm6j1vz2u2&st=pftsjs2h&dl=1)
2. **Run** the installer - Select the "Update" option
3. **Wait** for the update to complete

---

## Migration

### From Previous Installations

If you have a previous installation of Event Importer, the installer can migrate your data:

1. **Run the new installer**
2. When prompted, choose "Yes" to migrate from a previous installation
3. **Enter the path** to your previous installation (e.g., `/path/to/old/event-importer`)
4. The installer will migrate:
   - API keys from `.env` file
   - Event database from `data/events.db`

### Manual Migration

If automatic migration fails, you can manually migrate:

```bash
# Copy your API keys
cp /old/installation/.env ~/Library/Application\ Support/event-importer/

# Copy your event database
cp /old/installation/data/events.db ~/Library/Application\ Support/event-importer/
```

---

## Making the Command Globally Accessible

If you didn't configure PATH during installation, you can still make `event-importer` globally accessible:

### Option 1: Add to PATH

```bash
# Add to your shell profile (~/.zshrc, ~/.bash_profile, etc.)
export PATH="$HOME/Applications/event-importer:$PATH"

# Reload your shell
source ~/.zshrc
```

### Option 2: Create a Symlink

```bash
# Create a symlink in a directory already in your PATH
ln -s ~/Applications/event-importer/event-importer /usr/local/bin/event-importer
```

After either option, you can use `event-importer` from any directory.

---

## Documentation

### Core Guides

- **[Usage Guide](docs/USAGE.md)**: Detailed instructions for the CLI, API, and MCP interfaces
- **[Architecture](docs/ARCHITECTURE.md)**: Technical overview of the project architecture
- **[Development Guide](docs/DEVELOPMENT.md)**: Setup and guidelines for developers

### Feature Documentation

- **[API Reference](docs/API.md)**: Complete HTTP API documentation
- **[MCP Server](docs/MCP.md)**: Model Context Protocol (MCP) integration for AI assistants
- **[Genre Enhancer](docs/GENRE_ENHANCER.md)**: How the AI-powered genre detection works
- **[Image Enhancer](docs/IMAGE_ENHANCER.md)**: Image search and enhancement system
- **[Integrations](docs/INTEGRATIONS.md)**: How to build and use integrations (e.g., TicketFairy)

### Build & Distribution

- **[Build Process](docs/BUILD_PROCESS.md)**: How to package the application
- **[Cross Platform](docs/CROSS_PLATFORM.md)**: Platform-specific considerations and support

---

## Troubleshooting

### Installation Issues

#### Permission Denied

- The installer needs write access to `~/Applications` and `~/Library/Application Support`
- Try running from your home directory
- Check directory permissions

#### Download Failed

- Check your internet connection
- The installer will prompt for an alternative download URL if needed
- You can manually download from the releases page

#### API Keys Not Working

- Verify keys are correctly entered (no extra spaces)
- Check the [API key documentation](docs/USAGE.md#api-keys) for required format
- Some keys are optional - you only need keys for the sources you plan to use

### Migration Issues

#### Can't Find Previous Installation

- Ensure you provide the full path to the root directory
- Look for the directory containing `.env` file at the root
- The installer migrates:
  - `.env` file (API keys and settings)
  - `data/events.db` (your event database)

#### Database Migration Failed

- Ensure the old database isn't corrupted
- Check that you have enough disk space
- Manual migration is an option (see above)

### Runtime Issues

See the [Usage Guide](docs/USAGE.md) for common runtime issues and solutions.

---

## Quick Start

After installation:

```bash
# Import an event from a URL
event-importer events import https://ra.co/events/1234567

# View imported events
event-importer events list

# View event details
event-importer events details 1

# Rebuild event data (preview only - use update to save)
event-importer events rebuild description 1 --type short
event-importer events rebuild genres 1 --context "electronic music"
event-importer events rebuild image 1

# Update event fields
event-importer events update 1 --title "New Title" --venue "New Venue"

# Get statistics
event-importer stats

# Configure settings
event-importer settings list
event-importer settings set ANTHROPIC_API_KEY your-key-here

# Start the API server
event-importer api

# Use with Claude Desktop (MCP)
event-importer mcp
```

For detailed usage instructions, see the [Usage Guide](docs/USAGE.md).
