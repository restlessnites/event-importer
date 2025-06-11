# Event Importer MCP Guide

This guide explains how to use the Event Importer as a tool within an MCP (Morpheus Connected Peripheral) compatible AI assistant, such as Claude Desktop. It is designed for users who may not be developers.

## What is MCP?

MCP allows AI assistants like Claude to connect to and use external tools on your local machine. By setting up the Event Importer with MCP, you can ask Claude to import, list, and manage event data using simple conversational commands.

## Setup

### Step 1: Start the MCP Server

First, you need to run the Event Importer's MCP server. Open your terminal, navigate to the `event-importer` directory, and run this command:

```bash
uv run event-importer-mcp
```

This command starts a server that listens for requests from your AI assistant. You must keep this terminal window open while you want to use the tools.

### Step 2: Configure Your AI Assistant (Claude Desktop)

Next, you need to tell your AI assistant how to connect to the Event Importer. In Claude Desktop, you can do this by editing its configuration file.

1. Open your Claude Desktop configuration.
2. Find the `mcpServers` section (or add it if it doesn't exist).
3. Add the following JSON block inside `mcpServers`:

```json
{
  "mcpServers": {
    "event-importer": {
      "command": "uv",
      "args": [
        "--directory",
        "/full/path/to/event-importer",
        "run",
        "event-importer-mcp"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_KEY",
        "ZYTE_API_KEY": "YOUR_KEY",
        "TICKETMASTER_API_KEY": "YOUR_KEY (Optional)",
        "GOOGLE_API_KEY": "YOUR_KEY (Optional)",
        "GOOGLE_CSE_ID": "YOUR_ID (Optional)"
      }
    }
  }
}
```

**Important Notes**:

- **`/full/path/to/event-importer`**: You **must** replace this with the absolute path to where you cloned the `event-importer` project on your computer.
  - On macOS/Linux, you can get this path by navigating to the directory in your terminal and running `pwd`.
  - On Windows, you can get it from the address bar in File Explorer.
- **API Keys**: Replace `YOUR_KEY` with your actual API keys. These are required for the importer to work. See the main `README.md` for instructions on how to get them.

Once configured, restart your AI assistant. You can now use the Event Importer tools.

## Available Tools

Here are the tools you can now use in your conversations with the AI.

---

### Core Event Tools

#### `import_event`

**What it does**: Imports all available information about an event from a given URL. This is the main tool you will use.

**When to use it**: When you have a link to an event page, a flyer image, or a ticket site and you want to extract the event details into a structured format.

**Parameters**:

- `url` (required): The web address of the event.

**Example Conversation**:
> **You**: Please import this event: <https://ra.co/events/2147288>
>
> **Claude**: *(uses the `import_event` tool)*
>
> **Claude**: Okay, I've imported the event "Synth-Etik Presents I Hate Models, Klaps, Raxeller". Here are the details:
>
> - **Venue**: Catch One
> - **Date**: 2025-05-21
> - **Lineup**: I Hate Models, Klaps, Raxeller
> - **Genres**: Techno

---

#### `list_events`

**What it does**: Shows a list of events that have already been imported and are stored in your local database.

**When to use it**: When you want to see what events you've recently imported or search for a specific event in your database.

**Parameters**:

- `limit` (optional): The maximum number of events to show.
- `search` (optional): A keyword to search for in the event data (e.g., artist name, venue).
- `summary_only` (optional): If `true`, shows a compact table view instead of full details for each event. Defaults to `false`.

**Example Conversation**:
> **You**: Show me the last 5 events I imported.
>
> **Claude**: *(uses the `list_events` tool with `limit: 5`)*
>
> **Claude**: Here are the last 5 events you imported: ...

> **You**: Find any events with "Cursive"
>
> **Claude**: *(uses `list_events` with `search: "Cursive"`)*

---

#### `show_event`

**What it does**: Displays all the detailed information for a single, specific event using its ID.

**When to use it**: After using `list_events`, if you want to see the full details of one particular event from the list.

**Parameters**:

- `event_id` (required): The numerical ID of the event. You can find this ID by using the `list_events` tool first.

**Example Conversation**:
> **You**: Show me the details for event 15.
>
> **Claude**: *(uses the `show_event` tool with `event_id: 15`)*
>
> **Claude**: Here are the full details for Event #15: ...

---

#### `get_statistics`

**What it does**: Provides analytics and a summary of your event database.

**When to use it**: When you want to see a high-level overview of your imported data, such as how many events you have in total, how many were imported recently, and submission statistics.

**Parameters**:

- `detailed` (optional): If `true`, provides a more comprehensive breakdown of statistics. Defaults to `false`.

**Example Conversation**:
> **You**: Can I get my import stats?
>
> **Claude**: *(uses the `get_statistics` tool)*
>
> **Claude**: Certainly. Here are your event statistics:
>
> - **Total Events**: 125
> - **Events Imported Today**: 8
> - ...

---

### Integration Tools (TicketFairy)

These tools are for submitting imported events to the TicketFairy service. This is a more advanced use case.

#### `submit_to_ticketfairy`

**What it does**: Submits events from your database to TicketFairy. You can filter which events to send.

**Parameters**:

- `filter` (optional): Which events to submit. Can be `unsubmitted`, `failed`, `pending`, or `all`. Defaults to `unsubmitted`.
- `dry_run` (optional): If `true`, shows which events *would* be submitted without actually sending them. This is great for testing.

**Example Conversation**:
> **You**: Do a dry run of submitting unsubmitted events to TicketFairy.
>
> **Claude**: *(uses `submit_to_ticketfairy` with `filter: "unsubmitted", dry_run: true`)*

#### `ticketfairy_status`

**What it does**: Shows the submission status for the TicketFairy integration, including total events, unsubmitted events, and a breakdown of successes and failures.

**When to use it**: To check on the health and progress of your TicketFairy submissions.

**Example Conversation**:
> **You**: What's the status of my TicketFairy submissions?
>
> **Claude**: *(uses the `ticketfairy_status` tool)*
