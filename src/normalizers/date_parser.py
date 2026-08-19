"""
Universal Date Parser Utility.
Parses various timestamp formats (ISO, RFC 2822, relative dates, standard date strings) into datetime.date.
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

    # 1. Try ISO 8601 parsing (e.g. '2026-08-19T00:11:50.000000Z' or '2026-08-19')
    try:
        clean_iso = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_iso).date()
    except (ValueError, TypeError):
        pass

    # 2. Try RFC 2822 (e.g. 'Wed, 19 Aug 2026 00:00:00 GMT')
    try:
        dt = parsedate_to_datetime(raw)
        if dt:
            return dt.date()
    except Exception:
        pass

    # 3. Try relative dates ('X hours ago', 'X days ago', 'yesterday', 'today')
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
