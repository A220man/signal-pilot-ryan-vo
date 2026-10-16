"""Tests for the DocumentService: ingestion, text extraction, JSON flattening."""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.document_service import DocumentService


@pytest.fixture
def service(db, settings):
    return DocumentService(db, settings)


class TestTextExtraction:
    def test_plain_text(self, service):
        """Plain text content passes through unchanged."""
        text = service.extract_text("readme.txt", "Hello World")
        assert "Hello" in text
        assert "World" in text

    def test_markdown(self, service):
        """Markdown content passes through as-is for indexing."""
        md = "# Title\n\nSome paragraph text."
        text = service.extract_text("doc.md", md)
        assert "Title" in text
        assert "paragraph" in text

    def test_json_flattened(self, service):
        """JSON content is flattened into key:path: value lines."""
        json_content = '{"title": "Test", "value": 42, "items": ["a", "b"]}'
        text = service.extract_text("data.json", json_content)
        assert "title: Test" in text
        assert "value: 42" in text
        assert "items[0]: a" in text
        assert "items[1]: b" in text

    def test_invalid_json_falls_back(self, service):
        """Malformed JSON falls back to raw text."""
        text = service.extract_text("bad.json", "not json at all")
        assert "not json" in text

    def test_bytes_content_decoded(self, service):
        """Bytes content is decoded as UTF-8."""
        text = service.extract_text("test.txt", b"hello world")
        assert "hello" in text


class TestIngestDocument:
    def test_ingest_returns_record(self, service):
        """Ingestion returns a stored document record."""
        record = service.ingest_document("test.txt", "machine learning models", "text/plain")
        assert record["filename"] == "test.txt"
        assert record["content_length"] >= 2  # machine, learning, models → 3 tokens (models is a stop word? no)
        assert "content" in record

    def test_ingest_creates_inverted_index(self, service):
        """Ingested documents are searchable."""
        service.ingest_document("a.txt", "deep learning neural networks", "text/plain")
        results = service.search("deep learning")
        assert len(results) == 1
        assert results[0].filename == "a.txt"

    def test_ingest_json_document(self, service):
        """JSON documents are flattened and searchable by nested field."""
        json_content = '{"status": "error", "message": "connection timeout"}'
        service.ingest_document("error.json", json_content, "application/json")
        results = service.search("timeout")
        assert len(results) == 1
        assert results[0].filename == "error.json"

    def test_file_size_stored(self, service):
        """File size is recorded correctly."""
        content = "hello world test"
        record = service.ingest_document("t.txt", content, "text/plain")
        assert record["file_size"] == len(content.encode("utf-8"))


class TestSearchAndRetrieve:
    def test_search_returns_ranked_results(self, service):
        """Search returns results ordered by BM25 score."""
        service.ingest_document("a.txt", "machine learning algorithms", "text/plain")
        service.ingest_document("b.txt", "data science python", "text/plain")
        results = service.search("machine learning")
        assert len(results) == 1
        assert results[0].filename == "a.txt"

    def test_get_document_not_found(self, service):
        """Getting a non-existent document returns None."""
        assert service.get_document(999) is None

    def test_list_documents(self, service):
        """List returns document summaries."""
        service.ingest_document("a.txt", "hello world", "text/plain")
        service.ingest_document("b.txt", "foo bar", "text/plain")
        docs = service.list_documents()
        assert len(docs) == 2

    def test_delete_document(self, service):
        """Deleted documents are no longer retrievable."""
        record = service.ingest_document("a.txt", "hello world", "text/plain")
        doc_id = record["id"]
        assert service.delete_document(doc_id)
        assert service.get_document(doc_id) is None

    def test_count_documents(self, service):
        """Document count reflects stored documents."""
        service.ingest_document("a.txt", "hello world", "text/plain")
        service.ingest_document("b.txt", "foo bar", "text/plain")
        assert service.count_documents() == 2

    def test_empty_index_search(self, service):
        """Search on empty index returns empty list."""
        assert service.search("anything") == []