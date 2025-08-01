"""Runtime configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class RuntimeConfig(BaseSettings):
    """Runtime configuration settings."""

    debug: bool = Field(False, alias="DEBUG")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
