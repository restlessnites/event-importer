# Event Importer MCP Guide

This guide explains how to use the Event Importer as a tool within Claude Desktop using MCP (Model Context Protocol). It is designed for users who may not be developers.

## What is MCP?

MCP allows AI assistants like Claude Desktop to connect to and use external tools on your local machine. By setting up the Event Importer with MCP, you can ask Claude to import, list, and manage event data using simple conversational commands.

## Setup

**⚠️ Important**: You must install Event Importer first using the installer before setting up MCP integration.

### Step 1: Install Event Importer

Follow the installation instructions in the main [README.md](../README.md) to install Event Importer using the installer. The installer will automatically set up Claude Desktop integration if Claude Desktop is detected on your system.

### Step 2: Manual Claude Desktop Configuration (if needed)

If the installer didn't automatically configure Claude Desktop, or if you need to reconfigure it, follow these steps:

1. Open Claude Desktop
2. Go to Claude > Settings > Developer
3. Click "Edit Config" to open the configuration file
4. Add the following configuration:

```json
{
  "mcpServers": {
    "event-importer": {
      "command": "/Users/your-username/Applications/event-importer/event-importer",
      "args": ["mcp"]
    }
  }
}
```

**Replace `/Users/your-username` with your actual username.**

### Finding Your Username

If you're not sure what your username is:

1. Press `Cmd+Space`, type "terminal", and press Enter
2. In the terminal, type `whoami` and press Enter
3. Your username will be displayed
4. Replace `your-username` in the path above with this value

### Step 3: Restart Claude Desktop

After updating the configuration, restart Claude Desktop for the changes to take effect.

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
>
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

### Event Management Tools

#### `rebuild_event_description`

**What it does**: Regenerates the event description using AI. You can choose to regenerate either the short summary or the long detailed description.

**When to use it**: When an event has a poor description or you want to provide additional context to improve it.

**Parameters**:

- `event_id` (required): The ID of the event to rebuild the description for.
- `description_type` (required): Either "short" or "long" to specify which description to regenerate.
- `supplementary_context` (optional): Additional context to help generate a better description.

**Example Conversation**:
> **You**: The description for event 42 is too generic. Can you regenerate it with more focus on the underground techno aspect?
>
> **Claude**: *(uses `rebuild_event_description` with `event_id: 42, description_type: "long", supplementary_context: "underground techno event"`)*
>
> **Claude**: I've regenerated the long description for event 42. Here's the new version:
>
> "Step into the depths of underground techno culture at this immersive night..."
>
> Would you like me to save this new description?

---

#### `update_event`

**What it does**: Updates any field of an event in the database. You can change the title, venue, date, time, lineup, genres, and more.

**When to use it**: When you need to correct or update information for an event that's already been imported.

**Parameters**:

- `event_id` (required): The ID of the event to update.
- `updates` (required): An object containing the fields to update. Can include:
  - `title`: Event title
  - `venue`: Venue name
  - `date`: Start date (YYYY-MM-DD)
  - `end_date`: End date for multi-day events (YYYY-MM-DD)
  - `time`: Time object with `start`, `end`, and `timezone`
  - `lineup`: Array of artist names
  - `genres`: Array of genre names
  - `short_description`: Brief description (max 200 chars)
  - `long_description`: Detailed description
  - `cost`: Ticket price
  - `minimum_age`: Age restriction
  - `ticket_url`: Link to tickets
  - `images`: Object with `full` and `thumbnail` URLs
  - `location`: Object with `city`, `state`, `country`, and `coordinates`

**Example Conversation**:
> **You**: Update event 23 - the venue changed to "The New Warehouse" and it's now starting at 10pm instead of 9pm
>
> **Claude**: *(uses `update_event` with `event_id: 23, updates: {"venue": "The New Warehouse", "time": {"start": "22:00", "end": "04:00", "timezone": "America/Los_Angeles"}}`)*
>
> **Claude**: I've updated event 23:
>
> - Venue changed to "The New Warehouse"
> - Start time changed to 10:00 PM
>
> The changes have been saved to the database.

---

#### `rebuild_genres`

**What it does**: Re-analyzes and regenerates the genres for an event using AI and search. Shows a preview without saving.

**When to use it**: When an event has incorrect or missing genres, or when you want to provide additional context to improve genre detection.

**Parameters**:

- `event_id` (required): The ID of the event to rebuild genres for.
- `supplementary_context` (optional): Additional context to help identify genres. Required if the event has no lineup.

**Example Conversation**:
> **You**: Event 15 has no genres. Can you rebuild them? The artists are Four Tet and Floating Points.
>
> **Claude**: *(uses `rebuild_genres` with `event_id: 15, supplementary_context: "Four Tet, Floating Points"`)*
>
> **Claude**: I've analyzed the event and found these genres:
>
> - Electronic
> - Ambient
> - IDM
> - Experimental
>
> This is a preview. Would you like me to save these genres?

---

#### `rebuild_image`

**What it does**: Searches for and selects the best image for an event. Shows all candidates found and the selected best image.

**When to use it**: When an event has a low-quality image or no image, and you want to find a better one.

**Parameters**:

- `event_id` (required): The ID of the event to find images for.
- `supplementary_context` (optional): Additional context to help find better images (e.g., "official poster 2024").

**Example Conversation**:
> **You**: Event 20 has a blurry image. Can you find a better one?
>
> **Claude**: *(uses `rebuild_image` with `event_id: 20`)*
>
> **Claude**: I found 5 image candidates:
>
> **Best Image Selected**:
>
> - Score: 230
> - Source: Event Website
> - Dimensions: 1200x630
> - Reason: High quality official event poster
>
> Would you like me to update the event with this image?

---

### Integration Tools (TicketFairy)

These tools are for submitting imported events to the TicketFairy service. This is a more advanced use case.

#### `submit_ticketfairy`

**What it does**: Submits an event to TicketFairy from a URL. This imports the event and submits it to TicketFairy in one step.

**When to use it**: When you want to import an event and immediately submit it to TicketFairy.

**Parameters**:

- `url` (required): The source URL of the event page to submit.
- `dry_run` (optional): If `true`, shows the transformed data without actually submitting. This is great for testing.

**Example Conversation**:
> **You**: Submit this event to TicketFairy: <https://ra.co/events/1234567>
>
> **Claude**: *(uses `submit_ticketfairy` with `url: "https://ra.co/events/1234567"`)*
>
> **You**: Do a dry run first to see what would be submitted
>
> **Claude**: *(uses `submit_ticketfairy` with `url: "https://ra.co/events/1234567", dry_run: true`)*

---

## Common Issues and Solutions

### "event-importer tools not found"

- Make sure you've installed Event Importer using the installer first
- Check that the path in your Claude Desktop config is correct
- Restart Claude Desktop after making configuration changes

### "Permission denied" errors

- Make sure the event-importer binary has execute permissions
- If needed, run `chmod +x ~/Applications/event-importer/event-importer` in terminal

### Tools appear but don't work

- Check that your API keys are configured properly
- The installer should have guided you through API key setup
- You can reconfigure by running the installer again

---

## Getting Help

If you encounter issues:

1. Check the main [README.md](../README.md) for installation troubleshooting
2. Look at the [USAGE.md](USAGE.md) guide for detailed command examples
3. Review the installer logs if MCP integration setup failed
