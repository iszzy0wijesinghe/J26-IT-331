from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


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

    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5433, ge=1, le=65535)
    db_name: str = "geonex"
    db_user: str = "geonex_app"
    db_password: SecretStr = SecretStr("")

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    @property
    def database_url(self) -> URL:
        """Build a PostgreSQL URL with safely encoded credentials."""

        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> GeoNexSettings:
    """Return one cached settings instance per process."""

    return GeoNexSettings()