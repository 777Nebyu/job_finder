"""
Telegram Channel Web Scraper.
Scrapes public job postings from Ethiopian & African Telegram job channels via public web previews (https://t.me/s/<channel>).
Requires no Telegram API keys or phone logins.
Supports dynamic channels and application deadline parsing.
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.raw_job import RawJobPosting
from src.scrapers.base import BaseScraper
from src.scrapers.dynamic_channels import DynamicChannelStore
from src.scrapers.registry import ScraperRegistry


@ScraperRegistry.register("telegram_channels")
class TelegramChannelScraper(BaseScraper):
    """
    Scrapes job postings from public Telegram channels via web previews.
    Default monitored channels:
    - @freelance_ethio (Afriwork official feed)
    - @Ethiojobsofficial
    - @hahujobs
    - @shegerjobs
    - @harmeejobs
    - @effoi_jobs
    """

    source_name = "telegram_channels"

    DEFAULT_CHANNELS = [
        "freelance_ethio",
        "Ethiojobsofficial",
        "hahujobs",
        "shegerjobs",
        "harmeejobs",
        "effoi_jobs",
    ]

    def __init__(
        self,
        channels: Optional[List[str]] = None,
        max_posts_per_channel: int = 30,
        channel_store: Optional[DynamicChannelStore] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.default_channels = channels or self.DEFAULT_CHANNELS
        self.max_posts_per_channel = max_posts_per_channel
        self.channel_store = channel_store

    def get_active_channels(self) -> List[str]:
        """Returns merged list of default and dynamically added channels."""
        channels = list(self.default_channels)
        if self.channel_store:
            dynamic_list = self.channel_store.get_all_dynamic_channels()
            for ch in dynamic_list:
                if ch not in channels:
                    channels.append(ch)
        return channels

    def fetch(self) -> List[RawJobPosting]:
        all_postings: List[RawJobPosting] = []
        active_channels = self.get_active_channels()

        self.logger.info(f"Scraping {len(active_channels)} Telegram channels: {active_channels}")

        for channel in active_channels:
            url = f"https://t.me/s/{channel.lstrip('@')}"
            self.logger.debug(f"Fetching Telegram channel @{channel}: {url}")

            try:
                response = self.client.get(url)
            except Exception as e:
                self.logger.warning(f"Failed to fetch Telegram channel @{channel}: {e}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            messages = soup.find_all("div", class_="tgme_widget_message_wrap")

            channel_count = 0
            for msg_wrap in reversed(messages):
                if channel_count >= self.max_posts_per_channel:
                    break

                posting = self._parse_message(msg_wrap, channel)
                if posting:
                    all_postings.append(posting)
                    channel_count += 1

            self.logger.info(f"Telegram channel @{channel}: extracted {channel_count} postings.")

        return all_postings

    def _parse_message(self, msg_elem, channel_name: str) -> Optional[RawJobPosting]:
        """Parses a single Telegram message container into RawJobPosting with deadline."""
        text_div = msg_elem.find("div", class_="tgme_widget_message_text")
        date_elem = msg_elem.find("time")
        link_elem = msg_elem.find("a", class_="tgme_widget_message_date")

        if not text_div or not link_elem:
            return None

        raw_text = text_div.get_text(separator="\n").strip()
        if len(raw_text) < 15:
            return None

        # 1. Title Extraction
        title = None
        m_title = re.search(r"(?:Job\s*Title|Position|Role)\s*:\s*([^<\n]+)", raw_text, re.I)
        if m_title:
            title = m_title.group(1).strip()

        if not title:
            first_b = text_div.find(["b", "strong"])
            if first_b and len(first_b.get_text(strip=True)) > 3:
                cand = first_b.get_text(strip=True)
                if not any(k in cand.lower() for k in ["description", "about", "requirement", "qualif", "deadline", "job title", "vacancy"]):
                    title = cand

        if not title:
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            if lines:
                title = lines[0].lstrip("🔘🔹📌- •")

        if not title or len(title) < 3:
            return None

        title = title.split("\n")[0].strip()

        # 2. Company Extraction
        company = None
        m_comp = re.search(r"(?:Company|Employer|Organization)\s*:\s*([^<\n]+)", raw_text, re.I)
        if m_comp:
            company = m_comp.group(1).strip()
        elif " at " in title:
            parts = title.split(" at ")
            title = parts[0].strip()
            company = parts[1].strip()
        elif " @ " in title:
            parts = title.split(" @ ")
            title = parts[0].strip()
            company = parts[1].strip()

        if not company:
            company = f"@{channel_name}"

        # 3. Location
        location = "Ethiopia"
        m_loc = re.search(r"(?:Location|Place\s*of\s*Work|Work\s*Location)\s*:\s*([^<\n]+)", raw_text, re.I)
        if m_loc:
            location = m_loc.group(1).strip()

        # 4. Deadline Extraction
        deadline_raw = None
        m_dl = re.search(r"(?:Deadline|Closing\s*Date|Apply\s*Before|Expires)\s*:\s*([^\n<,]+(?:\s*,\s*\d{4})?)", raw_text, re.I)
        if m_dl:
            deadline_raw = m_dl.group(1).strip()

        is_remote = "remote" in raw_text.lower() or "remote" in title.lower()
        post_url = link_elem.get("href", f"https://t.me/s/{channel_name}")
        dt_str = date_elem.get("datetime") if date_elem else None
        tags = re.findall(r"#([a-zA-Z0-9_]+)", raw_text)
        tags.append(f"@{channel_name}")

        return RawJobPosting(
            source=f"tg_{channel_name.lower()}",
            raw_id=post_url.split("/")[-1] if "/" in post_url else None,
            title=title,
            company=company,
            location=location,
            remote_flag=is_remote,
            url=post_url,
            posted_date_raw=dt_str,
            deadline_raw=deadline_raw,
            description=raw_text,
            tags=tags,
        )
