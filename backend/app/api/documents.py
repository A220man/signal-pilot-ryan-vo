"""Document API routes: upload, list, get, delete."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.document import DocumentResponse, DocumentSummary, DocumentUpload
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

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    doc: DocumentUpload,
    service: DocumentService = Depends(get_service),
) -> DocumentResponse:
    """Upload and index a document."""
    record = service.ingest_document(
        filename=doc.filename,
        raw_content=doc.content,
        mime_type=doc.mime_type,
    )
    return DocumentResponse(**record)


@router.post("/file", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_service),
) -> DocumentResponse:
    """Upload a file from disk and index it."""
    raw_content = file.file.read()
    record = service.ingest_document(
        filename=file.filename or "unnamed",
        raw_content=raw_content,
        mime_type=file.content_type,
    )
    return DocumentResponse(**record)

@router.get("", response_model=List[DocumentSummary])
def list_documents(
    limit: int = 50,
    offset: int = 0,
    service: DocumentService = Depends(get_service),
) -> List[DocumentSummary]:
    """List indexed documents with pagination."""
    docs = service.list_documents(limit=limit, offset=offset)
    return [DocumentSummary(**doc) for doc in docs]


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    service: DocumentService = Depends(get_service),
) -> DocumentResponse:
    """Retrieve a document by ID."""
    doc = service.get_document(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    return DocumentResponse(**doc)


@router.delete("/{doc_id}", response_model=None)
def delete_document(
    doc_id: int,
    service: DocumentService = Depends(get_service),
) -> Response:
    """Delete a document by ID."""
    if not service.delete_document(doc_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)