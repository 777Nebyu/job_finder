"""
Unit tests for Application Deadline Parsing and Expiration Filtering.
"""

from datetime import date, datetime, timedelta, timezone
from config.settings import FilterConfig
from src.filters.keyword_filter import JobFilterEngine
from src.models.canonical_job import JobPosting
from src.normalizers.date_parser import parse_deadline


def test_deadline_parser():
    """Verify parsing of various deadline string formats."""
    d1 = parse_deadline("August 31st, 2026")
    assert d1 == date(2026, 8, 31)

    d2 = parse_deadline("Aug 31, 2026")
    assert d2 == date(2026, 8, 31)

    d3 = parse_deadline("September 1st, 2026")
    assert d3 == date(2026, 9, 1)

    d4 = parse_deadline("2026-09-15")
    assert d4 == date(2026, 9, 15)


def test_expired_deadline_filtering():
    """Verify that jobs with expired deadlines are filtered out."""
    config = FilterConfig(
        include_keywords=["IT Officer"],
        case_sensitive=False,
    )
    engine = JobFilterEngine(config)

    # Past deadline
    past_date = datetime.now(timezone.utc).date() - timedelta(days=5)
    expired_job = JobPosting(
        source="tg_freelance_ethio",
        title="IT Officer",
        company="Tech Corp",
        url="https://t.me/freelance_ethio/1",
        deadline=past_date,
    )
    res = engine.evaluate(expired_job)
    assert res.is_match is False
    assert "deadline has passed" in res.reason.lower()

    # Future deadline
    future_date = datetime.now(timezone.utc).date() + timedelta(days=10)
    active_job = JobPosting(
        source="tg_freelance_ethio",
        title="IT Officer",
        company="Tech Corp",
        url="https://t.me/freelance_ethio/2",
        deadline=future_date,
    )
    res_active = engine.evaluate(active_job)
    assert res_active.is_match is True
