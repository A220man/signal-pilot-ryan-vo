"""Pytest fixtures for backend tests."""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.database import drop_db, get_db, init_db


@pytest.fixture
def temp_db_path(tmp_path):
    """Return a temporary directory path for the SQLite database."""
    db_dir = tmp_path / "data"
    db_dir.mkdir()
    return db_dir / "test.db"


@pytest.fixture
def settings(temp_db_path):
    """Return Settings pointing at a temp database with demo mode forced on."""
    return Settings(
        database_url=f"sqlite:///{temp_db_path}",
        demo_mode=True,
        host="127.0.0.1",
        port=8000,
        app_version="1.0.0",
    )


@pytest.fixture
def db(settings):
    """Provide a fresh initialized database connection for each test."""
    init_db(settings)
    conn = get_db(settings)
    yield conn
    conn.close()
    drop_db(settings)


@pytest.fixture
def clean_db(settings):
    """Provide a fresh DB and clean up afterwards (alias for clarity)."""
    init_db(settings)
    conn = get_db(settings)
    yield conn
    conn.close()
    drop_db(settings)