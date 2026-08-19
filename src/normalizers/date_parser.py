"""
Universal Date and Deadline Parser Utility.
Parses publication timestamps and application deadline strings into standard datetime.date.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional
import re
from email.utils import parsedate_to_datetime


def parse_job_date(raw_date: Optional[str]) -> Optional[date]:
    """
    Parse a raw date string into a standard datetime.date object.
    Supports ISO 8601, RFC 2822, relative strings ('2 days ago'), and standard formats.
    """
    if not raw_date or not isinstance(raw_date, str):
        return None

    raw = raw_date.strip()
    if not raw:
        return None

    # 1. Try ISO 8601 parsing
    try:
        clean_iso = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_iso).date()
    except (ValueError, TypeError):
        pass

    # 2. Try RFC 2822
    try:
        dt = parsedate_to_datetime(raw)
        if dt:
            return dt.date()
    except Exception:
        pass

    # 3. Try relative dates
    lower = raw.lower()
    today = datetime.now(timezone.utc).date()
    if "today" in lower or "just now" in lower or "hour" in lower or "minute" in lower:
        return today
    if "yesterday" in lower:
        return today - timedelta(days=1)

    days_match = re.search(r"(\d+)\s*(?:days?|d)\s*ago", lower)
    if days_match:
        days = int(days_match.group(1))
        return today - timedelta(days=days)

    weeks_match = re.search(r"(\d+)\s*(?:weeks?|w)\s*ago", lower)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        return today - timedelta(weeks=weeks)

    months_match = re.search(r"(\d+)\s*(?:months?|m)\s*ago", lower)
    if months_match:
        months = int(months_match.group(1))
        return today - timedelta(days=months * 30)

    # 4. Common explicit format patterns
    date_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y/%m/%d",
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except (ValueError, TypeError):
            continue

    return None


def parse_deadline(raw_deadline: Optional[str]) -> Optional[date]:
    """
    Parse an application deadline date string.
    Handles formats like:
    - 'August 31st, 2026'
    - 'Aug 31, 2026'
    - 'September 1st, 2026'
    - '31/08/2026'
    - '2026-08-31'
    - 'Aug 31' (defaults to current year)
    - Relative deadlines: '5 days from now', 'in 3 days'
    """
    if not raw_deadline or not isinstance(raw_deadline, str):
        return None

    cleaned = raw_deadline.strip()
    if not cleaned:
        return None

    lower = cleaned.lower()
    today = datetime.now(timezone.utc).date()
    
    # Relative deadline: 'in X days' or 'X days from now'
    rel_match = re.search(r"(?:in\s*)?(\d+)\s*(?:days?|d)\s*(?:from\s*now)?", lower)
    if rel_match and ("in" in lower or "from now" in lower or "left" in lower):
        days = int(rel_match.group(1))
        return today + timedelta(days=days)

    # Remove ordinal suffixes: 1st, 2nd, 3rd, 4th, 26th, 31st
    cleaned = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", cleaned)
    cleaned = re.sub(r"[^\w\s\-\/\,]", " ", cleaned).strip()

    formats = [
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%b %d",
        "%B %d",
    ]

    current_year = today.year
    for fmt in formats:
        try:
            if "%Y" not in fmt and "%y" not in fmt:
                dt = datetime.strptime(f"{cleaned} {current_year}", f"{fmt} %Y")
            else:
                dt = datetime.strptime(cleaned, fmt)
            return dt.date()
        except (ValueError, TypeError):
            continue

    return None
