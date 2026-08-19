"""
Dynamic Keyword Store for Telegram Bot Commands.
Persists user-added keywords in SQLite and syncs with JSON state file so they survive restarts.
Supports bulk add and remove.
"""

from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
from src.storage.database import DatabaseManager
from src.utils.logger import setup_logger
from src.utils.persistent_state import PersistentStateStore

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
    """Manages persistent dynamic keywords stored in SQLite and synced to JSON state."""

    def __init__(self, db_manager: DatabaseManager, state_store: Optional[PersistentStateStore] = None):
        self.db_manager = db_manager
        self.state_store = state_store or PersistentStateStore()
        self._init_table()
        self._restore_from_state_file()

    def _init_table(self) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(CREATE_KEYWORDS_TABLE)
            conn.commit()

    def _restore_from_state_file(self) -> None:
        """Restores keywords from JSON state file on boot/restart."""
        state = self.state_store.load_state()
        inc_kws = state.get("dynamic_keywords_include", [])
        exc_kws = state.get("dynamic_keywords_exclude", [])
        now_str = datetime.now(timezone.utc).isoformat()

        with self.db_manager.get_connection() as conn:
            for kw in inc_kws:
                if kw.strip():
                    conn.execute(
                        "INSERT INTO dynamic_keywords (keyword, kind, created_at) VALUES (?, 'include', ?) ON CONFLICT(keyword) DO NOTHING;",
                        (kw.strip(), now_str),
                    )
            for kw in exc_kws:
                if kw.strip():
                    conn.execute(
                        "INSERT INTO dynamic_keywords (keyword, kind, created_at) VALUES (?, 'exclude', ?) ON CONFLICT(keyword) DO NOTHING;",
                        (kw.strip(), now_str),
                    )
            conn.commit()

    def _sync_to_state_file(self) -> None:
        """Flushes current dynamic keywords to the JSON state file."""
        inc = self.get_all_dynamic_keywords("include")
        exc = self.get_all_dynamic_keywords("exclude")
        state = self.state_store.load_state()
        state["dynamic_keywords_include"] = inc
        state["dynamic_keywords_exclude"] = exc
        self.state_store.save_state(state)

    def add_keyword(self, keyword: str, kind: str = "include") -> Tuple[bool, str]:
        """Add a dynamic keyword. Returns (success, message)."""
        kw = keyword.strip().strip(",")
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
            self._sync_to_state_file()
            logger.info(f"Added dynamic {kind} keyword: '{kw}'")
            return True, f"✅ Added '{kw}' to {kind} keywords."
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                return False, f"⚠️ Keyword '{kw}' already exists."
            logger.error(f"Error adding keyword '{kw}': {e}")
            return False, f"❌ Error saving keyword: {e}"

    def add_multiple_keywords(self, raw_input: str, kind: str = "include") -> Tuple[List[str], List[str]]:
        """
        Parses and adds multiple keywords separated by commas or newlines.
        Returns (added_keywords, skipped_keywords).
        """
        tokens = [t.strip() for t in re.split(r"[,;\n]+", raw_input) if t.strip()]
        added = []
        skipped = []

        for token in tokens:
            ok, _ = self.add_keyword(token, kind=kind)
            if ok:
                added.append(token)
            else:
                skipped.append(token)

        return added, skipped

    def remove_keyword(self, keyword: str) -> Tuple[bool, str]:
        """Remove a dynamic keyword. Returns (success, message)."""
        kw = keyword.strip().strip(",")
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dynamic_keywords WHERE LOWER(keyword) = LOWER(?);", (kw,))
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            self._sync_to_state_file()
            logger.info(f"Removed dynamic keyword: '{kw}'")
            return True, f"✅ Removed keyword: '{kw}'"
        return False, f"⚠️ Keyword '{kw}' was not found in dynamic keywords."

    def remove_multiple_keywords(self, raw_input: str) -> Tuple[List[str], List[str]]:
        """
        Parses and removes multiple keywords.
        Returns (removed_keywords, not_found_keywords).
        """
        tokens = [t.strip() for t in re.split(r"[,;\n]+", raw_input) if t.strip()]
        removed = []
        not_found = []

        for token in tokens:
            ok, _ = self.remove_keyword(token)
            if ok:
                removed.append(token)
            else:
                not_found.append(token)

        return removed, not_found

    def get_all_dynamic_keywords(self, kind: str = "include") -> List[str]:
        """Retrieve all stored dynamic keywords of a given kind."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT keyword FROM dynamic_keywords WHERE kind = ? ORDER BY id ASC;", (kind.lower(),))
            rows = cursor.fetchall()
            return [row["keyword"] for row in rows]
