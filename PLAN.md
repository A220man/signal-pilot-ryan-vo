# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

feat-bm25-search-engine

## Roadmap

### feat-backend-core — FastAPI backend with SQLite and document ingestion API

Status: done

Acceptance:
- FastAPI app factory creates the app
- SQLite database initializes with documents and inverted_index tables
- POST /api/v1/documents uploads and indexes a document
- GET /api/v1/documents/{id} retrieves a document
- GET /api/v1/health returns status

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/api/documents.py`, `backend/app/api/health.py`, `backend/app/models/document.py`, `backend/app/services/document_service.py`, `backend/app/services/tokenizer.py`

Tests: `backend/tests/test_api.py`, `backend/tests/test_document_service.py`

### feat-bm25-search-engine — BM25 search engine with inverted index and snippet generation

Status: done

Acceptance:
- Query terms are tokenized and matched against the inverted index
- BM25 scores are computed deterministically
- Search returns ranked results with relevance scores
- Snippets are generated with query term context
- Pagination and offset work correctly
- Stats endpoint returns index statistics

Implementation: `backend/app/services/search_engine.py`, `backend/app/api/search.py`, `backend/app/api/stats.py`

Tests: `backend/tests/test_search_engine.py`, `backend/tests/test_api.py`

### feat-document-detail — Document detail retrieval with full content

Status: done

Acceptance:
- Documents can be retrieved by ID via GET /api/v1/documents/{id}
- Full content is returned
- 404 for missing documents

Implementation: `backend/app/api/documents.py`

Tests: `backend/tests/test_api.py`

### feat-frontend-search-ui — React TypeScript frontend with upload, search, and document detail

Status: done

Acceptance:
- Vite dev server starts with typed API client
- Upload form submits documents to the backend
- Search bar accepts queries and displays ranked results with snippets
- Clicking a result shows full document detail
- Loading, error, and empty states are handled

Implementation: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/types/index.ts`, `frontend/src/components/DocumentUploader.tsx`, `frontend/src/components/SearchBar.tsx`, `frontend/src/components/SearchResults.tsx`, `frontend/src/components/DocumentViewer.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/styles.css`

Tests: `frontend/src/__tests__/api.test.ts`, `frontend/src/__tests__/SearchResults.test.tsx`

### feat-packaging — Docker, CI, and project metadata

Status: done

Acceptance:
- Backend and frontend Dockerfiles build with nonroot users
- docker-compose.yaml with persistent volumes and Keycloak
- CI workflow tests backend, frontend, and builds Docker images
- portfolio.json, README, LICENSE, CHANGELOG, pyproject.toml present

Implementation: `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml`, `pyproject.toml`, `portfolio.json`, `README.md`, `CHANGELOG.md`, `.gitignore`, `.env.example`

### feat-auth-oidc — OIDC authentication through Keycloak with roles and SAML brokering

Status: planned

Acceptance:
- Login redirects to Keycloak with state, nonce, and PKCE
- Tokens are validated for signature, issuer, and audience
- Viewer, analyst, admin roles enforced on data endpoints
- Explicit logout clears session
- Tests cover unauthenticated rejection and role denial

### feat-llm-adapters — LLM provider adapters for opt-in advisory explanations

Status: planned

Acceptance:
- OpenAI-compatible, Anthropic, Gemini, and Ollama adapters via httpx
- Opt-in labeled advisory explanations grounded in records
- Bounded timeouts and redacted errors

