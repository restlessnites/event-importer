"""MCP server implementation for the event importer."""

import asyncio
import logging
import sys
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from app import __version__
from app.config import get_config
from app.core.router import Router
from app.shared.http import close_http_service


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# MCP Tool Schema
IMPORT_EVENT_TOOL = types.Tool(
    name="import_event",
    description="Import structured event information from a URL",
    inputSchema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL of the event page to import",
            },
            "force_method": {
                "type": "string",
                "enum": ["api", "web", "image"],
                "description": "Force a specific import method",
            },
            "include_raw_data": {
                "type": "boolean",
                "description": "Include raw extracted data in response",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 60)",
                "default": 60,
                "minimum": 1,
                "maximum": 300,
            },
        },
        "required": ["url"],
    },
)


async def main():
    """Main entry point for the MCP server."""
    logger.info(f"Starting Event Importer MCP Server v{__version__}")

    # Validate configuration
    try:
        config = get_config()
        features = config.get_enabled_features()
        logger.info(f"Enabled features: {features}")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create server and router
    server = Server("event-importer")
    router = Router()

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools."""
        return [IMPORT_EVENT_TOOL]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent]:
        """Handle tool calls."""
        if name != "import_event":
            raise ValueError(f"Unknown tool: {name}")

        try:
            # Route the request
            result = await router.route_request(arguments)

            # Return as JSON text
            import json

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Tool call error: {e}")
            import json

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": str(e)}, indent=2),
                )
            ]

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        try:
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="event-importer",
                    server_version=__version__,
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        finally:
            # Cleanup
            await close_http_service()


def run():
    """Entry point for the MCP server script."""
    asyncio.run(main())


if __name__ == "__main__":
    run() 