"""API key configurations."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.loader import load_config
from config.paths import get_project_root


class APIConfig(BaseSettings):
    """API key configurations."""

    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    zyte_api_key: str | None = Field(None, alias="ZYTE_API_KEY")
    ticketmaster_api_key: str | None = Field(None, alias="TICKETMASTER_API_KEY")
    google_api_key: str | None = Field(None, alias="GOOGLE_API_KEY")
    google_cse_id: str | None = Field(None, alias="GOOGLE_CSE_ID")
    ticketfairy_api_key: str | None = Field(None, alias="TICKETFAIRY_API_KEY")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # For packaged app: config.json -> env vars
        # For development: .env -> env vars
        del settings_cls  # Required by pydantic but unused
        return (
            init_settings,
            lambda: load_config(),  # Only loads in packaged app
            env_settings,
            dotenv_settings,  # Only loads in development
            file_secret_settings,
        )

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )
