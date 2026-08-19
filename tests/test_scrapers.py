"""
Unit and Integration tests for Module 1: Scrapers and Error Isolation.
"""

import pytest
from src.models.raw_job import RawJobPosting
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry
from src.scrapers.sources.ethiojobs import EthiojobsScraper
from src.scrapers.sources.remoteok import RemoteOKScraper
from src.scrapers.sources.jobicy import JobicyScraper


class BrokenScraper(BaseScraper):
    """Mock scraper designed to intentionally throw exceptions (testing FR-9)."""
    source_name = "broken_source"

    def fetch(self):
        raise ConnectionResetError("Simulated catastrophic network failure")


def test_scraper_registry():
    """Verify scraper registration and factory instantiation."""
    available = ScraperRegistry.list_available()
    assert "ethiojobs" in available
    assert "remoteok" in available
    assert "jobicy" in available
    assert "afriwork" in available
    assert "josad" in available

    scraper = ScraperRegistry.create_scraper("ethiojobs")
    assert isinstance(scraper, EthiojobsScraper)


def test_error_isolation_fr9():
    """FR-9 Test: Ensure a crashing scraper does NOT raise an exception out of safe_fetch()."""
    broken = BrokenScraper()
    # safe_fetch should catch exception, log it, and return empty list
    results = broken.safe_fetch()
    assert results == []


def test_live_ethiojobs_scraper():
    """Integration test: Live fetch from Ethiojobs."""
    scraper = EthiojobsScraper(max_pages=1)
    results = scraper.safe_fetch()
    assert isinstance(results, list)
    if results:
        job = results[0]
        assert isinstance(job, RawJobPosting)
        assert job.source == "ethiojobs"
        assert len(job.title) > 0
        assert job.url.startswith("http")


def test_live_remoteok_scraper():
    """Integration test: Live fetch from RemoteOK."""
    scraper = RemoteOKScraper(max_jobs=5)
    results = scraper.safe_fetch()
    assert isinstance(results, list)
    if results:
        job = results[0]
        assert isinstance(job, RawJobPosting)
        assert job.source == "remoteok"
        assert len(job.title) > 0
