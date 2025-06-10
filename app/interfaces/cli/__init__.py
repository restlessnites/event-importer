"""CLI interface for event importer."""

import asyncio
import sys
from typing import Optional

from app.interfaces.cli.core import CLI
from app.interfaces.cli.theme import Theme
from app.config import get_config
from app.core.router import Router
from app.schemas import ImportRequest

# Global instance
_cli: CLI | None = None


def get_cli() -> CLI:
    """Get the global CLI instance."""
    global _cli
    if _cli is None:
        _cli = CLI()
    return _cli


async def main(args):
    """Main CLI entry point."""
    cli = get_cli()
    
    try:
        # Validate configuration
        config = get_config()
        
        if not args.url:
            cli.error("URL is required")
            sys.exit(1)
        
        # Create router
        router = Router()
        
        # Create request
        request_data = {
            "url": args.url,
            "timeout": args.timeout,
        }
        
        if args.method:
            request_data["force_method"] = args.method
        
        cli.header("Event Importer", f"Importing from: {args.url}")
        
        # Show progress
        with cli.progress("Importing event data..."):
            result = await router.route_request(request_data)
        
        # Display result
        if result.get("success"):
            cli.success("Import successful!")
            cli.event_card(result["data"])
        else:
            cli.error(f"Import failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        cli.error(f"CLI error: {e}")
        sys.exit(1)


def run_cli(args):
    """Run the CLI with the given args."""
    asyncio.run(main(args))


__all__ = ["get_cli", "CLI", "Theme", "main", "run_cli"]
