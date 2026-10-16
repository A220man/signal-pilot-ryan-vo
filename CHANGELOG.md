# Changelog

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