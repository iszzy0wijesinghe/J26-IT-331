from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeoNexSettings(BaseSettings):
    """Central runtime configuration for GeoNex services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="GEONEX_",
        case_sensitive=False,
        extra="ignore",
    )

    env: Literal["development", "test", "demo", "production"] = "development"

    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "geonex"
    db_user: str = "geonex"
    db_password: str = ""

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    @property
    def database_url(self) -> str:
        """Return a PostgreSQL SQLAlchemy-compatible connection URL."""

        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> GeoNexSettings:
    """Return one cached settings instance per process."""

    return GeoNexSettings()