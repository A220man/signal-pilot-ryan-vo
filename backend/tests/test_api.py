"""Integration tests for the API layer — cross the real HTTP boundary."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.core.config as config_mod
from app.core.config import Settings
from app.core.database import drop_db, init_db
from app.main import create_app


@pytest.fixture
def temp_settings(tmp_path):
    """Settings pointing at a temp DB with demo mode on."""
    db_path = tmp_path / "test_api.db"
    return Settings(
        database_url=f"sqlite:///{db_path}",
        demo_mode=True,
        host="127.0.0.1",
        app_version="1.0.0",
    )


@pytest.fixture
def client(temp_settings):
    """TestClient with a fresh initialized database and overridden settings dependency."""
    # Reset the singleton so no stale settings leak from other test modules
    config_mod._settings = None
    init_db(temp_settings)
    app = create_app(temp_settings)
    # Override get_settings so routes use our test settings, not the singleton
    app.dependency_overrides[config_mod.get_settings] = lambda: temp_settings
    with TestClient(app) as c:
        yield c
    drop_db(temp_settings)
    app.dependency_overrides.clear()
    config_mod._settings = None

class TestHealthEndpoint:
    def test_health_returns_status(self, client):
        """Health endpoint returns OK status with version and demo flag."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["demo_mode"] is True

    def test_health_reports_document_count(self, client):
        """Health endpoint reports the correct document count."""
        client.post("/api/v1/documents", json={
            "filename": "a.txt", "content": "hello world"
        })
        resp = client.get("/api/v1/health")
        assert resp.json()["document_count"] == 1


