"""Main application entry point and factory."""

import sys
import argparse
from app import __version__


def main():
    """Main entry point that routes to appropriate interface."""
    parser = argparse.ArgumentParser(
        prog="event-importer",
        description="Event Importer - Extract structured event data from websites",
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"event-importer {__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="interface", help="Interface to use")
    
    # CLI interface
    cli_parser = subparsers.add_parser("cli", help="Run CLI interface")
    cli_parser.add_argument("url", nargs="?", help="URL to import")
    cli_parser.add_argument("--method", choices=["api", "web", "image"], help="Force import method")
    cli_parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    
    # MCP interface  
    mcp_parser = subparsers.add_parser("mcp", help="Run MCP server")
    
    # API interface
    api_parser = subparsers.add_parser("api", help="Run HTTP API server")
    api_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    if not args.interface:
        # Default behavior - show help
        parser.print_help()
        return
    
    if args.interface == "cli":
        from app.interfaces.cli import run_cli
        run_cli(args)
    elif args.interface == "mcp":
        from app.interfaces.mcp.server import run as mcp_run
        mcp_run()
    elif args.interface == "api":
        from app.interfaces.api.server import run as api_run
        api_run(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
