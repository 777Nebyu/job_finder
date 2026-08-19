"""
SQLite Database Connection and Schema Management (FR-5).
"""

import sqlite3
from pathlib import Path
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
    deadline TEXT,
    description TEXT,
    tags TEXT,
    dedupe_hash TEXT NOT NULL UNIQUE,
    first_seen TEXT NOT NULL,
    notified INTEGER NOT NULL DEFAULT 0
);
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
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        """Initializes database schema, columns, and indices with safe auto-migration."""
        try:
            with self.get_connection() as conn:
                # 1. Create table if not exists
                conn.execute(CREATE_TABLES_SQL)

                # 2. Check and migrate columns
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(jobs);")
                columns = [col["name"] for col in cursor.fetchall()]
                if "deadline" not in columns:
                    conn.execute("ALTER TABLE jobs ADD COLUMN deadline TEXT;")

                # 3. Create indices
                conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_dedupe_hash ON jobs (dedupe_hash);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs (source);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs (first_seen);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs (deadline);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs (notified);")
                conn.commit()
            logger.debug(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database at {self.db_path}: {e}")
            raise e
