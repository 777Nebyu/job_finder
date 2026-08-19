"""
Resilient and Polite HTTP Client.
Handles user-agent spoofing, per-domain rate limiting, exponential backoff, and timeouts.
"""

import time
import urllib.parse
import urllib.robotparser
from typing import Any, Dict, Optional
import requests
from src.utils.logger import setup_logger

logger = setup_logger("http_client")


class ResilientHttpClient:
    """
    HTTP client enforcing polite scraping habits:
    - User-Agent identification
    - Configurable per-request delays
    - Automatic retries with exponential backoff
    - Timeout protections
    """

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 JobAlertBot/1.0",
        default_timeout: int = 15,
        rate_limit_delay: float = 1.5,
        max_retries: int = 3,
    ):
        self.user_agent = user_agent
        self.default_timeout = default_timeout
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self._last_request_time: Dict[str, float] = {}
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _respect_rate_limit(self, url: str) -> None:
        """Enforces minimum delay between requests to the same domain."""
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        now = time.time()
        last_time = self._last_request_time.get(domain, 0)
        elapsed = now - last_time

        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            time.sleep(sleep_time)

        self._last_request_time[domain] = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
    ) -> requests.Response:
        """Perform a polite HTTP GET request with retries."""
        timeout_val = timeout or self.default_timeout
        custom_headers = headers or {}

        for attempt in range(1, self.max_retries + 1):
            try:
                self._respect_rate_limit(url)
                response = self.session.get(
                    url,
                    params=params,
                    headers=custom_headers,
                    timeout=timeout_val,
                    allow_redirects=allow_redirects,
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"HTTP GET failed ({attempt}/{self.max_retries}) for {url}: {e}"
                )
                if attempt == self.max_retries:
                    raise e
                time.sleep(2 ** attempt)

        raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts.")

    def post(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """Perform a polite HTTP POST request with retries."""
        timeout_val = timeout or self.default_timeout
        custom_headers = headers or {}

        for attempt in range(1, self.max_retries + 1):
            try:
                self._respect_rate_limit(url)
                response = self.session.post(
                    url,
                    json=json_data,
                    data=data,
                    headers=custom_headers,
                    timeout=timeout_val,
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"HTTP POST failed ({attempt}/{self.max_retries}) for {url}: {e}"
                )
                if attempt == self.max_retries:
                    raise e
                time.sleep(2 ** attempt)

        raise RuntimeError(f"Failed to POST to {url} after {self.max_retries} attempts.")
