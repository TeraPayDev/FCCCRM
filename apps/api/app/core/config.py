from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "cram-development-only-jwt-secret-change-before-non-development"


class Settings(BaseSettings):
    """Application settings for the CRAM API."""

    app_name: str = "CRAM API"
    app_description: str = "Climate Risk Analytics Management Platform API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://10.1.11.7:3000,http://localhost:3000"

    auth_jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    auth_access_token_minutes: int = 15
    auth_refresh_token_minutes: int = 60 * 24 * 7
    auth_failed_login_limit: int = 5
    auth_lock_minutes: int = 15

    copernicus_cds_url: str = "https://cds.climate.copernicus.eu/api"
    copernicus_cds_key: SecretStr | None = None

    # CRAM AI Assistant
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5-mini"
    openai_timeout_seconds: float = 45.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a normalized list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_auth_secret(self) -> Settings:
        if (
            self.app_env.lower() not in {"development", "test", "testing"}
            and self.auth_jwt_secret.get_secret_value() == DEV_JWT_SECRET
        ):
            raise ValueError(
                "AUTH_JWT_SECRET must be explicitly configured outside development/test."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings object."""
    return Settings()
