"""
Dynamic Keyword Store for Telegram Bot Commands.
Persists user-added keywords in SQLite so they survive restarts.
"""

from datetime import datetime, timezone
from typing import List, Tuple
from src.storage.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger("dynamic_keywords")

CREATE_KEYWORDS_TABLE = """
CREATE TABLE IF NOT EXISTS dynamic_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'include',
    created_at TEXT NOT NULL
);
"""


class DynamicKeywordStore:
    """Manages persistent dynamic keywords stored in SQLite."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._init_table()

    def _init_table(self) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(CREATE_KEYWORDS_TABLE)
            conn.commit()

    def add_keyword(self, keyword: str, kind: str = "include") -> Tuple[bool, str]:
        """Add a dynamic keyword. Returns (success, message)."""
        kw = keyword.strip()
        if not kw:
            return False, "Keyword cannot be empty."

        now_str = datetime.now(timezone.utc).isoformat()
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    "INSERT INTO dynamic_keywords (keyword, kind, created_at) VALUES (?, ?, ?);",
                    (kw, kind.lower(), now_str),
                )
                conn.commit()
            logger.info(f"Added dynamic {kind} keyword: '{kw}'")
            return True, f"✅ Added '{kw}' to {kind} keywords."
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                return False, f"⚠️ Keyword '{kw}' already exists."
            logger.error(f"Error adding keyword '{kw}': {e}")
            return False, f"❌ Error saving keyword: {e}"

    def remove_keyword(self, keyword: str) -> Tuple[bool, str]:
        """Remove a dynamic keyword. Returns (success, message)."""
        kw = keyword.strip()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dynamic_keywords WHERE LOWER(keyword) = LOWER(?);", (kw,))
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info(f"Removed dynamic keyword: '{kw}'")
            return True, f"✅ Removed keyword: '{kw}'"
        return False, f"⚠️ Keyword '{kw}' was not found in dynamic keywords."

    def get_all_dynamic_keywords(self, kind: str = "include") -> List[str]:
        """Retrieve all stored dynamic keywords of a given kind."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT keyword FROM dynamic_keywords WHERE kind = ? ORDER BY id ASC;", (kind.lower(),))
            rows = cursor.fetchall()
            return [row["keyword"] for row in rows]
