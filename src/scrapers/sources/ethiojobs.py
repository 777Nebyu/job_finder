"""
Ethiojobs Scraper (https://ethiojobs.net/jobs).
Extracts jobs from the server-rendered Next.js pageProps data and pagination.
"""

import json
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.raw_job import RawJobPosting
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry


@ScraperRegistry.register("ethiojobs")
class EthiojobsScraper(BaseScraper):
    """Scrapes job listings from Ethiojobs.net."""

    source_name = "ethiojobs"

    def __init__(
        self,
        base_url: str = "https://ethiojobs.net/jobs",
        max_pages: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_url = base_url
        self.max_pages = max_pages

    def fetch(self) -> List[RawJobPosting]:
        all_postings: List[RawJobPosting] = []

        for page in range(1, self.max_pages + 1):
            url = f"{self.base_url}?page={page}"
            self.logger.debug(f"Fetching Ethiojobs page {page}: {url}")
            
            try:
                response = self.client.get(url)
            except Exception as e:
                self.logger.warning(f"Ethiojobs failed to fetch page {page}: {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            script_tag = soup.find("script", id="__NEXT_DATA__")

            if not script_tag or not script_tag.string:
                self.logger.warning(f"No __NEXT_DATA__ script found on Ethiojobs page {page}.")
                break

            try:
                data = json.loads(script_tag.string)
                jobs_container = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("jobs", {})
                )
                items = jobs_container.get("data", [])
            except Exception as e:
                self.logger.warning(f"Failed to parse Next.js JSON on Ethiojobs page {page}: {e}")
                break

            if not items:
                self.logger.debug(f"No jobs found on Ethiojobs page {page}.")
                break

            for item in items:
                posting = self._parse_ethiojobs_item(item)
                if posting:
                    all_postings.append(posting)

        return all_postings

    def _parse_ethiojobs_item(self, item: dict) -> Optional[RawJobPosting]:
        """Convert an Ethiojobs JSON item to RawJobPosting."""
        title = item.get("title")
        if not title:
            return None

        # Extract company name
        company_data = item.get("company")
        company_name = "Unknown Company"
        if isinstance(company_data, dict):
            company_name = company_data.get("name") or company_data.get("name_legal") or "Unknown Company"

        # Direct link
        slug = item.get("slug")
        if slug:
            job_url = f"https://ethiojobs.net/jobs/{slug}"
        else:
            job_url = self.base_url

        # Location and remote eligibility
        location_type = str(item.get("location_type", "")).strip()
        is_remote = location_type.lower() == "remote" or "remote" in title.lower()
        
        # Tags & categories
        tags: List[str] = []
        catalogs = item.get("catalogs", [])
        if isinstance(catalogs, list):
            for cat in catalogs:
                if isinstance(cat, dict) and "name" in cat:
                    tags.append(str(cat["name"]).strip())
                elif isinstance(cat, str):
                    tags.append(cat.strip())

        if location_type:
            tags.append(location_type)

        level = item.get("level")
        if level:
            tags.append(f"Level {level}")

        # Construct raw job posting
        return RawJobPosting(
            source=self.source_name,
            raw_id=str(item.get("id", "")),
            title=title.strip(),
            company=company_name.strip(),
            location=f"Ethiopia ({location_type})" if location_type else "Ethiopia",
            remote_flag=is_remote,
            url=job_url,
            posted_date_raw=item.get("date_published"),
            description=item.get("description", ""),
            tags=tags,
            raw_payload=item,
        )
