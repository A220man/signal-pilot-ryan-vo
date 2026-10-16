"""Signal Pilot — FastAPI application factory.

The application is a token-efficient BM25 search engine for AI agent memory
and RAG contexts. Documents are indexed once and searched with deterministic
BM25 ranking — the core retrieval engine works offline without any LLM key.

In demo mode (default), the server binds to 127.0.0.1 only and requires no
authentication. Production deployments set DEMO_MODE=false and configure
Keycloak OIDC (planned for a future milestone).
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, health, search
from app.core.config import get_settings, Settings
from app.core.database import init_db

logger = logging.getLogger("signal_pilot")

VERSION = "1.0.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Both Docker and local commands use this same factory as the entrypoint.
    """
    if settings is None:
        settings = get_settings()

    # Initialise the SQLite database schema
    init_db(settings)

    app = FastAPI(
        title="Signal Pilot",
        description=(
            "Token-efficient BM25 search engine for AI agents and RAG pipelines. "
            "Index documents once, search many times."
        ),
        version=VERSION,
    )

    # CORS — in demo mode, allow localhost dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.demo_mode else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    from app.api import stats
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
    app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])

    # Startup / shutdown hooks
    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Signal Pilot %s starting (demo_mode=%s)", VERSION, settings.demo_mode)

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Signal Pilot shutting down")

    return app


# Module-level app instance for uvicorn/gunicorn
app = create_app()