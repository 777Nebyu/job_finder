"""
Base Scraper Abstract Base Class.
Defines the standard plugin contract for all job board scrapers (FR-1, FR-9, FR-11).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.raw_job import RawJobPosting
from src.scrapers.http_client import ResilientHttpClient
from src.utils.logger import setup_logger


class BaseScraper(ABC):
    """
    Abstract Base Class that every source scraper must inherit from.
    Encapsulates resilient HTTP transport and error isolation.
    """

    source_name: str = "base_source"
    enabled: bool = True

    def __init__(
        self,
        client: Optional[ResilientHttpClient] = None,
        enabled: bool = True,
        rate_limit_delay: float = 1.5,
    ):
        self.client = client or ResilientHttpClient(rate_limit_delay=rate_limit_delay)
        self.enabled = enabled
        self.logger = setup_logger(f"scraper.{self.source_name}")

    @abstractmethod
    def fetch(self) -> List[RawJobPosting]:
        """
        Fetch raw job postings from the target source.
        Must be implemented by each concrete scraper subclass.
        """
        pass

    def safe_fetch(self) -> List[RawJobPosting]:
        """
        Executes fetch() with error isolation (FR-9).
        If a scraper encounters a network failure, HTML structure change,
        or unexpected exception, it catches the error, logs it with full context,
        and returns an empty list so other scrapers can proceed uninterrupted.
        """
        if not self.enabled:
            self.logger.info(f"Scraper [{self.source_name}] is disabled. Skipping.")
            return []

        self.logger.info(f"Starting fetch for source [{self.source_name}]...")
        start_time = self._current_time()

        try:
            results = self.fetch()
            elapsed = self._current_time() - start_time
            self.logger.info(
                f"Source [{self.source_name}] completed successfully: fetched {len(results)} postings in {elapsed:.2f}s."
            )
            return results
        except Exception as exc:
            elapsed = self._current_time() - start_time
            self.logger.error(
                f"Error in scraper [{self.source_name}] after {elapsed:.2f}s: {exc}",
                exc_info=True,
            )
            # Return empty list to isolate failure from the rest of the pipeline
            return []

    @staticmethod
    def _current_time() -> float:
        import time
        return time.time()
