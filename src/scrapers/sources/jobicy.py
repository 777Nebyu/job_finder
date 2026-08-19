"""
Jobicy Remote Jobs Scraper (https://jobicy.com/api/v2/remote-jobs).
Fetches categorized remote positions via public JSON API.
"""

from typing import List
from src.models.raw_job import RawJobPosting
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry


@ScraperRegistry.register("jobicy")
class JobicyScraper(BaseScraper):
    """Scrapes remote jobs from Jobicy public JSON API."""

    source_name = "jobicy"

    def __init__(
        self,
        api_url: str = "https://jobicy.com/api/v2/remote-jobs",
        count: int = 30,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_url = api_url
        self.count = count

    def fetch(self) -> List[RawJobPosting]:
        all_postings: List[RawJobPosting] = []

        try:
            response = self.client.get(
                self.api_url,
                params={"count": self.count},
            )
            data = response.json()
        except Exception as e:
            self.logger.warning(f"Jobicy API request failed: {e}")
            return []

        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        for item in jobs:
            title = item.get("jobTitle")
            if not title:
                continue

            company = item.get("companyName") or "Unknown Company"
            location = item.get("jobGeo") or "Anywhere (100% Remote)"
            url = item.get("url") or f"https://jobicy.com/jobs/{item.get('id')}"
            
            tags: List[str] = []
            if item.get("jobIndustry"):
                tags.append(str(item.get("jobIndustry")))
            if item.get("jobType"):
                tags.append(str(item.get("jobType")))

            all_postings.append(
                RawJobPosting(
                    source=self.source_name,
                    raw_id=str(item.get("id")),
                    title=title.strip(),
                    company=company.strip(),
                    location=location.strip(),
                    remote_flag=True,
                    url=url,
                    posted_date_raw=item.get("pubDate"),
                    description=item.get("jobDescription", ""),
                    tags=tags,
                    raw_payload=item,
                )
            )

        return all_postings
