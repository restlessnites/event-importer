"""Health check API routes."""

import logging

from fastapi import APIRouter

from app import __version__
from app.config import get_config
from app.interfaces.api.models.responses import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        config = get_config()
        features = config.get_enabled_features()

        return HealthResponse(status="healthy", version=__version__, features=features)
    except (ValueError, TypeError, KeyError):
        logger.exception("Health check error")
        return HealthResponse(status="unhealthy", version=__version__, features=[])
