"""
Unit tests for Module 5: Telegram Formatting and Notifier (FR-8, FR-13).
"""

from src.models.canonical_job import JobPosting
from src.notifiers.formatter import MessageFormatter


def test_telegram_html_card_formatting():
    """FR-8: Verify HTML escaping and message card structure."""
    job = JobPosting(
        source="ethiojobs",
        title="IT Officer <Urgent>",
        company="Global & Local NGO",
        location="Addis Ababa, Ethiopia",
        remote_flag=False,
        url="https://ethiojobs.net/jobs/it-101",
        description="Responsible for internal network and server maintenance.",
        tags=["IT Support", "Networking"],
    )

    card = MessageFormatter.format_telegram_html(job)
    assert "<b>Role:</b> <code>IT Officer &lt;Urgent&gt;</code>" in card
    assert "Global &amp; Local NGO" in card
    assert "https://ethiojobs.net/jobs/it-101" in card
    assert "On-site / Office" in card
