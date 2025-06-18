"""CLI interface with improved error handling"""

import asyncio
import sys
import logging

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


class SuppressConsoleHandler(logging.StreamHandler):
    """Custom handler that suppresses console output during CLI operations."""
    
    def emit(self, record):
        # Don't emit to console - let error capture handle it
        pass


def setup_quiet_logging():
    """Set up logging to suppress console output during CLI import."""
    # Remove existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our suppressing handler
    suppress_handler = SuppressConsoleHandler()
    root_logger.addHandler(suppress_handler)
    
    # Set reasonable levels
    root_logger.setLevel(logging.WARNING)


async def main(args):
    """Main CLI entry point with clean error handling."""
    cli = get_cli()
    
    # Check if verbose mode is enabled
    verbose = getattr(args, 'verbose', False)
    
    # Only set up quiet logging if not in verbose mode
    if not verbose:
        setup_quiet_logging()
    
    try:
        # Validate configuration
        config = get_config()
        
        if not args.url:
            cli.error("URL is required")
            sys.exit(1)
        
        # Start capturing errors before any operations (but only if not verbose)
        if not verbose:
            cli.error_capture.start(logging.WARNING)
        
        # Create router
        router = Router()
        
        # Create request
        request_data = {
            "url": args.url,
            "timeout": args.timeout,
            "ignore_cache": getattr(args, 'ignore_cache', False),
        }
        
        if args.method:
            request_data["force_method"] = args.method
        
        # Clean header without emojis
        cli.header("EVENT IMPORTER", f"Importing from: {args.url}")
        
        # Show cache status without emojis
        if request_data.get("ignore_cache"):
            cli.info("Cache ignored - forcing fresh import")
        else:
            cli.info("Cache enabled - will use cached data if available")
        
        # Show verbose status
        if verbose:
            cli.info("Verbose logging enabled")
        
        # Show progress with clean output
        with cli.progress("Importing event data...") as progress_cli:
            result = await router.route_request(request_data)
        
        # Stop capturing errors (if we started it)
        if not verbose:
            cli.error_capture.stop()
        
        # Display result
        if result.get("success"):
            cli.success("Import successful")
            cli.event_card(result["data"])
        else:
            error_msg = result.get("error", "Unknown error")
            cli.error(f"Import failed: {error_msg}")
            
            # Show captured errors if any (only in non-verbose mode)
            if not verbose and (cli.error_capture.has_errors() or cli.error_capture.has_warnings()):
                cli.show_captured_errors("Error Details")
            
            return False
            
        return True
            
    except Exception as e:
        cli.error(f"CLI error: {e}")
        
        # Show captured errors (only in non-verbose mode)
        if not verbose and (cli.error_capture.has_errors() or cli.error_capture.has_warnings()):
            cli.show_captured_errors("Error Details")
        
        return False
    finally:
        # ALWAYS clean up HTTP connections
        try:
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
        cli.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        cli = get_cli() 
        cli.error(f"Fatal error: {e}")
        sys.exit(1)


__all__ = ["get_cli", "CLI", "Theme", "main", "run_cli"]