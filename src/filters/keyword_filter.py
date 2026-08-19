"""
Keyword and Rule Filter Engine (FR-7).
Evaluates JobPosting against inclusion, exclusion, and location criteria.
Combines static config keywords with persistent dynamic keywords from SQLite.
"""

import re
from typing import List, Optional
from config.settings import FilterConfig
from src.filters.dynamic_keywords import DynamicKeywordStore
from src.models.canonical_job import JobPosting
from src.models.filter_rules import FilterMatchResult
from src.utils.logger import setup_logger

logger = setup_logger("filter")


class JobFilterEngine:
    """
    Applies configurable inclusion/exclusion keyword rules and location filters.
    """

    def __init__(self, config: FilterConfig, keyword_store: Optional[DynamicKeywordStore] = None):
        self.config = config
        self.keyword_store = keyword_store
        self._refresh_patterns()

    def _refresh_patterns(self) -> None:
        """Compiles regex patterns from both config and dynamic store."""
        includes = list(self.config.include_keywords)
        excludes = list(self.config.exclude_keywords)

        if self.keyword_store:
            dyn_inc = self.keyword_store.get_all_dynamic_keywords("include")
            dyn_exc = self.keyword_store.get_all_dynamic_keywords("exclude")
            includes.extend([k for k in dyn_inc if k not in includes])
            excludes.extend([k for k in dyn_exc if k not in excludes])

        self.current_includes = includes
        self.current_excludes = excludes

        self._include_patterns = [
            self._compile_pattern(kw, self.config.case_sensitive)
            for kw in includes
            if kw.strip()
        ]
        self._exclude_patterns = [
            self._compile_pattern(kw, self.config.case_sensitive)
            for kw in excludes
            if kw.strip()
        ]

    def reload(self) -> None:
        """Reloads dynamic keywords and recompiles regex patterns."""
        self._refresh_patterns()

    @staticmethod
    def _compile_pattern(keyword: str, case_sensitive: bool) -> re.Pattern:
        """
        Compiles a keyword into a word-boundary regex pattern.
        Handles multi-word phrases and symbols safely.
        """
        escaped = re.escape(keyword.strip())
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.compile(rf"\b{escaped}\b", flags)

    def evaluate(self, job: JobPosting) -> FilterMatchResult:
        """
        Evaluates a single JobPosting against filter criteria and deadline validity.
        Returns a FilterMatchResult indicating whether it passes.
        """
        # Ensure latest patterns are loaded
        self._refresh_patterns()

        # 0. Check Deadline / Expiration: Skip jobs whose application deadline has already passed
        if job.deadline:
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            if job.deadline < today:
                return FilterMatchResult(
                    is_match=False,
                    reason=f"Application deadline has passed (expired on {job.deadline.strftime('%Y-%m-%d')}).",
                )

        # Search target text includes title, company, description, and tags
        search_text = f"{job.title} {job.company} {' '.join(job.tags)} {job.description[:1000]}"

        # 1. Check Exclude Keywords First
        matched_excludes: List[str] = []
        for kw, pattern in zip(self.current_excludes, self._exclude_patterns):
            if pattern.search(search_text):
                matched_excludes.append(kw)

        if matched_excludes:
            return FilterMatchResult(
                is_match=False,
                matched_exclude_keywords=matched_excludes,
                reason=f"Matched exclude keywords: {', '.join(matched_excludes)}",
            )

        # 2. Check Include Keywords
        matched_includes: List[str] = []
        if not self._include_patterns:
            # If no include keywords defined, pass everything by default
            is_include_matched = True
        else:
            for kw, pattern in zip(self.current_includes, self._include_patterns):
                if pattern.search(search_text):
                    matched_includes.append(kw)
            is_include_matched = len(matched_includes) > 0

        if not is_include_matched:
            return FilterMatchResult(
                is_match=False,
                reason="Did not match any required include keywords.",
            )

        # 3. Check Location (if strict location is required)
        matched_location: Optional[str] = None
        if self.config.require_remote_or_africa and self.config.locations:
            loc_text = f"{job.location} {job.title}".lower()
            is_loc_match = any(loc.lower() in loc_text for loc in self.config.locations)
            if not is_loc_match and not job.remote_flag:
                return FilterMatchResult(
                    is_match=False,
                    reason=f"Location [{job.location}] did not match target regions {self.config.locations}",
                )

        return FilterMatchResult(
            is_match=True,
            matched_include_keywords=matched_includes,
            matched_exclude_keywords=[],
            matched_location=job.location,
            reason="Passed all filter rules.",
        )

    def filter_batch(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """Filters a list of jobs, returning only those that match the criteria."""
        passed_jobs: List[JobPosting] = []
        for job in jobs:
            result = self.evaluate(job)
            if result.is_match:
                logger.info(
                    f"Job matched filters: [{job.title} @ {job.company}] (Keywords: {result.matched_include_keywords})"
                )
                passed_jobs.append(job)
            else:
                logger.debug(f"Job rejected: [{job.title} @ {job.company}] -> {result.reason}")

        logger.info(f"Filter Engine: {len(passed_jobs)} passed out of {len(jobs)} postings.")
        return passed_jobs
