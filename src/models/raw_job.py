"""
Raw Job Posting Model.
Represents unstructured or semi-structured data returned directly from a scraper before normalization.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RawJobPosting(BaseModel):
    """
    Standard container for raw job data produced by any BaseScraper implementation.
    """
    source: str = Field(..., description="Scraper identifier, e.g., 'ethiojobs', 'remoteok'")
    raw_id: Optional[str] = Field(default=None, description="Unique ID from source platform if available")
    title: str = Field(..., description="Job title text as scraped")
    company: Optional[str] = Field(default=None, description="Company/organization name")
    location: Optional[str] = Field(default=None, description="Raw location string")
    remote_flag: Optional[bool] = Field(default=None, description="Whether posting explicitly mentions remote")
    url: str = Field(..., description="Direct link to the job posting")
    posted_date_raw: Optional[str] = Field(default=None, description="Raw date text or ISO string")
    description: Optional[str] = Field(default="", description="Job description or HTML/text content")
    tags: List[str] = Field(default_factory=list, description="Extracted or source tags/categories")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Raw JSON or metadata dict for debugging")
