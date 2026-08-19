"""
Unit tests for Dynamic Keywords persistence.
"""

import tempfile
from pathlib import Path
from src.filters.dynamic_keywords import DynamicKeywordStore
from src.storage.database import DatabaseManager


def test_dynamic_keyword_lifecycle():
    """Verify adding, retrieving, deduplicating, and removing dynamic keywords."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_dyn.db")
        db = DatabaseManager(db_path)
        store = DynamicKeywordStore(db)

        # 1. Add
        ok, msg = store.add_keyword("Flutter Developer", kind="include")
        assert ok is True
        assert "Added" in msg

        # 2. Duplicate Add
        ok2, msg2 = store.add_keyword("Flutter Developer", kind="include")
        assert ok2 is False
        assert "already exists" in msg2

        # 3. Retrieve
        all_kw = store.get_all_dynamic_keywords("include")
        assert "Flutter Developer" in all_kw

        # 4. Remove
        ok_rem, msg_rem = store.remove_keyword("Flutter Developer")
        assert ok_rem is True
        assert "Removed" in msg_rem

        # 5. Verify empty
        all_kw_after = store.get_all_dynamic_keywords("include")
        assert "Flutter Developer" not in all_kw_after
