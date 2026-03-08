"""Application settings loaded from environment variables via pydantic-settings."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for EchoBridge AI.

    Every field has a default so the application starts cleanly with an
    empty .env file.  Set real values in .env before deploying.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    DEBUG: bool = True
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ------------------------------------------------------------------
    # Backboard (AI backbone)
    # ------------------------------------------------------------------
    BACKBOARD_API_KEY: str = ""

    # ------------------------------------------------------------------
    # ElevenLabs (TTS)
    # ------------------------------------------------------------------
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"

    # ------------------------------------------------------------------
    # Google Cloud (STT)
    # ------------------------------------------------------------------
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # ------------------------------------------------------------------
    # Cloudinary (media storage)
    # ------------------------------------------------------------------
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ------------------------------------------------------------------
    # Supabase (database)
    # ------------------------------------------------------------------
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ------------------------------------------------------------------
    # Tailscale (private networking)
    # ------------------------------------------------------------------
    TAILSCALE_ENABLED: bool = False
    TAILSCALE_HOSTNAME: str = ""

    # ------------------------------------------------------------------
    # Auth0 (authentication)
    # ------------------------------------------------------------------
    AUTH0_DOMAIN: str = ""
    AUTH0_AUDIENCE: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        """Accept a comma-separated string or a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]


settings = Settings()
