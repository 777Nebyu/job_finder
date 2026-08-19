"""
Data Normalization Engine (FR-2).
Transforms RawJobPosting instances into clean, canonical JobPosting records.
"""

import html
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.canonical_job import JobPosting
from src.models.raw_job import RawJobPosting
from src.normalizers.date_parser import parse_deadline, parse_job_date
from src.utils.logger import setup_logger

logger = setup_logger("normalizer")


class JobNormalizer:
    """
    Transforms raw scraped job data into canonical JobPosting schema.
    Applies text cleaning, HTML stripping, date and deadline normalization, and remote detection.
    """

    REMOTE_KEYWORDS = [
        "remote",
        "work from home",
        "wfh",
        "telecommute",
        "anywhere",
        "worldwide",
        "distributed",
    ]

    @classmethod
    def clean_text(cls, text: Optional[str]) -> str:
        """Strips HTML tags, decodes HTML entities, and collapses excessive whitespace."""
        if not text:
            return ""

        unescaped = html.unescape(text)

        if "<" in unescaped and ">" in unescaped:
            soup = BeautifulSoup(unescaped, "html.parser")
            cleaned = soup.get_text(separator=" ")
        else:
            cleaned = unescaped

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def clean_title(cls, title: str) -> str:
        """Sanitizes job title."""
        title = cls.clean_text(title)
        title = re.sub(r"[\s\-\|]+$", "", title).strip()
        return title

    @classmethod
    def clean_company(cls, company: Optional[str]) -> str:
        """Sanitizes company name."""
        comp = cls.clean_text(company)
        return comp if comp else "Unknown Company"

    @classmethod
    def detect_remote(
        cls,
        title: str,
        location: Optional[str],
        explicit_remote_flag: Optional[bool],
        tags: List[str],
    ) -> bool:
        """Detects if job is remote eligible."""
        if explicit_remote_flag is True:
            return True

        search_corpus = f"{title} {location or ''} {' '.join(tags)}".lower()
        return any(kw in search_corpus for kw in cls.REMOTE_KEYWORDS)

    @classmethod
    def extract_deadline_from_text(cls, text: str) -> Optional[str]:
        """Extracts raw deadline string from job description or text."""
        m_dl = re.search(r"(?:Deadline|Closing\s*Date|Apply\s*Before|Expires)\s*:\s*([^\n<,]+(?:\s*,\s*\d{4})?)", text, re.I)
        if m_dl:
            return m_dl.group(1).strip()
        return None

    @classmethod
    def normalize(cls, raw: RawJobPosting) -> JobPosting:
        """
        Main normalization method.
        Converts a RawJobPosting into a validated canonical JobPosting.
        """
        clean_title = cls.clean_title(raw.title)
        clean_company = cls.clean_company(raw.company)
        clean_location = cls.clean_text(raw.location) or "Remote"
        clean_description = cls.clean_text(raw.description)

        cleaned_tags = list(
            dict.fromkeys(cls.clean_text(t) for t in raw.tags if cls.clean_text(t))
        )

        is_remote = cls.detect_remote(
            title=clean_title,
            location=clean_location,
            explicit_remote_flag=raw.remote_flag,
            tags=cleaned_tags,
        )

        posted_date = parse_job_date(raw.posted_date_raw)

        # Parse deadline: check raw.deadline_raw first, then fallback to text regex
        deadline_raw = raw.deadline_raw or cls.extract_deadline_from_text(raw.description)
        deadline = parse_deadline(deadline_raw)

        dedupe_hash = JobPosting.compute_dedupe_hash(
            title=clean_title,
            company=clean_company,
            url=raw.url,
        )

        return JobPosting(
            source=raw.source.lower(),
            title=clean_title,
            company=clean_company,
            location=clean_location,
            remote_flag=is_remote,
            url=raw.url.strip(),
            posted_date=posted_date,
            deadline=deadline,
            description=clean_description,
            tags=cleaned_tags,
            dedupe_hash=dedupe_hash,
        )

    @classmethod
    def normalize_batch(cls, raw_postings: List[RawJobPosting]) -> List[JobPosting]:
        """Normalizes a batch of raw postings, skipping invalid entries."""
        results: List[JobPosting] = []
        for raw in raw_postings:
            try:
                job = cls.normalize(raw)
                results.append(job)
            except Exception as e:
                logger.warning(f"Failed to normalize raw posting from [{raw.source}]: {e}")
        return results
