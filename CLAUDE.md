# Claude Context - Event Importer

## Project Overview
Event Importer is a CLI tool that extracts structured event data from websites. It uses various agents (RA, Ticketmaster, Dice, etc.) to parse event information and can be integrated with Claude Desktop via MCP.

## Recent Major Refactoring (2025-07-29)

### CLI System Overhaul
**Complete migration from mixed CLI system (Typer, custom, Rich) to clicycle**
- All CLI commands now use clicycle for consistent theming and display
- Removed dependencies: Typer, Rich, custom CLI system
- All tests updated to use clicycle

### Key Architecture Decisions

#### 1. Separation of Concerns
- **Installer**: Standalone tool for setup, configuration, and validation
- **App**: Main application focused on event importing
- **No backwards compatibility**: Complete rewrite was chosen over gradual migration

#### 2. Integration System
- Integrations are intentionally decoupled and can be added/removed dynamically
- Dynamic discovery using Python entry points
- Both CLI and MCP discover integrations automatically
- TicketFairy is now integrated into main CLI (not a separate tool)

#### 3. Configuration
- Moved from JSON config to SQLite storage (using shared SettingsStorage)
- Shared configuration module between installer and app
- API keys and settings stored in SQLite database

#### 4. Validation
- Validation is **installer concern only** - removed from app entirely
- No validate command in main CLI
- Validation checks API keys and database connectivity

## Important Guidelines

### CLI Usage with clicycle
```python
# Always configure at start of function/test
clicycle.configure(app_name="event-importer")

# Display hierarchy
clicycle.header("Main heading")      # First in a group
clicycle.section("Sub-heading")      # Subsections under header
clicycle.info("Information")         # General info
clicycle.success("Success message")  # Success feedback
clicycle.error("Error message")      # Error feedback
clicycle.warning("Warning")          # Warnings
clicycle.table([data], title="...")  # Tables

# Important rules:
# - Never use bullet points manually (no •)
# - Use clicycle.list_item() for bullet lists
# - Never use \n in clicycle output
# - No emojis unless user explicitly requests
```

### Testing
- All integration tests updated to use clicycle
- Run with: `python -m pytest tests/`
- Coverage requirement: 50% minimum

### File Structure
```
event-importer/
├── app/                    # Main application
│   ├── interfaces/        
│   │   ├── cli/           # CLI commands (using clicycle)
│   │   ├── api/           # HTTP API
│   │   └── mcp/           # MCP server
│   ├── integrations/      # Dynamic integrations
│   │   └── ticketfairy/   # TicketFairy integration
│   └── services/          # Core services
├── installer/             # Standalone installer
│   ├── components/        # Installer components
│   └── validation.py      # Installation validation
├── config/                # Shared configuration
│   ├── settings.py        # Settings definitions
│   └── storage.py         # SQLite storage
└── tests/                 # All tests (updated for clicycle)
```

### Make Commands
- `make install` - Install dependencies
- `make test` - Run tests
- `make lint` - Run linting
- `make format` - Format code
- `make build` - Build packaged app
- `make run-api` - Run API server
- `make run-mcp` - Run MCP server

### CLI Commands
```bash
# Main commands
event-importer import-event <url>
event-importer stats
event-importer list-events
event-importer event-details <id>
event-importer api
event-importer mcp

# Integration commands (dynamically discovered)
event-importer ticketfairy submit <args>
event-importer ticketfairy stats
```

## Current State (as of 2025-07-29)
- ✅ CLI fully migrated to clicycle
- ✅ All tests updated and passing
- ✅ Installer separated from app
- ✅ TicketFairy integrated into main CLI
- ✅ Dynamic integration discovery working
- ✅ MCP server can see integration tools
- ✅ Documentation updated

## Pending/Shelved Items
- Validation command approach (shelved - user said "shelve it for now")
- PATH configuration in installer (implemented but may need testing)

## Common Issues and Solutions

### Installer Running During Development
- Fixed by checking `sys.frozen` - installer only runs in packaged apps
- SQLite storage checked for first-run detection

### Import Errors in Tests
- All old CLI imports removed
- Use `import clicycle` instead of old CLI system
- No more references to removed modules

### Circular Dependencies
- Avoided by proper module organization
- Imports at module level are fine (user confirmed)

## Key User Preferences
1. **No emojis** unless explicitly requested
2. **Use clicycle.list_item()** for bullet points, not manual bullets
3. **No newlines (\n)** in clicycle output
4. **Complete rewrites preferred** over backwards compatibility
5. **Separation of concerns** - keep installer and app separate
6. **Dynamic discovery** for integrations
7. **Consistent use of clicycle** throughout codebase

## Next Session Context
When continuing work on this project:
1. All CLI commands use clicycle
2. Tests are working with new system
3. Installer is separate from app
4. Validation exists only in installer
5. Integrations are dynamically discovered
6. Configuration uses SQLite storage