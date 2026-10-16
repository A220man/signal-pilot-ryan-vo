"""SQLite database layer: connection management, schema, and migration helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import Settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT    NOT NULL,
    content       TEXT    NOT NULL,
    content_length INTEGER NOT NULL,
    file_size     INTEGER NOT NULL,
    mime_type     TEXT,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS inverted_index (
    token    TEXT    NOT NULL,
    doc_id   INTEGER NOT NULL,
    frequency INTEGER NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_inverted_token
    ON inverted_index(token);
CREATE INDEX IF NOT EXISTS idx_inverted_doc
    ON inverted_index(doc_id);
CREATE INDEX IF NOT EXISTS idx_documents_created
    ON documents(created_at DESC);
"""


def get_db(settings: Settings) -> sqlite3.Connection:
    """Return a SQLite connection with row factory. Raises if DB file is locked."""
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(settings: Settings) -> None:
    """Create tables if they do not yet exist."""
    conn = get_db(settings)
    try:
        conn.executescript(SCHEMA_SQL)
    finally:
        conn.close()


def drop_db(settings: Settings) -> None:
    """Delete the SQLite database file (used by tests)."""
    db_path = settings.db_path
    if db_path.exists():
        db_path.unlink()
        # Remove WAL/SHM sidecars
        for suffix in ("-wal", "-shm"):
            sidecar = db_path.with_name(db_path.name + suffix)
            if sidecar.exists():
                sidecar.unlink()