"""Pydantic models for documents, search requests, and responses."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class DocumentUpload(BaseModel):
    """Request model for uploading a document via JSON body."""
    filename: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    mime_type: Optional[str] = Field(default=None, max_length=128)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v or v.strip() != v or "/" in v or "\\" in v:
            raise ValueError("filename must not contain path separators or whitespace at edges")
        return v


class DocumentResponse(BaseModel):
    """Response model for a stored document."""
    id: int
    filename: str
    content: Optional[str] = None
    content_length: int
    file_size: int
    mime_type: Optional[str] = None
    created_at: str


class DocumentSummary(BaseModel):
    """Lightweight document metadata for list views."""
    id: int
    filename: str
    content_length: int
    file_size: int
    mime_type: Optional[str] = None
    created_at: str


class SearchResultItem(BaseModel):
    """A single ranked search result with snippet."""
    doc_id: int
    filename: str
    score: float
    snippet: str
    content_length: int
    created_at: str


class SearchResponse(BaseModel):
    """Search response with pagination metadata."""
    query: str
    total: int
    offset: int
    limit: int
    results: List[SearchResultItem]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    demo_mode: bool = True
    document_count: int = 0


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str