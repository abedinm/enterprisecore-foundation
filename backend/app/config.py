"""
Centralized application configuration.

All settings come from environment variables (or a .env file in development).
Use `from app.config import settings` everywhere — never read env vars directly.
"""

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    # App metadata
    app_name: str = "EnterpriseCore AI Suite"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    # JWT / Security
    secret_key: str = Field(default="dev-only-secret-change-me", min_length=16)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    # Database
    database_url: str = "sqlite:///./data/enterprisecore.db"

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    # First admin (seeded on startup if no users exist).
    # Note: pydantic-email rejects `.local` as a reserved TLD; use a real one.
    first_admin_email: str = "admin@enterprisecore.io"
    first_admin_password: str = "Admin123!"
    first_admin_name: str = "System Admin"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton instance imported everywhere.
settings = Settings()
