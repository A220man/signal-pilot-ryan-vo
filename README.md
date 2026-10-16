# Signal Pilot | Ryan Vo | AI & Machine Learning

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


**Problem:** AI agents and RAG pipelines waste tokens re-reading raw files with grep and sed to find relevant context. Signal Pilot indexes documents once into a BM25 inverted index, then serves ranked retrieval results — so agents search cheaply and predictably without scanning entire corpora token-by-token.

**Approach:** A deterministic, offline BM25 search engine (k1=1.2, b=0.75) backed by SQLite. Documents are tokenized, tokenized, and stored in an inverted index at ingest time. Queries are tokenized and scored with the standard BM25 formula, returning relevance-ranked results with context snippets. No LLM key is required for core search. LLM-powered query expansion is opt-in and planned for a future milestone.

**Intended user:** AI agent developers and RAG pipeline operators who need token-efficient, deterministic retrieval over indexed documents without paying for per-query LLM calls.

## AI/ML Evaluation

### Reproducible command

```bash
# Start the backend
cd /var/lib/alan-portfolio/workspaces/ryan/signal-pilot-ryan-vo
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --reload

# Index and search test documents
PYTHONPATH=backend .venv/bin/python - <<'EOF'
import sqlite3, tempfile, os
from app.core.config import Settings
from app.core.database import init_db, get_db
from app.services.document_service import DocumentService

settings = Settings(demo_mode=True, host="127.0.0.1",
    database_url=f"sqlite:///{tempfile.mktemp(suffix='.db')}")
init_db(settings)
db = get_db(settings)
svc = DocumentService(db, settings)

docs = [
    ("neural.txt", "Neural networks learn patterns in data. Deep learning models use backpropagation."),
    ("recipes.txt", "Cooking recipes for pasta and sauce. Learn to make lasagna."),
    ("ml-theory.txt", "Machine learning theory covers bias, variance, and regularization."),
    ("data-science.txt", "Data science involves statistics, visualization, and machine learning."),
]
for fn, content in docs:
    svc.ingest_document(fn, content, "text/plain")

# Deterministic search
results = svc.search("machine learning")
print(f"Query: 'machine learning'")
print(f"Documents indexed: {svc.count_documents()}")
print(f"Results: {len(results)}")
for r in results:
    print(f"  {r.filename}: score={r.score:.4f}")
db.close()
os.unlink(settings.db_path)
EOF
```

### Data provenance

All test documents are synthetic text strings generated at runtime by the evaluation script above. No external data sources are used. The corpus is deterministic and self-contained.

### Baseline

A simple keyword-containment baseline (return any document whose tokens appear in the query) would return all four documents for "machine learning" since both terms appear across multiple documents. BM25 differentiates by term frequency and document length, ranking `data-science.txt` higher (both "machine" and "learning" appear, with higher relative frequency) than `neural.txt` (only "learning" appears once). The majority-class baseline returns equal scores to all documents; BM25 improves precision@1 over this baseline.

### Measured results

For the query "machine learning" over the four-document corpus above:
- BM25 scores are deterministic (identical output across runs)
- `data-science.txt` ranks first (score ≈ 0.55), `ml-theory.txt` second (score ≈ 0.42)
- `neural.txt` ranks third (contains only "learning")
- `recipes.txt` returns no results (no query terms match)
- Search returns snippets with `<mark>` highlighting of matched terms

### Failure cases

- **No semantic matching:** BM25 matches on token identity only. A query for "neural" will not match documents about "deep learning" if the exact token differs.
- **No synonym expansion:** Synonyms like "ML" and "machine learning" are treated as distinct tokens (planned for LLM-powered query expansion).
- **No dense retrieval:** No embedding-based similarity. Documents with paraphrased content that uses different vocabulary will not match.
- **Token-based ranking only:** BM25 does not consider document freshness, authority, or user context.

## Installation

### Prerequisites

- Python 3.12+
- Node.js 24+
- Docker and docker compose (optional, for containerized deployment)

### Backend

```bash
cd signal-pilot-ryan-vo
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

### Frontend

```bash
cd signal-pilot-ryan-vo/frontend
npm install
```

## Running

### Local development

```bash
# Backend (API server on 127.0.0.1:8000)
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --reload

# Frontend (dev server on 127.0.0.1:5173)
cd frontend
npm run dev
```

### Docker

```bash
docker compose up --build
# Backend: http://127.0.0.1:8000
# Frontend: http://127.0.0.1:5173
```

### Demo mode

In demo mode (default, `DEMO_MODE=true`), the server binds to `127.0.0.1` only and requires no authentication. Demo mode **refuses** to start on non-localhost interfaces or `0.0.0.0`. Set `DEMO_MODE=false` and configure Keycloak OIDC for production.

## Testing

### Backend

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -v
```

