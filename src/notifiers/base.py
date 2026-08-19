"""
Base Notifier Interface Contract.
"""

from abc import ABC, abstractmethod
from typing import List
from src.models.canonical_job import JobPosting


class BaseNotifier(ABC):
    """Abstract interface for all notification dispatchers."""

    @abstractmethod
    def verify_connection(self) -> bool:
        """Verify API credentials and target chat reachability on startup (FR-13)."""
        pass

    @abstractmethod
    def send_notification(self, job: JobPosting) -> bool:
        """Send an alert for a single job posting."""
        pass

    def send_batch(self, jobs: List[JobPosting]) -> int:
        """Send alerts for a batch of jobs. Returns number of successful deliveries."""
        sent_count = 0
        for job in jobs:
            if self.send_notification(job):
                sent_count += 1
        return sent_count
