"""
Job Repository for SQLite Storage.
Handles persistence, deduplication lookups, and query methods.
"""

import json
from datetime import date, datetime, timezone
from typing import List, Optional
from src.models.canonical_job import JobPosting
from src.storage.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger("repository")


class JobRepository:
    """Repository handling all database operations for JobPosting entities."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def save_job(self, job: JobPosting, mark_notified: bool = False) -> JobPosting:
        """Persists a canonical JobPosting into SQLite."""
        job.generate_and_set_hash()

        insert_sql = """
        INSERT INTO jobs (
            source, title, company, location, remote_flag, url,
            posted_date, description, tags, dedupe_hash, first_seen, notified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(dedupe_hash) DO NOTHING
        RETURNING id;
        """

        tags_json = json.dumps(job.tags)
        posted_date_str = job.posted_date.isoformat() if job.posted_date else None
        first_seen_str = job.first_seen.isoformat()

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                insert_sql,
                (
                    job.source,
                    job.title,
                    job.company,
                    job.location,
                    1 if job.remote_flag else 0,
                    job.url,
                    posted_date_str,
                    job.description,
                    tags_json,
                    job.dedupe_hash,
                    first_seen_str,
                    1 if mark_notified else 0,
                ),
            )
            row = cursor.fetchone()
            if row:
                job.id = row["id"]
            conn.commit()

        return job

    def is_hash_seen(self, dedupe_hash: str) -> bool:
        """Fast check to see if a dedupe_hash already exists in the database."""
        query = "SELECT 1 FROM jobs WHERE dedupe_hash = ? LIMIT 1;"
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (dedupe_hash,))
            return cursor.fetchone() is not None

    def mark_as_notified(self, job_id: int) -> None:
        """Mark a job posting as having had a notification sent."""
        query = "UPDATE jobs SET notified = 1 WHERE id = ?;"
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (job_id,))
            conn.commit()

    def get_recent_jobs(self, limit: int = 500) -> List[JobPosting]:
        """Fetch recent job postings from the database."""
        query = "SELECT * FROM jobs ORDER BY id DESC LIMIT ?;"
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def count_total_jobs(self) -> int:
        """Returns the total number of stored jobs."""
        query = "SELECT COUNT(*) as count FROM jobs;"
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return row["count"] if row else 0

    @staticmethod
    def _row_to_model(row) -> JobPosting:
        """Converts an SQLite row into a JobPosting model."""
        tags = []
        if row["tags"]:
            try:
                tags = json.loads(row["tags"])
            except Exception:
                tags = []

        posted_date = None
        if row["posted_date"]:
            try:
                posted_date = date.fromisoformat(row["posted_date"])
            except Exception:
                pass

        first_seen = datetime.now(timezone.utc)
        if row["first_seen"]:
            try:
                first_seen = datetime.fromisoformat(row["first_seen"])
            except Exception:
                pass

        return JobPosting(
            id=row["id"],
            source=row["source"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            remote_flag=bool(row["remote_flag"]),
            url=row["url"],
            posted_date=posted_date,
            description=row["description"] or "",
            tags=tags,
            dedupe_hash=row["dedupe_hash"],
            first_seen=first_seen,
        )
