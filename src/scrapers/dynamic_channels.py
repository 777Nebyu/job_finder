"""
Dynamic Channel Store for Telegram Channel Scraper.
Allows adding and removing Telegram job channels dynamically via Telegram Bot commands and Web UI.
"""

from datetime import datetime, timezone
import re
from typing import List, Tuple
from src.storage.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger("dynamic_channels")

CREATE_CHANNELS_TABLE = """
CREATE TABLE IF NOT EXISTS dynamic_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
"""


class DynamicChannelStore:
    """Manages persistent dynamic Telegram channels stored in SQLite."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._init_table()

    def _init_table(self) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute(CREATE_CHANNELS_TABLE)
            conn.commit()

    @staticmethod
    def clean_channel_name(channel: str) -> str:
        """Cleans and standardizes channel handle (e.g. 'https://t.me/freelance_ethio' or '@freelance_ethio' -> 'freelance_ethio')."""
        ch = channel.strip()
        ch = re.sub(r"^https?://t\.me/(?:s/)?", "", ch)
        ch = ch.lstrip("@").strip().rstrip("/")
        return ch

    def add_channel(self, channel: str) -> Tuple[bool, str]:
        """Add a dynamic Telegram channel to scrape. Returns (success, message)."""
        clean_ch = self.clean_channel_name(channel)
        if not clean_ch:
            return False, "⚠️ Invalid channel name."

        now_str = datetime.now(timezone.utc).isoformat()
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    "INSERT INTO dynamic_channels (channel_name, created_at) VALUES (?, ?);",
                    (clean_ch, now_str),
                )
                conn.commit()
            logger.info(f"Added dynamic Telegram channel: @{clean_ch}")
            return True, f"✅ Added @{clean_ch} to monitored job channels."
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                return False, f"⚠️ Channel @{clean_ch} is already being monitored."
            logger.error(f"Error adding channel '@{clean_ch}': {e}")
            return False, f"❌ Error saving channel: {e}"

    def remove_channel(self, channel: str) -> Tuple[bool, str]:
        """Remove a dynamic channel. Returns (success, message)."""
        clean_ch = self.clean_channel_name(channel)
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dynamic_channels WHERE LOWER(channel_name) = LOWER(?);", (clean_ch,))
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info(f"Removed dynamic channel: @{clean_ch}")
            return True, f"✅ Removed @{clean_ch} from monitored channels."
        return False, f"⚠️ Channel @{clean_ch} was not found in dynamic channels."

    def get_all_dynamic_channels(self) -> List[str]:
        """Retrieve all stored dynamic channels."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT channel_name FROM dynamic_channels ORDER BY id ASC;")
            rows = cursor.fetchall()
            return [row["channel_name"] for row in rows]
