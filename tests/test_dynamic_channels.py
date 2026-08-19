"""
Unit tests for Dynamic Telegram Channels.
"""

import tempfile
from pathlib import Path
from src.scrapers.dynamic_channels import DynamicChannelStore
from src.storage.database import DatabaseManager


def test_dynamic_channel_store():
    """Verify adding, standardizing, retrieving, and removing Telegram channels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_channels.db")
        db = DatabaseManager(db_path)
        store = DynamicChannelStore(db)

        # 1. Add with @ prefix
        ok, msg = store.add_channel("@harmeejobs")
        assert ok is True
        assert "harmeejobs" in msg

        # 2. Add with full URL
        ok2, msg2 = store.add_channel("https://t.me/effoi_jobs")
        assert ok2 is True

        # 3. Retrieve
        all_ch = store.get_all_dynamic_channels()
        assert "harmeejobs" in all_ch
        assert "effoi_jobs" in all_ch

        # 4. Remove
        ok_rem, msg_rem = store.remove_channel("harmeejobs")
        assert ok_rem is True

        # 5. Verify removed
        all_after = store.get_all_dynamic_channels()
        assert "harmeejobs" not in all_after
        assert "effoi_jobs" in all_after
