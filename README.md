# Event Importer

[![Tests](https://github.com/restlessnites/event-importer/actions/workflows/tests.yml/badge.svg)](https://github.com/restlessnites/event-importer/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-52.6%25-green)](https://github.com/restlessnites/event-importer)

A tool that extracts structured event data from websites, images, and APIs. Use it as a **command-line tool**, **HTTP API server**, or **MCP server** for AI assistants.

---

## Installation

### For Most Users (Recommended)

This method is for non-technical users who want to use the application without setting up a development environment.

1. **Download**: Get the latest `restless-event-importer-installer.zip` file from the releases page or the link provided in Slack.

2. **Extract and Run**: Double-click the downloaded zip file to extract it, then double-click the `event-importer-installer` file to run it.

The installer will automatically:

- Create the `~/Applications/restless-event-importer` directory
- Move itself to the proper location
- Clean up the downloaded files
- Download the latest Event Importer application
- Guide you through configuring API keys
- Set up Claude Desktop integration (if installed)
- Optionally configure your shell to make `event-importer` globally accessible
- Launch the Event Importer when complete

After installation, the Event Importer will be available at:

```bash
~/Applications/restless-event-importer/event-importer
```

### Making the Command Globally Accessible

If you chose not to configure PATH during installation, you can still make `event-importer` globally accessible:

```bash
# Add to your shell profile (~/.zshrc, ~/.bash_profile, etc.)
export PATH="$HOME/Applications/restless-event-importer:$PATH"

# Or create a symlink in a directory already in your PATH
ln -s ~/Applications/restless-event-importer/event-importer /usr/local/bin/event-importer
```

After restarting your terminal or running `source ~/.zshrc`, you can use `event-importer` from any directory.

### For Developers (From Source)

This method is for developers who want to run the application from source or contribute to its development.

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/restlessnites/event-importer.git
   cd event-importer
   ```

2. **Set Up the Environment**:
   ```bash
   make dev-setup
   ```

3. **Configure API Keys**:
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

---

## Documentation

- **[Usage Guide](docs/USAGE.md)**: Detailed instructions for the CLI, API, and MCP interfaces.
- **[Development Guide](docs/DEVELOPMENT.md)**: A technical overview for developers, including testing and configuration.
- **[Build and Distribution](docs/BUILD_PROCESS.md)**: How to package the application with PyInstaller.
- **[Architecture](docs/ARCHITECTURE.md)**: A technical overview of the project's architecture.
- **[Integrations](docs/INTEGRATIONS.md)**: How to build and use integrations.
- **[AI Enhancement](docs/AI_ENHANCEMENT.md)**: How the AI-powered features like genre and image enhancement work.
