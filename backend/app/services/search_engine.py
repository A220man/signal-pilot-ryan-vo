"""BM25 search engine: inverted index storage, deterministic ranking, snippets."""
from __future__ import annotations
import html
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.config import Settings
from app.services.tokenizer import tokenize


@dataclass
class SearchResult:
    """A single ranked search result with a context snippet."""
    doc_id: int
    filename: str
    score: float
    snippet: str
    content_length: int
    created_at: str


class BM25SearchEngine:
    """Deterministic BM25 search engine backed by SQLite.

    Uses the standard BM25 formula with configurable k1 and b parameters.
    All computations are offline and deterministic — no LLM key required.
    """

    def __init__(self, db: sqlite3.Connection, settings: Settings) -> None:
        self.db = db
        self.k1: float = settings.bm25_k1
        self.b: float = settings.bm25_b

    # ------------------------------------------------------------------
    # Indexing

    def index_document(
        self,
        filename: str,
        content: str,
        file_size: int,
        mime_type: Optional[str] = None,
    ) -> int:
        """Tokenize and store a document, building its inverted index entries.

        Returns the new document ID.
        """
        tokens = tokenize(content)
        token_freqs = _term_frequencies(tokens)
        doc_length = len(tokens)

        created_at = datetime.now(timezone.utc).isoformat()

        # Insert document row
        cursor = self.db.execute(
            "INSERT INTO documents (filename, content, content_length, file_size, mime_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (filename, content, doc_length, file_size, mime_type, created_at),
        )
        doc_id = cursor.lastrowid

        # Insert inverted index entries
        self.db.executemany(
            "INSERT INTO inverted_index (token, doc_id, frequency) VALUES (?, ?, ?)",
            [(token, doc_id, freq) for token, freq in token_freqs.items()],
        )
        return doc_id

    # ------------------------------------------------------------------
    # Search

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        mime_type: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search documents by BM25 ranking for *query*.

        Returns a list of SearchResult objects ordered by descending score.
        Handles empty queries, zero documents, and missing terms gracefully.
        Optionally filters by mime_type.
        """
        tokens = tokenize(query)
        if not tokens:
            return []

        total_docs = self._get_total_docs()
        if total_docs == 0:
            return []

        avgdl = self._get_avg_doc_length()
        if avgdl == 0:
            return []

        # Compute IDF for each query term
        idf_values: Dict[str, float] = {}
        for token in tokens:
            n = self._get_term_doc_count(token)
            idf = math.log((total_docs - n + 0.5) / (n + 0.5) + 1.0)
            idf_values[token] = idf

        # Gather matching documents and their term frequencies
        doc_scores: Dict[int, float] = {}
        for token in tokens:
            idf = idf_values[token]
            rows = self.db.execute(
                "SELECT doc_id, frequency FROM inverted_index WHERE token = ?",
                (token,),
            ).fetchall()
            for row in rows:
                doc_id = row["doc_id"]
                tf = row["frequency"]
                doc_length = self._get_doc_length(doc_id)
                norm = 1.0 - self.b + self.b * doc_length / avgdl
                score = idf * (tf * (self.k1 + 1)) / (tf + self.k1 * norm)
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score

        # Apply mime_type filter if provided
        if mime_type is not None:
            placeholders = ",".join("?" * len(doc_scores)) if doc_scores else "NULL"
            filtered_ids = set()
            if doc_scores:
                rows = self.db.execute(
                    f"SELECT id FROM documents WHERE id IN ({placeholders}) AND mime_type = ?",
                    list(doc_scores.keys()) + [mime_type],
                ).fetchall()
                filtered_ids = {row["id"] for row in rows}
                doc_scores = {k: v for k, v in doc_scores.items() if k in filtered_ids}

        # Sort by score descending, apply pagination
        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        paged = ranked[offset:offset + limit]

        # Build result objects
        results: List[SearchResult] = []
        for doc_id, score in paged:
            doc = self.db.execute(
                "SELECT id, filename, content, content_length, created_at FROM documents WHERE id = ?",
                (doc_id,),
            ).fetchone()
            if doc is None:
                continue
            snippet = self._generate_snippet(doc["content"], tokens)
            results.append(SearchResult(
                doc_id=doc["id"],
                filename=doc["filename"],
                score=round(score, 4),
                snippet=snippet,
                content_length=doc["content_length"],
                created_at=doc["created_at"],
            ))

        return results

    # ------------------------------------------------------------------
    # Document detail

    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Retrieve a single document by ID. Returns None if not found."""
        row = self.db.execute(
            "SELECT id, filename, content, content_length, file_size, mime_type, created_at "
            "FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def list_documents(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """List documents with pagination, most recent first."""
        rows = self.db.execute(
            "SELECT id, filename, content_length, file_size, mime_type, created_at "
            "FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document and its index entries. Returns True if deleted."""
        cursor = self.db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return cursor.rowcount > 0

    def document_count(self) -> int:
        """Return the total number of indexed documents."""
        return self.db.execute("SELECT COUNT(*) as n FROM documents").fetchone()["n"]

    # ------------------------------------------------------------------
    # Internal helpers

    def _get_total_docs(self) -> int:
        return self.db.execute("SELECT COUNT(*) as n FROM documents").fetchone()["n"]

    def _get_avg_doc_length(self) -> float:
        result = self.db.execute(
            "SELECT COALESCE(AVG(content_length), 0) as avgdl FROM documents"
        ).fetchone()
        return result["avgdl"] or 0.0

    def _get_doc_length(self, doc_id: int) -> int:
        result = self.db.execute(
            "SELECT content_length FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return result["content_length"] if result else 0

    def _get_term_doc_count(self, token: str) -> int:
        return self.db.execute(
            "SELECT COUNT(DISTINCT doc_id) as n FROM inverted_index WHERE token = ?",
            (token,),
        ).fetchone()["n"]

    def _generate_snippet(self, content: str, query_tokens: List[str], window: int = 75) -> str:
        """Generate a snippet showing the first query-term hit with context.

        Highlights matched terms and truncates with ellipsis when the context
        is longer than the window.
        """
        if not content:
            return ""

        content_lower = content.lower()
        first_pos = -1
        for token in query_tokens:
            pos = content_lower.find(token)
            if pos != -1 and (first_pos == -1 or pos < first_pos):
                first_pos = pos

        if first_pos == -1:
            # No exact token boundary match — show start of content
            snippet_text = content[:window * 4]
        else:
            start = max(0, first_pos - window)
            end = min(len(content), first_pos + len(query_tokens[0]) + window)
            snippet_text = content[start:end]
            if start > 0:
                snippet_text = "..." + snippet_text
            if end < len(content):
                snippet_text = snippet_text + "..."

        # Highlight query terms
        result = html.escape(snippet_text)
        for token in query_tokens:
            # Highlight whole-token matches, case-insensitive
            pattern = re.compile(r'\b(' + re.escape(token) + r')\b', re.IGNORECASE)
            result = pattern.sub(r'<mark>\1</mark>', result)

        return result


def _term_frequencies(tokens: List[str]) -> Dict[str, int]:
    """Compute term→frequency mapping for a token list."""
    freq: Dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return freq