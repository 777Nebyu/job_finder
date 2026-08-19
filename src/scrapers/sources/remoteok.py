"""
RemoteOK API Scraper (https://remoteok.com/api).
Fetches global and Africa-eligible remote positions via public JSON API.
"""

from typing import List, Optional
from src.models.raw_job import RawJobPosting
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry


@ScraperRegistry.register("remoteok")
class RemoteOKScraper(BaseScraper):
    """Scrapes remote jobs from RemoteOK public JSON API."""

    source_name = "remoteok"

    def __init__(
        self,
        api_url: str = "https://remoteok.com/api",
        max_jobs: int = 50,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_url = api_url
        self.max_jobs = max_jobs

    def fetch(self) -> List[RawJobPosting]:
        all_postings: List[RawJobPosting] = []

        try:
            response = self.client.get(
                self.api_url,
                headers={"User-Agent": "JobAlertBot/1.0 (Contact: alert-bot@example.com)"},
            )
            data = response.json()
        except Exception as e:
            self.logger.warning(f"RemoteOK API request failed: {e}")
            return []

        if not isinstance(data, list):
            return []

        # The first element in RemoteOK API is often legal/disclaimer metadata
        job_items = [item for item in data if isinstance(item, dict) and "id" in item and "position" in item]

        for item in job_items[: self.max_jobs]:
            title = item.get("position")
            if not title:
                continue

            company = item.get("company", "Unknown Company")
            location = item.get("location") or "Worldwide Remote"
            url = item.get("url") or f"https://remoteok.com/l/{item.get('id')}"
            tags = item.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]

            all_postings.append(
                RawJobPosting(
                    source=self.source_name,
                    raw_id=str(item.get("id")),
                    title=title.strip(),
                    company=company.strip(),
                    location=location.strip(),
                    remote_flag=True,
                    url=url,
                    posted_date_raw=item.get("date"),
                    description=item.get("description", ""),
                    tags=tags,
                    raw_payload=item,
                )
            )

        return all_postings
