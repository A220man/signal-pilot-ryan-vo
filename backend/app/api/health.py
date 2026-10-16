"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.document import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Health check: returns service status and document count."""
    db = get_db(settings)
    try:
        count = db.execute("SELECT COUNT(*) as n FROM documents").fetchone()["n"]
    finally:
        db.close()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        demo_mode=settings.demo_mode,
        document_count=count,
    )