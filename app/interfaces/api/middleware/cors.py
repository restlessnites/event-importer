"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors_middleware(app: FastAPI) -> None:
    """Add CORS middleware to the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this based on your needs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ) 