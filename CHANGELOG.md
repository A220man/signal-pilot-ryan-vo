# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to Signal Pilot are documented here.

## [1.0.0] — 2026-10-16

### Added
- FastAPI backend with SQLite persistent storage
- BM25 search engine with inverted index and deterministic ranking
- Document ingestion API with tokenization (lowercase, alphanumeric)
- Snippet generation with query term context highlighting
- Search API with pagination and relevance-based result ordering
- React + TypeScript frontend with Vite dev server
- Typed API client derived from actual backend routes
- Upload, search, and document detail workflows
- Loading, error, and empty states in UI
- Docker backend/frontend Dockerfiles with nonroot users
- docker-compose.yaml with persistent volumes and Keycloak (auth pending)
- GitHub Actions CI workflow (backend pytest, frontend build/test)
- Portfolio JSON, README, and this changelog

## [1.0.1] — 2026-10-23

### Added
- MIME type filter for search API (`mime_type` query parameter)
- BM25 search engine filters results by mime_type
- Frontend SearchBar with MIME type dropdown filter (Text, Markdown, JSON, All)
- Filter integrates with pagination (limit/offset)
- Applied filters returned in search response metadata

### Testing
- Backend: 2 new search engine tests, 2 new API tests for mime_type filter
- Frontend: 6 new SearchBar component tests with filter interaction