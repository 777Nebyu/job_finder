"""
Dynamic Channel Store for Telegram Channel Scraper.
Allows adding and removing multiple Telegram job channels dynamically.
Guarantees zero duplicate scraping and dual persistence (SQLite + JSON state file)
so custom channels survive server restarts and container redeploys.
"""

from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
from src.storage.database import DatabaseManager
from src.utils.logger import setup_logger
from src.utils.persistent_state import PersistentStateStore

logger = setup_logger("dynamic_channels")

CREATE_CHANNELS_TABLE = """
CREATE TABLE IF NOT EXISTS dynamic_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
"""

DEFAULT_MONITORED_CHANNELS = [
    "freelance_ethio",
    "ethiojobsofficial",
    "hahujobs",
    "shegerjobs",
    "harmeejobs",
    "effoi_jobs",
]


class DynamicChannelStore:
    """Manages persistent dynamic Telegram channels stored in SQLite and synced to JSON state."""

    def __init__(self, db_manager: DatabaseManager, state_store: Optional[PersistentStateStore] = None):
        self.db_manager = db_manager
        self.state_store = state_store or PersistentStateStore()
        self._init_table()
        self._restore_from_state_file()

    def _init_table(self) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(CREATE_CHANNELS_TABLE)
            conn.commit()

    def _restore_from_state_file(self) -> None:
        """Restores channels from JSON state file on boot/restart."""
        state = self.state_store.load_state()
        saved_channels = state.get("dynamic_channels", [])
        now_str = datetime.now(timezone.utc).isoformat()

        with self.db_manager.get_connection() as conn:
            for ch in saved_channels:
                clean_ch = self.clean_channel_name(ch)
                if clean_ch:
                    conn.execute(
                        "INSERT INTO dynamic_channels (channel_name, created_at) VALUES (?, ?) ON CONFLICT(channel_name) DO NOTHING;",
                        (clean_ch, now_str),
                    )
            conn.commit()

    def _sync_to_state_file(self) -> None:
        """Flushes current dynamic channels to the JSON state file."""
        all_dyn = self.get_all_dynamic_channels()
        state = self.state_store.load_state()
        state["dynamic_channels"] = all_dyn
        self.state_store.save_state(state)

    @staticmethod
    def clean_channel_name(channel: str) -> str:
        """Cleans and standardizes channel handle (e.g. 'https://t.me/freelance_ethio' or '@freelance_ethio' -> 'freelance_ethio')."""
        ch = channel.strip()
        ch = re.sub(r"^https?://t\.me/(?:s/)?", "", ch)
        ch = ch.lstrip("@").strip().rstrip("/")
        ch = ch.strip(", ")
        return ch

    def add_channel(self, channel: str) -> Tuple[bool, str]:
        """Add a dynamic Telegram channel to scrape. Returns (success, message)."""
        clean_ch = self.clean_channel_name(channel)
        if not clean_ch:
            return False, "⚠️ Invalid channel name."

        if clean_ch.lower() in [c.lower() for c in DEFAULT_MONITORED_CHANNELS]:
            return False, f"⚠️ Channel @{clean_ch} is already in the default monitored list."

        now_str = datetime.now(timezone.utc).isoformat()
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    "INSERT INTO dynamic_channels (channel_name, created_at) VALUES (?, ?);",
                    (clean_ch, now_str),
                )
                conn.commit()
            self._sync_to_state_file()
            logger.info(f"Added dynamic Telegram channel: @{clean_ch}")
            return True, f"✅ Added @{clean_ch} to monitored job channels."
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                return False, f"⚠️ Channel @{clean_ch} is already being monitored."
            logger.error(f"Error adding channel '@{clean_ch}': {e}")
            return False, f"❌ Error saving channel: {e}"

    def add_multiple_channels(self, raw_input: str) -> Tuple[List[str], List[str]]:
        """
        Parses and adds multiple channels separated by spaces, commas, or newlines.
        Returns (added_channels, skipped_or_existing_channels).
        """
        tokens = re.split(r"[\s,\n]+", raw_input.strip())
        added = []
        skipped = []

        for token in tokens:
            cleaned = self.clean_channel_name(token)
            if not cleaned:
                continue
            ok, _ = self.add_channel(cleaned)
            if ok:
                added.append(f"@{cleaned}")
            else:
                skipped.append(f"@{cleaned}")

        return added, skipped

    def remove_channel(self, channel: str) -> Tuple[bool, str]:
        """Remove a dynamic channel. Returns (success, message)."""
        clean_ch = self.clean_channel_name(channel)
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dynamic_channels WHERE LOWER(channel_name) = LOWER(?);", (clean_ch,))
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            self._sync_to_state_file()
            logger.info(f"Removed dynamic channel: @{clean_ch}")
            return True, f"✅ Removed @{clean_ch} from monitored channels."
        return False, f"⚠️ Channel @{clean_ch} was not found in dynamic channels."

    def remove_multiple_channels(self, raw_input: str) -> Tuple[List[str], List[str]]:
        """
        Parses and removes multiple channels.
        Returns (removed_channels, not_found_channels).
        """
        tokens = re.split(r"[\s,\n]+", raw_input.strip())
        removed = []
        not_found = []

        for token in tokens:
            cleaned = self.clean_channel_name(token)
            if not cleaned:
                continue
            ok, _ = self.remove_channel(cleaned)
            if ok:
                removed.append(f"@{cleaned}")
            else:
                not_found.append(f"@{cleaned}")

        return removed, not_found

    def get_all_dynamic_channels(self) -> List[str]:
        """Retrieve all stored dynamic channels."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT channel_name FROM dynamic_channels ORDER BY id ASC;")
            rows = cursor.fetchall()
            return [row["channel_name"] for row in rows]
