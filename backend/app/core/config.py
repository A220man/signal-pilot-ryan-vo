"""Application configuration settings."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables (with .env fallback).

    Demo mode binds to localhost and skips authentication. Production
    deployments set DEMO_MODE=false and configure Keycloak OIDC.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = 8000
    demo_mode: bool = True

    # --- Database ---
    database_url: str = "sqlite:///./data/signal_pilot.db"

    # --- LLM (optional, for opt-in advisory explanations) ---
    llm_api_key: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None

    # --- Keycloak OIDC (planned) ---
    keycloak_server_url: str | None = None
    keycloak_realm: str | None = None
    keycloak_client_id: str | None = None
    keycloak_client_secret: str | None = None
    keycloak_redirect_uri: str | None = None
    keycloak_public_client: bool = True

    # --- Search defaults ---
    default_search_limit: int = 20
    max_search_limit: int = 100
    bm25_k1: float = 1.2
    bm25_b: float = 0.75

    # --- Version ---
    app_version: str = "1.0.0"

    @property
    def db_path(self) -> Path:
        """Resolve the SQLite file path from database_url."""
        url = self.database_url
        if url.startswith("sqlite:///"):
            return Path(url[len("sqlite:///"):])
        if url.startswith("sqlite://"):
            return Path(url[len("sqlite://"):])
        return Path(url)

    def assert_local_only(self) -> None:
        """Refuse to start demo mode on a non-localhost interface."""
        if self.demo_mode:
            if self.host not in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
                raise RuntimeError(
                    "Demo mode is only permitted on localhost interfaces. "
                    "Set DEMO_MODE=false and configure Keycloak OIDC for production."
                )
            if self.host == "0.0.0.0":
                raise RuntimeError(
                    "Demo mode refuses 0.0.0.0 binding. Use 127.0.0.1 or set DEMO_MODE=false."
                )


def get_settings() -> Settings:
    """Return a cached Settings instance (module-level singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.assert_local_only()
    return _settings


_settings: Settings | None = None