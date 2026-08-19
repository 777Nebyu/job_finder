"""
Canonical Job Posting Data Model.
Strictly implements Section 4 (Canonical Data Schema) of the Functional Requirements:
- id: integer (Primary key)
- source: string (Which scraper produced this posting)
- title: string (Job title as posted)
- company: string (Company or organization name)
- location: string (Normalized location text)
- remote_flag: boolean (Whether posting is remote-eligible)
- url: string (Direct link to the posting)
- posted_date: Optional[date] (Date the posting was published)
- description: string (Full or truncated job description text)
- tags: List[str] (Keywords/skills extracted or provided by source)
- dedupe_hash: string (Hash of title + company + url)
- first_seen: datetime (Timestamp first fetched by system)
"""

from datetime import date, datetime, timezone
from typing import List, Optional
import hashlib
from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    """Canonical representation of a job posting across all sources."""
    id: Optional[int] = Field(default=None, description="Database primary key")
    source: str = Field(..., description="Scraper identifier (e.g. 'ethiojobs', 'remoteok')")
    title: str = Field(..., description="Job title")
    company: str = Field(default="Unknown Company", description="Employer or organization name")
    location: str = Field(default="Remote", description="Location string")
    remote_flag: bool = Field(default=False, description="Remote eligible flag")
    url: str = Field(..., description="Direct URL to job posting")
    posted_date: Optional[date] = Field(default=None, description="Publication date")
    description: str = Field(default="", description="Job description text")
    tags: List[str] = Field(default_factory=list, description="Categorization tags/skills")
    dedupe_hash: str = Field(default="", description="SHA-256 hash for intra-source deduplication")
    first_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp first fetched",
    )

    @classmethod
    def compute_dedupe_hash(cls, title: str, company: str, url: str) -> str:
        """
        Compute deterministic SHA-256 dedupe hash from (title + company + url).
        Normalizes whitespace and casing before hashing.
        """
        norm_title = " ".join(title.lower().split())
        norm_company = " ".join(company.lower().split())
        # Clean URL query params that change per request (e.g. tracking tokens)
        norm_url = url.strip().split("?")[0].lower()
        key = f"{norm_title}|{norm_company}|{norm_url}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def generate_and_set_hash(self) -> str:
        """Sets the dedupe_hash on this instance if not already present."""
        if not self.dedupe_hash:
            self.dedupe_hash = self.compute_dedupe_hash(self.title, self.company, self.url)
        return self.dedupe_hash
