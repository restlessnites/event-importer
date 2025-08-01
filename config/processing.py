"""Configuration for data processing rules."""

from pydantic_settings import BaseSettings


class ProcessingConfig(BaseSettings):
    """Configuration for data processing rules."""

    long_description_min_length: int = 200
    short_description_max_length: int = 100
