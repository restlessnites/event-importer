"""Health check API routes."""

import logging

from fastapi import APIRouter

from app import __version__
from app.interfaces.api.models.responses import HealthResponse
from app.services.integration_discovery import get_enabled_integrations
from config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        features = config.get_enabled_features()
        integrations = get_enabled_integrations()

        return HealthResponse(
            status="healthy",
            version=__version__,
            features=features,
            integrations=integrations,
        )
    except (ValueError, TypeError, KeyError):
        logger.exception("Health check error")
        return HealthResponse(status="unhealthy", version=__version__, features=[])
