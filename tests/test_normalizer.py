"""
Unit tests for Module 2: Normalization and Date Parsing.
"""

from datetime import date
from src.models.raw_job import RawJobPosting
from src.normalizers.base_normalizer import JobNormalizer
from src.normalizers.date_parser import parse_job_date


def test_date_parser_formats():
    """Verify universal date parser on ISO, relative, and formatted dates."""
    # ISO date
    d1 = parse_job_date("2026-08-19T14:30:00Z")
    assert d1 == date(2026, 8, 19)

    # Standard format
    d2 = parse_job_date("August 19, 2026")
    assert d2 == date(2026, 8, 19)

    # Relative date
    d3 = parse_job_date("2 days ago")
    assert isinstance(d3, date)


def test_normalizer_html_stripping():
    """Verify HTML stripping and entity decoding."""
    raw = RawJobPosting(
        source="ethiojobs",
        title="&lt;b&gt;IT Officer&lt;/b&gt; - Urgent!",
        company="Global Health &amp; Safety PLC",
        location="<p>Addis Ababa</p>",
        description="<div>We are looking for an <b>IT Specialist</b> &amp; system admin.</div>",
        url="https://ethiojobs.net/jobs/it-1",
        posted_date_raw="2026-08-19",
        tags=["IT", "Support"],
    )

    job = JobNormalizer.normalize(raw)
    assert job.title == "IT Officer - Urgent!"
    assert job.company == "Global Health & Safety PLC"
    assert job.location == "Addis Ababa"
    assert "<b>" not in job.description
    assert job.posted_date == date(2026, 8, 19)
    assert len(job.dedupe_hash) == 64


def test_normalizer_remote_detection():
    """Verify remote detection logic."""
    raw_remote = RawJobPosting(
        source="remoteok",
        title="Senior Python Backend Developer (100% Remote)",
        company="Tech Inc",
        location="Worldwide",
        url="https://remoteok.com/l/1",
    )
    job = JobNormalizer.normalize(raw_remote)
    assert job.remote_flag is True
