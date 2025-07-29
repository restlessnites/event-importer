# Event Importer

[![Tests](https://github.com/restlessnites/event-importer/actions/workflows/tests.yml/badge.svg)](https://github.com/restlessnites/event-importer/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-52.6%25-green)](https://github.com/restlessnites/event-importer)

A tool that extracts structured event data from websites, images, and APIs. Use it as a **command-line tool**, **HTTP API server**, or **MCP server** for AI assistants.

---

## Installation

There are two ways to install the Event Importer, depending on your needs.

### For Most Users (Recommended)

This method is for non-technical users who want to use the application without having to set up a development environment.

1. **Download**: Get the latest `Restless-Event-Importer.zip` file from the project's releases page or the link provided in Slack.
2. **Unzip**: Unzip the file to a location of your choice (e.g., your `Documents` folder).
3. **Run Setup**: Open the Terminal app, navigate to the unzipped folder, and run the setup command:

    ```bash
    # Example if you unzipped it in your Documents folder
    cd ~/Documents/event-importer
    event-importer setup
    ```

The interactive setup process will guide you through configuring your API keys and connecting the tool to the Claude Desktop app. All API keys for all features are required.

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
    # Now edit .env
    ```

---

## Documentation

- **[Usage Guide](docs/USAGE.md)**: Detailed instructions for the CLI, API, and MCP interfaces.
- **[Development Guide](docs/DEVELOPMENT.md)**: A technical overview for developers, including testing and configuration.
- **[Build and Distribution](docs/BUILD_PROCESS.md)**: How to package the application with PyInstaller.
- **[Architecture](docs/ARCHITECTURE.md)**: A technical overview of the project's architecture.
- **[Integrations](docs/INTEGRATIONS.md)**: How to build and use integrations.
- **[AI Enhancement](docs/AI_ENHANCEMENT.md)**: How the AI-powered features like genre and image enhancement work.
