"""
Filter Rules Data Model.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FilterMatchResult(BaseModel):
    """Result of evaluating a job posting against filter criteria."""
    is_match: bool
    matched_include_keywords: List[str] = Field(default_factory=list)
    matched_exclude_keywords: List[str] = Field(default_factory=list)
    matched_location: Optional[str] = None
    reason: str = ""