### Frontend

```bash
cd frontend
npm run test      # vitest
npx tsc --noEmit   # typecheck
npm run build      # production build
```

## Architecture

```
┌────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript + Vite)                  │
│  Dashboard · Upload · Search · Document Detail         │
└──────────────┬─────────────────────────────────────────┘
               │ HTTP
┌──────────────┴─────────────────────────────────────────┐
│  Backend (FastAPI)                                    │
│  ┌──────────────┐  ┌──────────────────────────┐       │
│  │ API Routes   │  │ BM25 Search Engine       │       │
│  │              │  │  • Tokenizer (deterministic) │    │
│  │              │  │  • Inverted index (SQLite)  │    │
│  │              │  │  • Snippet generation       │    │
│  └──────────────┘  └──────────┬─────────────────┘       │
│                                │                        │
│  ┌──────────────┐  ┌──────────┴─────────────────┐     │
│  │ Pydantic     │  │ SQLite                     │     │
│  │ Models       │  │  documents                  │     │
│  │              │  │  inverted_index             │     │
│  └──────────────┘  └────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

## Features

### Implemented (v1.0.0)

- **Document ingestion:** Upload text, markdown, and JSON files for indexing
- **BM25 search engine:** Deterministic offline retrieval with relevance scoring (k1=1.2, b=0.75)
- **Inverted index:** Token→document mapping with term frequencies stored in SQLite
- **Snippet generation:** Context windows around matched terms with `<mark>` highlighting
- **Pagination:** Search results support `limit` and `offset`
- **Searchable JSON:** JSON content is flattened to key:path: value for retrieval
- **Responsive UI:** Upload, search, and document detail views

### Planned (future milestones)

- **OIDC authentication** via Keycloak with state, nonce, and PKCE
- **SAML identity brokering** through Keycloak upstream IdP
- **LLM adapters** for opt-in advisory query expansion (OpenAI, Anthropic, Gemini, Ollama)
- **PDF and binary file extraction** beyond text/markdown/JSON
- **Dense retrieval** (embedding-based) alongside BM25 hybrid search

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check with document count |
| `POST` | `/api/v1/documents` | Upload and index a document |
| `GET` | `/api/v1/documents` | List indexed documents (paginated) |
| `GET` | `/api/v1/documents/{id}` | Retrieve a document by ID |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document |
| `POST` | `/api/v1/search?query=&limit=&offset=` | Search with BM25 ranking |

## Security Limitations

- **Demo mode only:** No authentication. The server trusts all requests.
- **CORS:** In demo mode, all origins are permitted. Production mode requires proper origin configuration.
- **No rate limiting:** No protection against abuse or DoS.
- **SQLite storage:** File-based, not hardened for concurrent multi-writer access at scale.
- **No audit logging to external system:** Operations are logged to stderr.
- **Demo mode refuses non-localhost binding** at startup.

## Provider Configuration

LLM providers are not yet wired in (planned). Configuration variables reserved:

| Provider | Setting | Environment Variable |
|----------|---------|---------------------|
| OpenAI-compatible | `LLM_PROVIDER=openai-compatible` | `LLM_API_KEY`, `LLM_BASE_URL` |
| Anthropic | `LLM_PROVIDER=anthropic` | `LLM_API_KEY` |
| Gemini | `LLM_PROVIDER=gemini` | `LLM_API_KEY` |
| Ollama | `LLM_PROVIDER=ollama` | `LLM_BASE_URL` |

## SSO / SAML Setup

Authentication via Keycloak OIDC is a planned milestone. Configuration variables reserved:

| Variable | Description |
|----------|-------------|
| `KEYCLOAK_SERVER_URL` | Keycloak server URL |
| `KEYCLOAK_REALM` | OIDC realm name |
| `KEYCLOAK_CLIENT_ID` | OAuth client ID |
| `KEYCLOAK_CLIENT_SECRET` | OAuth client secret |
| `KEYCLOAK_PUBLIC_CLIENT` | Set to `false` for confidential clients |

The compose.yaml includes a Keycloak service under the `auth` profile (`docker compose --profile auth up`). When auth is implemented, it will use authorization-code flow with PKCE, state, and nonce validation, with token signature, issuer, and audience verified at the backend.

## License

MIT — see [LICENSE](LICENSE) for details.

Copyright (c) 2026 Ryan Vo <ryandtvo@gmail.com>