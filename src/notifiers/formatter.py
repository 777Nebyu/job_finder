"""
Job Alert Message Formatter.
Builds visually appealing, clickable Telegram HTML message cards.
"""

import html
from src.models.canonical_job import JobPosting


class MessageFormatter:
    """Formats canonical JobPosting instances into rich Telegram HTML cards."""

    @staticmethod
    def format_telegram_html(job: JobPosting) -> str:
        """
        Builds a clean Telegram HTML message card.
        Escapes HTML characters in dynamic data to prevent syntax breakage.
        """
        title = html.escape(job.title)
        company = html.escape(job.company)
        location = html.escape(job.location)
        source = html.escape(job.source.capitalize())
        url = job.url.strip()

        # Remote / On-site badge
        type_badge = "🌐 <b>Remote Eligible</b>" if job.remote_flag else "🏢 <b>On-site / Office</b>"

        # Tags string
        tags_str = ""
        if job.tags:
            tag_badges = [f"#{t.replace(' ', '_').replace('-', '_')}" for t in job.tags[:5]]
            tags_str = f"\n🏷️ <i>{html.escape(' '.join(tag_badges))}</i>"

        # Date string
        date_str = ""
        if job.posted_date:
            date_str = f"\n📅 <b>Posted:</b> {job.posted_date.strftime('%b %d, %Y')}"

        # Clean description preview (first 250 characters)
        desc_preview = ""
        if job.description:
            clean_desc = html.escape(job.description[:250].strip())
            if len(job.description) > 250:
                clean_desc += "..."
            desc_preview = f"\n\n📝 <i>{clean_desc}</i>"

        message = (
            f"🔔 <b>NEW JOB ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 <b>Role:</b> <code>{title}</code>\n"
            f"🏢 <b>Company:</b> {company}\n"
            f"📍 <b>Location:</b> {location}\n"
            f"{type_badge}\n"
            f"📡 <b>Source:</b> {source}"
            f"{date_str}"
            f"{tags_str}"
            f"{desc_preview}\n\n"
            f"👉 <a href=\"{url}\"><b>View Job &amp; Apply Now</b></a>"
        )
        return message

    @staticmethod
    def format_console_card(job: JobPosting) -> str:
        """Formats a job for terminal/console display."""
        return (
            f"\n[JOB ALERT] {job.title}\n"
            f"  Company : {job.company}\n"
            f"  Location: {job.location} (Remote: {job.remote_flag})\n"
            f"  Source  : {job.source}\n"
            f"  URL     : {job.url}\n"
        )
