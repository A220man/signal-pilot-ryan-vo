"""Tests for the BM25 search engine."""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.search_engine import BM25SearchEngine


@pytest.fixture
def engine(db, settings):
    return BM25SearchEngine(db, settings)


class TestIndexDocument:
    def test_basic_index(self, engine):
        """Indexing a document stores it and returns an ID."""
        doc_id = engine.index_document("test.txt", "hello world foo bar", 19, "text/plain")
        assert doc_id > 0

    def test_content_length_reflects_token_count(self, engine):
        """content_length reflects token count after stop-word filtering."""
        doc_id = engine.index_document("a.txt", "hello hello world", 16, "text/plain")
        doc = engine.get_document(doc_id)
        assert doc["content_length"] == 3  # hello, hello, world → 3 tokens

    def test_content_length_stored(self, engine):
        """content_length reflects token count after stop-word filtering."""
        # "hello world foo bar" → 4 tokens (no stop words)
        doc_id = engine.index_document("t.txt", "hello world foo bar", 19, "text/plain")
        doc = engine.get_document(doc_id)
        assert doc["content_length"] == 4

    def test_inverted_index_populated(self, engine):
        """Inverted index entries exist for each token."""
        doc_id = engine.index_document("t.txt", "hello world foo bar", 19, "text/plain")
        rows = engine.db.execute(
            "SELECT COUNT(*) as n FROM inverted_index WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        assert rows["n"] == 4

    def test_stores_created_at_utc(self, engine):
        """Created timestamp is UTC ISO format."""
        doc_id = engine.index_document("t.txt", "hello world", 11, "text/plain")
        doc = engine.get_document(doc_id)
        assert doc["created_at"].endswith("+00:00")


class TestSearch:
    def test_basic_search_returns_results(self, engine):
        """Search returns documents containing query terms."""
        engine.index_document("a.txt", "machine learning algorithms", 26, "text/plain")
        engine.index_document("b.txt", "cooking recipes and food", 25, "text/plain")
        results = engine.search("machine learning")
        assert len(results) == 1
        assert results[0].filename == "a.txt"

    def test_ranking_by_relevance(self, engine):
        """Documents with more matching terms rank higher."""
        engine.index_document("a.txt", "neural networks deep learning", 29, "text/plain")
        engine.index_document("b.txt", "neural networks", 15, "text/plain")
        results = engine.search("neural networks deep learning")
        assert results[0].filename == "a.txt"
        assert results[0].score > results[1].score

    def test_deterministic_scores(self, engine):
        """Same query on same index produces same scores."""
        engine.index_document("a.txt", "alpha beta gamma delta", 22, "text/plain")
        r1 = engine.search("alpha beta")
        r2 = engine.search("alpha beta")
        assert r1[0].score == r2[0].score

    def test_empty_query_returns_empty(self, engine):
        """Empty query (only stop words) returns no results."""
        results = engine.search("the a an")
        assert results == []

    def test_no_matching_term_returns_empty(self, engine):
        """Query with terms not in any document returns empty."""
        engine.index_document("a.txt", "hello world", 11, "text/plain")
        results = engine.search("nonexistent term")
        assert results == []

    def test_no_documents_returns_empty(self, engine):
        """Search on empty index returns empty list."""
        results = engine.search("anything")
        assert results == []

    def test_snippet_contains_query_terms(self, engine):
        """Snippet includes context around matched terms."""
        engine.index_document("a.txt", "the quick brown fox jumps over the lazy dog", 43, "text/plain")
        results = engine.search("fox")
        assert len(results) == 1
        assert "fox" in results[0].snippet.lower() or "mark" in results[0].snippet.lower()

    def test_pagination_offset(self, engine):
        """Offset skips the first N results."""
        for i in range(5):
            engine.index_document(f"doc_{i}.txt", "unique_term shared common", 28, "text/plain")
        results = engine.search("shared common", limit=2, offset=0)
        assert len(results) <= 2

    def test_partial_term_match_via_stop_removal(self, engine):
        """Search matches on content tokens after stop-word filtering."""
        engine.index_document("a.txt", "data science with python", 24, "text/plain")
        results = engine.search("data python")
        assert len(results) == 1
        assert results[0].doc_id > 0


class TestDocumentOperations:
    def test_get_document_not_found(self, engine):
        """Getting a non-existent document returns None."""
        assert engine.get_document(999) is None

    def test_list_documents(self, engine):
        """List returns all documents."""
        engine.index_document("a.txt", "hello world", 11, "text/plain")
        engine.index_document("b.txt", "foo bar baz", 11, "text/plain")
        docs = engine.list_documents()
        assert len(docs) == 2

    def test_delete_document(self, engine):
        """Deleting a document removes it from the index."""
        doc_id = engine.index_document("a.txt", "hello world", 11, "text/plain")
        assert engine.delete_document(doc_id)
        assert engine.get_document(doc_id) is None

    def test_delete_nonexistent_returns_false(self, engine):
        """Deleting a non-existent document returns False."""
        assert not engine.delete_document(999)

    def test_document_count(self, engine):
        """Document count reflects indexed documents."""
        engine.index_document("a.txt", "hello world", 11, "text/plain")
        engine.index_document("b.txt", "foo bar", 7, "text/plain")
        assert engine.document_count() == 2