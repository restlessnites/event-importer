"""FastAPI application for the event importer."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from app import __version__
from app.config import get_config
from app.shared.http import close_http_service
from app.interfaces.api.routes import events, health, statistics
from app.interfaces.api.middleware.cors import add_cors_middleware
from app.interfaces.api.middleware.logging import add_logging_middleware
from app.integrations import get_available_integrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting Event Importer API v{__version__}")
    
    try:
        config = get_config()
        features = config.get_enabled_features()
        logger.info(f"Enabled features: {features}")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Event Importer API")
    await close_http_service()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Event Importer API",
        description="Extract structured event data from websites",
        version=__version__,
        lifespan=lifespan,
    )
    
    # Add middleware
    add_cors_middleware(app)
    add_logging_middleware(app)
    
    # Add main routes
    app.include_router(events.router)
    app.include_router(health.router)
    app.include_router(statistics.router)
    
    # Auto-register integration routes
    integrations = get_available_integrations()
    for name, integration in integrations.items():
        if hasattr(integration, 'routes') and hasattr(integration.routes, 'router'):
            logger.info(f"Registering routes for integration: {name}")
            app.include_router(integration.routes.router)
    
    return app


def run(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Run the API server."""
    app = create_app()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run() 