class TestDocumentUpload:
    def test_upload_creates_document(self, client):
        """POST /documents creates and returns a document record."""
        resp = client.post("/api/v1/documents", json={
            "filename": "notes.txt",
            "content": "machine learning is fascinating",
            "mime_type": "text/plain",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "notes.txt"
        assert data["content"] == "machine learning is fascinating"
        assert "id" in data
        assert "created_at" in data

    def test_upload_rejects_invalid_filename(self, client):
        """Uploading with a path separator in filename fails validation."""
        resp = client.post("/api/v1/documents", json={
            "filename": "../etc/passwd",
            "content": "malicious",
        })
        assert resp.status_code == 422

    def test_upload_rejects_empty_content(self, client):
        """Uploading with empty content fails validation."""
        resp = client.post("/api/v1/documents", json={
            "filename": "empty.txt",
            "content": "",
        })
        assert resp.status_code == 422

    def test_upload_requires_filename(self, client):
        """Missing filename fails validation."""
        resp = client.post("/api/v1/documents", json={
            "content": "some content",
        })
        assert resp.status_code == 422

    def test_multiple_uploads(self, client):
        """Multiple documents can be uploaded independently."""
        for name, content in [("a.txt", "alpha beta"), ("b.txt", "gamma delta")]:
            resp = client.post("/api/v1/documents", json={
                "filename": name, "content": content
            })
            assert resp.status_code == 201
        assert client.get("/api/v1/health").json()["document_count"] == 2


class TestDocumentRetrieval:
    def test_get_document_by_id(self, client):
        """GET /documents/{id} returns the stored document."""
        resp = client.post("/api/v1/documents", json={
            "filename": "test.txt", "content": "retrievable content here"
        })
        doc_id = resp.json()["id"]
        resp = client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.txt"
        assert "retrievable" in data["content"]

    def test_get_document_not_found(self, client):
        """GET /documents/{id} returns 404 for missing document."""
        resp = client.get("/api/v1/documents/99999")
        assert resp.status_code == 404


class TestDocumentListing:
    def test_list_documents_empty(self, client):
        """Empty index returns empty list."""
        resp = client.get("/api/v1/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_documents_populated(self, client):
        """List returns all documents."""
        client.post("/api/v1/documents", json={"filename": "a.txt", "content": "hello"})
        client.post("/api/v1/documents", json={"filename": "b.txt", "content": "world"})
        resp = client.get("/api/v1/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all("id" in d for d in data)


class TestDeleteDocument:
    def test_delete_existing(self, client):
        """Deleting an existing document succeeds."""
        resp = client.post("/api/v1/documents", json={
            "filename": "delete.txt", "content": "to be removed"
        })
        doc_id = resp.json()["id"]
        resp = client.delete(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 204
        # Verify gone
        resp = client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 404

    def test_delete_nonexistent_404(self, client):
        """Deleting non-existent document returns 404."""
        resp = client.delete("/api/v1/documents/99999")
        assert resp.status_code == 404


class TestSearchAPI:
    def test_search_returns_ranked_results(self, client):
        """Search returns documents matching query terms, ranked by BM25."""
        client.post("/api/v1/documents", json={
            "filename": "ml.txt", "content": "machine learning algorithms"
        })
        client.post("/api/v1/documents", json={
            "filename": "food.txt", "content": "cooking recipes and taste"
        })
        resp = client.post("/api/v1/search/?query=machine+learning&limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["results"]) >= 1
        assert data["results"][0]["filename"] == "ml.txt"
        assert data["results"][0]["score"] > 0

    def test_search_empty_query(self, client):
        """Search with only stop words returns empty results."""
        client.post("/api/v1/documents", json={
            "filename": "a.txt", "content": "hello world"
        })
        resp = client.post("/api/v1/search/?query=the+a+an&limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_no_matches(self, client):
        """Search with non-matching terms returns empty results."""
        client.post("/api/v1/documents", json={
            "filename": "a.txt", "content": "hello world"
        })
        resp = client.post("/api/v1/search/?query=nonexistent+terms&limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_search_response_includes_metadata(self, client):
        """Search response includes query, pagination, and results."""
        client.post("/api/v1/documents", json={
            "filename": "a.txt", "content": "alpha beta gamma"
        })
        resp = client.post("/api/v1/search/?query=alpha+beta&limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "alpha beta"
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert isinstance(data["total"], int)

    def test_search_pagination(self, client):
        """Search respects limit and offset for pagination."""
        # Upload a document with many unique terms for matching
        client.post("/api/v1/documents", json={
            "filename": "a.txt",
            "content": "shared common unique terms here for testing pagination thoroughly",
        })
        client.post("/api/v1/documents", json={
            "filename": "b.txt",
            "content": "shared common other unique terms here for testing pagination",
        })
        resp = client.post("/api/v1/search/?query=shared+common&limit=1&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) <= 1

class TestStatsAPI:
    def test_stats_empty_index(self, client):
        """Stats endpoint returns zeros on empty index."""
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_count"] == 0
        assert data["unique_terms"] == 0

    def test_stats_after_ingest(self, client):
        """Stats reflect indexed documents."""
        client.post("/api/v1/documents", json={
            "filename": "a.txt", "content": "machine learning algorithms"
        })
        client.post("/api/v1/documents", json={
            "filename": "b.txt", "content": "data science python"
        })
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_count"] == 2
        assert data["total_tokens"] > 0
        assert data["unique_terms"] > 0
        assert data["max_doc_length"] >= data["min_doc_length"]


class TestFileUpload:
    def test_upload_file_creates_document(self, client):
        """Multipart file upload creates and indexes a document."""
        resp = client.post(
            "/api/v1/documents/file",
            files={"file": ("notes.txt", "machine learning models", "text/plain")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "notes.txt"

    def test_upload_json_file(self, client):
        """JSON file upload is flattened and searchable."""
        json_content = '{"status": "error", "message": "timeout occurred"}'
        resp = client.post(
            "/api/v1/documents/file",
            files={"file": ("error.json", json_content, "application/json")},
        )
        assert resp.status_code == 201
        # Verify search works on the flattened JSON
        resp = client.post("/api/v1/search/?query=timeout&limit=10&offset=0")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1