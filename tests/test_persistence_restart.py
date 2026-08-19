"""
Unit test for Server Restart & State Persistence.
Simulates a container reboot where the SQLite database is wiped/ephemeral,
verifying that custom channels and keywords are seamlessly restored from the state file.
"""

import tempfile
from pathlib import Path
from src.filters.dynamic_keywords import DynamicKeywordStore
from src.scrapers.dynamic_channels import DynamicChannelStore
from src.storage.database import DatabaseManager
from src.utils.persistent_state import PersistentStateStore


def test_channels_and_keywords_persist_across_restarts():
    """Verify that adding channels & keywords persists across database deletion/reboots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path_1 = str(Path(tmpdir) / "server_session_1.db")
        state_path = str(Path(tmpdir) / "dynamic_state.json")

        state_store = PersistentStateStore(file_path=state_path)

        # -------------------------------------------------------------
        # Session 1: User adds channels and keywords
        # -------------------------------------------------------------
        db_1 = DatabaseManager(db_path_1)
        channel_store_1 = DynamicChannelStore(db_1, state_store=state_store)
        keyword_store_1 = DynamicKeywordStore(db_1, state_store=state_store)

        ok_ch, _ = channel_store_1.add_channel("@elelanajobs")
        assert ok_ch is True

        ok_kw, _ = keyword_store_1.add_keyword("Cloud Architect")
        assert ok_kw is True

        # Verify state file was written
        saved_state = state_store.load_state()
        assert "elelanajobs" in saved_state["dynamic_channels"]
        assert "Cloud Architect" in saved_state["dynamic_keywords_include"]

        # -------------------------------------------------------------
        # Session 2: Server restarts, ephemeral DB is recreated from scratch
        # -------------------------------------------------------------
        db_path_2 = str(Path(tmpdir) / "server_session_2.db")
        db_2 = DatabaseManager(db_path_2)

        # New stores booting up after restart
        channel_store_2 = DynamicChannelStore(db_2, state_store=state_store)
        keyword_store_2 = DynamicKeywordStore(db_2, state_store=state_store)

        # Verify restored from state file into fresh database
        restored_channels = channel_store_2.get_all_dynamic_channels()
        restored_keywords = keyword_store_2.get_all_dynamic_keywords("include")

        assert "elelanajobs" in restored_channels
        assert "Cloud Architect" in restored_keywords
