"""
Unit tests for Module 0: Configuration, Models, and Logger.
"""

import os
from datetime import datetime, date
import pytest
from config.settings import AppConfig
from src.models.canonical_job import JobPosting
from src.models.raw_job import RawJobPosting


def test_config_loading():
    """Verify that configuration loads yaml parameters accurately."""
    config = AppConfig.load_from_file("config/config.yaml")
    assert config.bot.telegram_token == "8680554660:AAEywFEIzVJ9cY9kmpThQlpxCLxoiHNcadg"
    assert config.bot.chat_id == "-5412714799"
    assert "IT OFFICER" in config.filters.include_keywords
    assert "receptionist" in config.filters.include_keywords
    assert config.scrapers.sources["ethiojobs"].enabled is True


def test_job_posting_hash_generation():
    """Verify deterministic dedupe hash calculation."""
    hash1 = JobPosting.compute_dedupe_hash(
        title="IT Officer",
        company="Global NGO",
        url="https://ethiojobs.net/jobs/123?ref=feed",
    )
    hash2 = JobPosting.compute_dedupe_hash(
        title="  it officer  ",
        company="global ngo",
        url="https://ethiojobs.net/jobs/123",
    )
    # They should match because case, whitespace, and tracking query params are normalized
    assert hash1 == hash2

    posting = JobPosting(
        source="ethiojobs",
        title="Database Administrator",
        company="Tech Corp",
        url="https://ethiojobs.net/jobs/dba",
    )
    posting.generate_and_set_hash()
    assert len(posting.dedupe_hash) == 64  # SHA-256 length


def test_raw_job_posting():
    """Verify RawJobPosting creation."""
    raw = RawJobPosting(
        source="ethiojobs",
        title="Receptionist",
        company="Hilton Addis",
        url="https://ethiojobs.net/jobs/receptionist",
    )
    assert raw.source == "ethiojobs"
    assert raw.title == "Receptionist"
    assert raw.company == "Hilton Addis"
