"""API routes for index statistics and monitoring."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.services.search_engine import BM25SearchEngine


router = APIRouter()


def get_service(settings: Settings = Depends(get_settings)):
    db = get_db(settings)
    try:
        yield BM25SearchEngine(db, settings)
    finally:
        db.close()


class IndexStats(BaseModel):
    """Index statistics for monitoring and evaluation."""
    document_count: int
    total_tokens: int
    unique_terms: int
    avg_doc_length: float
    max_doc_length: int
    min_doc_length: int


@router.get("", response_model=IndexStats)
def get_stats(engine: BM25SearchEngine = Depends(get_service)) -> IndexStats:
    """Return index statistics for monitoring and AI/ML evaluation."""
    db = engine.db

    doc_stats = db.execute(
        "SELECT COUNT(*) as n, "
        "COALESCE(SUM(content_length), 0) as total_tokens, "
        "COALESCE(AVG(content_length), 0) as avg_length, "
        "COALESCE(MAX(content_length), 0) as max_length, "
        "COALESCE(MIN(content_length), 0) as min_length "
        "FROM documents"
    ).fetchone()

    unique_terms = db.execute(
        "SELECT COUNT(DISTINCT token) as n FROM inverted_index"
    ).fetchone()

    return IndexStats(
        document_count=doc_stats["n"],
        total_tokens=doc_stats["total_tokens"],
        unique_terms=unique_terms["n"],
        avg_doc_length=round(doc_stats["avg_length"], 2),
        max_doc_length=doc_stats["max_length"],
        min_doc_length=doc_stats["min_length"],
    )