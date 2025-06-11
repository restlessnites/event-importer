"""CLI interface"""

import asyncio
import sys

from app.interfaces.cli.core import CLI
from app.interfaces.cli.theme import Theme
from app.config import get_config
from app.core.router import Router
from app.shared.http import close_http_service 

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
            "ignore_cache": getattr(args, 'ignore_cache', False),  # Handle CLI flag
        }
        
        if args.method:
            request_data["force_method"] = args.method
        
        cli.header("Event Importer", f"Importing from: {args.url}")
        
        # Show cache status
        if request_data.get("ignore_cache"):
            cli.info("🔄 Cache ignored - forcing fresh import")
        else:
            cli.info("💾 Cache enabled - will use cached data if available")
        
        # Show progress
        with cli.progress("Importing event data..."):
            result = await router.route_request(request_data)
        
        # Display result
        if result.get("success"):
            cli.success("Import successful!")
            cli.event_card(result["data"])
        else:
            cli.error(f"Import failed: {result.get('error', 'Unknown error')}")
            return False  # Don't exit here, let cleanup happen
            
        return True
            
    except Exception as e:
        cli.error(f"CLI error: {e}")
        return False
    finally:
        # ALWAYS clean up HTTP connections
        try:
            with cli.spinner("Cleaning up connections..."):
                await close_http_service()
        except Exception as e:
            cli.warning(f"Cleanup warning: {e}")


def run_cli(args):
    """Run the CLI with the given args."""
    try:
        success = asyncio.run(main(args))
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        cli = get_cli()
        cli.warning("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        cli = get_cli() 
        cli.error(f"Fatal error: {e}")
        sys.exit(1)


__all__ = ["get_cli", "CLI", "Theme", "main", "run_cli"]