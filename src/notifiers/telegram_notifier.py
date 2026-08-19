"""
Telegram Notifier (FR-8 & FR-13).
Sends job alert messages via Telegram Bot API with connection verification and rate limiting.
"""

import time
from typing import Optional
import requests
from config.settings import BotConfig
from src.models.canonical_job import JobPosting
from src.notifiers.base import BaseNotifier
from src.notifiers.formatter import MessageFormatter
from src.utils.logger import setup_logger

logger = setup_logger("telegram_notifier")


class TelegramNotifier(BaseNotifier):
    """Dispatches job alerts to a Telegram chat, group, or channel."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.token = config.telegram_token.strip()
        self.chat_id = str(config.chat_id).strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.rate_limit_pause = config.rate_limit_per_second

    def verify_connection(self) -> bool:
        """
        FR-13: Verifies Telegram Bot token and target chat connectivity on startup.
        Logs clear, actionable errors if credentials or permissions are invalid.
        """
        if not self.token or not self.chat_id:
            logger.error("Telegram verification failed: Token or Chat ID is missing.")
            return False

        try:
            # 1. Verify Bot Token
            me_resp = requests.get(f"{self.base_url}/getMe", timeout=10)
            if me_resp.status_code != 200:
                logger.error(f"Telegram Bot Token is invalid: HTTP {me_resp.status_code} - {me_resp.text}")
                return False
            bot_info = me_resp.json().get("result", {})
            logger.info(f"Telegram Bot connected: @{bot_info.get('username')} ({bot_info.get('first_name')})")

            # 2. Verify Chat Reachability
            chat_resp = requests.post(
                f"{self.base_url}/getChat",
                json={"chat_id": self.chat_id},
                timeout=10,
            )
            if chat_resp.status_code != 200:
                logger.error(
                    f"Target Chat ID [{self.chat_id}] could not be reached: HTTP {chat_resp.status_code} - {chat_resp.text}. "
                    f"Ensure the bot has been added to the target group/channel and has message permissions."
                )
                return False

            chat_info = chat_resp.json().get("result", {})
            title = chat_info.get("title") or chat_info.get("username") or self.chat_id
            logger.info(f"Target Chat verified: '{title}' (ID: {self.chat_id})")
            return True

        except Exception as e:
            logger.error(f"Telegram connection check failed with exception: {e}")
            return False

    def send_notification(self, job: JobPosting) -> bool:
        """
        FR-8: Formats and sends a single job posting to the configured Telegram chat.
        """
        if not self.config.enabled:
            logger.debug("Telegram notifier is disabled. Skipping.")
            return False

        message_html = MessageFormatter.format_telegram_html(job)
        payload = {
            "chat_id": self.chat_id,
            "text": message_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=15,
            )

            if response.status_code == 200:
                logger.info(f"Telegram alert sent for: [{job.title} @ {job.company}]")
                # Rate limit pacing
                if self.rate_limit_pause > 0:
                    time.sleep(self.rate_limit_pause)
                return True
            else:
                logger.error(
                    f"Failed to send Telegram alert for [{job.title}]: HTTP {response.status_code} - {response.text}"
                )
                return False

        except Exception as exc:
            logger.error(f"Exception while sending Telegram message for [{job.title}]: {exc}")
            return False
