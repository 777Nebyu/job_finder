"""
Dual-Layer Deduplication Engine (FR-3 & FR-4).
- Layer 1: Intra-source SHA-256 Hash Matching (O(1))
- Layer 2: Cross-source Fuzzy String Matching via RapidFuzz
"""

from typing import List, Tuple
from rapidfuzz import fuzz
from src.models.canonical_job import JobPosting
from src.storage.repository import JobRepository
from src.utils.logger import setup_logger

logger = setup_logger("deduplicator")


class Deduplicator:
    """
    Evaluates new jobs against stored records to filter out duplicates.
    """

    def __init__(self, repository: JobRepository, fuzzy_threshold: int = 85):
        self.repository = repository
        self.fuzzy_threshold = fuzzy_threshold

    def is_duplicate(self, candidate: JobPosting, existing_jobs: List[JobPosting]) -> Tuple[bool, str]:
        """
        Check if candidate is a duplicate.
        Returns (is_duplicate: bool, reason: str).
        """
        # 1. Intra-source / Exact Hash Check (FR-3)
        candidate.generate_and_set_hash()
        if self.repository.is_hash_seen(candidate.dedupe_hash):
            return True, f"Exact hash match ({candidate.dedupe_hash[:8]}...) already exists."

        # 2. Cross-source Fuzzy Match (FR-4)
        candidate_key = f"{candidate.title.lower()} {candidate.company.lower()}"

        for stored in existing_jobs:
            stored_key = f"{stored.title.lower()} {stored.company.lower()}"

            # Fast exact match on title + company
            if candidate_key == stored_key:
                return True, f"Cross-source exact title/company match with Job #{stored.id} from [{stored.source}]."

            # Fuzzy similarity score
            score = fuzz.token_sort_ratio(candidate_key, stored_key)
            if score >= self.fuzzy_threshold:
                return True, f"Cross-source fuzzy match ({score:.1f}% similarity) with Job #{stored.id} from [{stored.source}]."

        return False, ""

    def filter_unique_postings(self, candidates: List[JobPosting]) -> List[JobPosting]:
        """
        Processes a list of candidates, returning only truly new and unique postings.
        Also persists new postings to the database.
        """
        existing_jobs = self.repository.get_recent_jobs(limit=1000)
        unique_postings: List[JobPosting] = []

        for candidate in candidates:
            is_dup, reason = self.is_duplicate(candidate, existing_jobs + unique_postings)
            if is_dup:
                logger.debug(f"Duplicate filtered: [{candidate.title} @ {candidate.company}] -> {reason}")
            else:
                # Save to database
                saved = self.repository.save_job(candidate)
                unique_postings.append(saved)

        logger.info(
            f"Deduplication complete: {len(unique_postings)} new unique postings found out of {len(candidates)} candidates."
        )
        return unique_postings
