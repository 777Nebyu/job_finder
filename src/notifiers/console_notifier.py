"""
Console Notifier for Local Development and Dry-Run Testing.
"""

from src.models.canonical_job import JobPosting
from src.notifiers.base import BaseNotifier
from src.notifiers.formatter import MessageFormatter
from src.utils.logger import setup_logger

logger = setup_logger("console_notifier")


class ConsoleNotifier(BaseNotifier):
    """Outputs formatted job alerts directly to the terminal."""

    def verify_connection(self) -> bool:
        logger.info("Console Notifier ready (Local Output Mode).")
        return True

    def send_notification(self, job: JobPosting) -> bool:
        card = MessageFormatter.format_console_card(job)
        print(card)
        return True
