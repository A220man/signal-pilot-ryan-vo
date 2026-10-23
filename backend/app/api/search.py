"""Search API routes: BM25-ranked search with pagination."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.document import SearchResponse
from app.services.document_service import DocumentService
router = APIRouter()


def get_service(
    settings: Settings = Depends(get_settings),
):
    """Dependency: DocumentService with DB connection that closes after the request."""
    db = get_db(settings)
    try:
        yield DocumentService(db, settings)
    finally:
        db.close()


@router.post("", response_model=SearchResponse)
def search(
    query: str,
    limit: int = 20,
    offset: int = 0,
    mime_type: Optional[str] = None,
    service: DocumentService = Depends(get_service),
) -> SearchResponse:
    """Search indexed documents with BM25 ranking.

    The query is tokenized and matched against the inverted index.
    Results are ranked by BM25 relevance score (descending).
    Optionally filter by mime_type.
    """
    results = service.search(query=query, limit=limit, offset=offset, mime_type=mime_type)
    # Count total matching docs for pagination metadata
    total = _count_matching(service, query, mime_type)
    applied_filters = {}
    if mime_type:
        applied_filters["mime_type"] = mime_type
    return SearchResponse(
        query=query,
        total=total,
        offset=offset,
        limit=min(limit, service.settings.max_search_limit),
        results=[
            {
                "doc_id": r.doc_id,
                "filename": r.filename,
                "score": r.score,
                "snippet": r.snippet,
                "content_length": r.content_length,
                "created_at": r.created_at,
            }
            for r in results
        ],
        applied_filters=applied_filters,
    )


def _count_matching(service: DocumentService, query: str, mime_type: Optional[str] = None) -> int:
    """Count total documents that match any query token (approximate total)."""
    from app.services.tokenizer import tokenize
    tokens = tokenize(query)
    if not tokens:
        return 0
    placeholders = ",".join("?" * len(tokens))
    if mime_type:
        row = service.db.execute(
            f"SELECT COUNT(DISTINCT doc_id) as n FROM inverted_index WHERE token IN ({placeholders}) "
            "AND doc_id IN (SELECT id FROM documents WHERE mime_type = ?)",
            tokens + [mime_type],
        ).fetchone()
    else:
        row = service.db.execute(
            f"SELECT COUNT(DISTINCT doc_id) as n FROM inverted_index WHERE token IN ({placeholders})",
            tokens,
        ).fetchone()
    return row["n"] if row else 0