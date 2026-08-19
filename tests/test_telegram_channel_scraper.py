"""
Unit tests for Telegram Channel Web Scraper.
"""

from src.scrapers.sources.telegram_channels import TelegramChannelScraper
from src.scrapers.registry import ScraperRegistry


def test_telegram_channel_scraper_registration():
    """Verify telegram_channels is registered in ScraperRegistry."""
    available = ScraperRegistry.list_available()
    assert "telegram_channels" in available


def test_telegram_channel_live_fetch():
    """Integration test: Scrape from public telegram channel."""
    scraper = TelegramChannelScraper(channels=["freelance_ethio"], max_posts_per_channel=5)
    results = scraper.safe_fetch()
    assert isinstance(results, list)
    if results:
        job = results[0]
        assert job.source.startswith("tg_")
        assert len(job.title) > 0
        assert "t.me" in job.url
