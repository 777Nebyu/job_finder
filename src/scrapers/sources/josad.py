"""
Josad Scraper (https://josad.net/jobs).
Extracts postings from Josad with cookie/session support and error isolation.
"""

from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.raw_job import RawJobPosting
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry


@ScraperRegistry.register("josad")
class JosadScraper(BaseScraper):
    """Scrapes job listings from Josad Ethiopian Jobs."""

    source_name = "josad"

    def __init__(
        self,
        base_url: str = "https://josad.net/jobs",
        session_cookie: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_url = base_url
        self.session_cookie = session_cookie

    def fetch(self) -> List[RawJobPosting]:
        all_postings: List[RawJobPosting] = []
        headers = {}
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie

        try:
            # Allow redirects or check initial page
            response = self.client.get(self.base_url, headers=headers, allow_redirects=True)
        except Exception as e:
            self.logger.warning(f"Josad fetch failed: {e}")
            return []

        # If redirected to login, note gracefully without crashing
        if "login" in response.url.lower():
            self.logger.info("Josad redirected to /login. A session cookie can be supplied in config if needed.")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        job_links = soup.find_all("a", href=lambda h: h and ("/job/" in h or "/jobs/" in h))

        for link in job_links:
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if title and href:
                full_url = href if href.startswith("http") else f"https://josad.net{href}"
                all_postings.append(
                    RawJobPosting(
                        source=self.source_name,
                        title=title,
                        company="Josad Employer",
                        location="Ethiopia",
                        remote_flag="remote" in title.lower(),
                        url=full_url,
                        description="",
                        tags=["Josad", "Ethiopia"],
                    )
                )

        return all_postings
