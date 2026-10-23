"""Document service: ingestion, text extraction, and search orchestration."""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from app.core.config import Settings
from app.services.search_engine import BM25SearchEngine, SearchResult


class DocumentService:
    """High-level service combining ingestion and search operations."""

    def __init__(self, db: sqlite3.Connection, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.engine = BM25SearchEngine(db, settings)

    def extract_text(self, filename: str, raw_content: bytes | str) -> str:
        """Extract plain text from uploaded content.

        Supports plain text (.txt), markdown (.md), and JSON (.json).
        For JSON, the extracted text is a flattened key:path representation.
        """
        if isinstance(raw_content, bytes):
            content = raw_content.decode("utf-8", errors="replace")
        else:
            content = raw_content

        ext = _get_extension(filename)
        if ext == ".json":
            return self._flatten_json(content)
        return content

    def ingest_document(
        self,
        filename: str,
        raw_content: bytes | str,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract text, tokenize, and store a document with its inverted index.

        Returns the stored document record.
        """
        content = self.extract_text(filename, raw_content)

        if isinstance(raw_content, bytes):
            file_size = len(raw_content)
        else:
            file_size = len(raw_content.encode("utf-8"))

        doc_id = self.engine.index_document(
            filename=filename,
            content=content,
            file_size=file_size,
            mime_type=mime_type,
        )

        return self.engine.get_document(doc_id)

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        mime_type: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search documents with BM25 ranking."""
        limit = min(limit, self.settings.max_search_limit)
        return self.engine.search(query, limit=limit, offset=offset, mime_type=mime_type)

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        return self.engine.get_document(doc_id)

    def list_documents(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List documents with pagination."""
        return self.engine.list_documents(limit=limit, offset=offset)

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document and its index entries."""
        return self.engine.delete_document(doc_id)

    def count_documents(self) -> int:
        """Return the total document count."""
        return self.engine.document_count()

    def _flatten_json(self, content: str) -> str:
        """Flatten JSON into a readable text representation."""
        import json
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content
        lines: List[str] = []

        def _walk(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else str(key)
                    _walk(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    _walk(item, new_path)
            else:
                text = str(obj) if obj is not None else "null"
                lines.append(f"{path}: {text}" if path else text)

        _walk(data)
        return "\n".join(lines)


def _get_extension(filename: str) -> str:
    """Return the lowercase file extension including the dot, or empty string."""
    dot = filename.rfind(".")
    if dot == -1:
        return ""
    return filename[dot:].lower()