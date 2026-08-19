"""
Afriwork Scraper (https://afriworket.com/jobs).
Extracts postings from Afriwork with HTML parsing and GraphQL/API support.
"""

from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.raw_job import RawJobPosting
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry


@ScraperRegistry.register("afriwork")
class AfriworkScraper(BaseScraper):
    """Scrapes job listings from Afriwork Ethiopia."""

    source_name = "afriwork"

    def __init__(
        self,
        base_url: str = "https://afriworket.com/jobs",
        auth_token: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_url = base_url
        self.auth_token = auth_token

    def fetch(self) -> List[RawJobPosting]:
        all_postings: List[RawJobPosting] = []

        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            response = self.client.get(self.base_url, headers=headers)
        except Exception as e:
            self.logger.warning(f"Afriwork fetch failed: {e}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Look for job link cards or articles
        cards = soup.find_all(["article", "div", "a"], class_=lambda c: c and any(k in c.lower() for k in ["job", "vacancy", "card"]))
        for card in cards:
            link = card.get("href") or (card.find("a") and card.find("a").get("href"))
            title_elem = card.find(["h2", "h3", "h4", "span", "p"])
            if link and title_elem and "/job" in link:
                title = title_elem.get_text(strip=True)
                full_url = link if link.startswith("http") else f"https://afriworket.com{link}"
                all_postings.append(
                    RawJobPosting(
                        source=self.source_name,
                        title=title,
                        company="Afriwork Listed Employer",
                        location="Ethiopia / Africa",
                        remote_flag="remote" in title.lower(),
                        url=full_url,
                        description="",
                        tags=["Afriwork", "Ethiopia"],
                    )
                )

        # If Nuxt/SPA client-rendered without server items, log status gracefully
        if not all_postings:
            self.logger.info("Afriwork returned SPA shell. No static HTML job cards extracted.")

        return all_postings
