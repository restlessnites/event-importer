"""Logging middleware for API requests."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log API requests and responses."""

    async def dispatch(
        self: LoggingMiddleware,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process the request and log details."""
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url}")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(f"Response: {response.status_code} - {duration:.3f}s")

        return response


def add_logging_middleware(app: FastAPI) -> None:
    """Add logging middleware to the FastAPI app."""
    app.add_middleware(LoggingMiddleware)
