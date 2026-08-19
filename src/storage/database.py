"""
SQLite Database Connection and Schema Management (FR-5).
"""

import sqlite3
from pathlib import Path
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger("database")

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    remote_flag INTEGER NOT NULL DEFAULT 0,
    url TEXT NOT NULL,
    posted_date TEXT,
    description TEXT,
    tags TEXT,
    dedupe_hash TEXT NOT NULL UNIQUE,
    first_seen TEXT NOT NULL,
    notified INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_jobs_dedupe_hash ON jobs (dedupe_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs (source);
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs (first_seen);
CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs (notified);
"""


class DatabaseManager:
    """Manages SQLite database connections, initialization, and transactions."""

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")  # Better concurrency and durability
        return conn

    def _init_db(self) -> None:
        """Initializes database schema and indices."""
        try:
            with self.get_connection() as conn:
                conn.executescript(CREATE_TABLES_SQL)
                conn.commit()
            logger.debug(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database at {self.db_path}: {e}")
            raise e
