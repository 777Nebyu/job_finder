"""
Unit tests for Module 4: Keyword & Rule Filter Engine (FR-7).
"""

from config.settings import FilterConfig
from src.filters.keyword_filter import JobFilterEngine
from src.models.canonical_job import JobPosting


def test_keyword_inclusion_matching():
    """Verify include keywords match on title and description."""
    config = FilterConfig(
        include_keywords=["IT Officer", "receptionist", "database administrator"],
        exclude_keywords=["unpaid", "volunteer"],
        case_sensitive=False,
    )
    engine = JobFilterEngine(config)

    job1 = JobPosting(
        source="ethiojobs",
        title="Junior IT Officer",
        company="NGO",
        url="https://example.com/1",
    )
    res1 = engine.evaluate(job1)
    assert res1.is_match is True
    assert "IT Officer" in res1.matched_include_keywords

    job2 = JobPosting(
        source="ethiojobs",
        title="Front Desk Receptionist",
        company="Hotel",
        url="https://example.com/2",
    )
    res2 = engine.evaluate(job2)
    assert res2.is_match is True
    assert "receptionist" in res2.matched_include_keywords


def test_keyword_exclusion_precedence():
    """Verify exclude keywords override matching include keywords."""
    config = FilterConfig(
        include_keywords=["IT Officer"],
        exclude_keywords=["unpaid", "volunteer"],
        case_sensitive=False,
    )
    engine = JobFilterEngine(config)

    job_unpaid = JobPosting(
        source="ethiojobs",
        title="IT Officer (Unpaid Volunteer)",
        company="Community Org",
        url="https://example.com/3",
    )
    res = engine.evaluate(job_unpaid)
    assert res.is_match is False
    assert "unpaid" in res.matched_exclude_keywords
