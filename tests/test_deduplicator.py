"""
Unit tests for Module 3: Storage & Dual Deduplication (FR-3, FR-4, FR-5).
"""

import tempfile
from pathlib import Path
from src.models.canonical_job import JobPosting
from src.storage.database import DatabaseManager
from src.storage.deduplicator import Deduplicator
from src.storage.repository import JobRepository


def test_sqlite_storage_and_intra_source_dedupe():
    """FR-3 & FR-5: Persistent storage and exact hash deduplication."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_jobs.db")
        db_manager = DatabaseManager(db_path)
        repo = JobRepository(db_manager)
        deduplicator = Deduplicator(repo, fuzzy_threshold=85)

        job1 = JobPosting(
            source="ethiojobs",
            title="Database Administrator",
            company="Bank of Abyssinia",
            url="https://ethiojobs.net/jobs/dba-100",
        )
        saved = repo.save_job(job1)
        assert saved.id is not None
        assert repo.is_hash_seen(job1.dedupe_hash) is True
        assert repo.count_total_jobs() == 1

        # Second identical posting should be detected as intra-source duplicate
        job1_dup = JobPosting(
            source="ethiojobs",
            title="Database Administrator",
            company="Bank of Abyssinia",
            url="https://ethiojobs.net/jobs/dba-100",
        )
        is_dup, reason = deduplicator.is_duplicate(job1_dup, [])
        assert is_dup is True
        assert "Exact hash match" in reason


def test_cross_source_fuzzy_deduplication():
    """FR-4: Cross-source fuzzy duplicate detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_fuzzy.db")
        db_manager = DatabaseManager(db_path)
        repo = JobRepository(db_manager)
        deduplicator = Deduplicator(repo, fuzzy_threshold=85)

        job_ethio = JobPosting(
            source="ethiojobs",
            title="Senior IT Officer",
            company="Save the Children Ethiopia",
            url="https://ethiojobs.net/jobs/save-it",
        )
        repo.save_job(job_ethio)

        # Cross-source posting with slightly different title and URL from another board
        job_afriwork = JobPosting(
            source="afriwork",
            title="Senior IT Officer",
            company="Save the Children Ethiopia",
            url="https://afriworket.com/jobs/it-officer-save",
        )

        existing = repo.get_recent_jobs()
        is_dup, reason = deduplicator.is_duplicate(job_afriwork, existing)
        assert is_dup is True
        assert "Cross-source" in reason
