"""
Centralized Configuration Manager (Pydantic Settings).
Supports loading from config.yaml, .env files, and environment variables.
"""

from pathlib import Path
from typing import List, Optional
import os
import yaml
from pydantic import BaseModel, Field


class BotConfig(BaseModel):
    telegram_token: str = Field(default="", description="Telegram Bot Token from @BotFather")
    chat_id: str = Field(default="", description="Target Chat, Group, or Channel ID")
    mode: str = Field(default="telegram", description="telegram | console | both")
    rate_limit_per_second: float = Field(default=1.0, description="Pause between sent notifications in seconds")
    enabled: bool = Field(default=True, description="Whether notifications are active")


class SchedulerConfig(BaseModel):
    interval_minutes: int = Field(default=8, description="Pipeline run interval in minutes (scrapes every 8 mins)")
    run_on_startup: bool = Field(default=True, description="Whether to trigger a scrape immediately on boot")


class FilterConfig(BaseModel):
    include_keywords: List[str] = Field(default_factory=list, description="Keywords that must match (OR logic)")
    exclude_keywords: List[str] = Field(default_factory=list, description="Keywords that disqualify a posting")
    locations: List[str] = Field(default_factory=list, description="Target locations or regions")
    require_remote_or_africa: bool = Field(default=False, description="Strict location enforcement")
    case_sensitive: bool = Field(default=False, description="Whether keyword matching is case sensitive")


class DatabaseConfig(BaseModel):
    db_path: str = Field(default="data/jobs.db", description="Path to SQLite database")
    fuzzy_threshold: int = Field(default=85, description="Fuzzy deduplication score threshold (0-100)")


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    log_file: str = Field(default="logs/job_alert_bot.log", description="Path to log file")
    max_bytes: int = Field(default=10 * 1024 * 1024, description="Log rotation size in bytes")
    backup_count: int = Field(default=5, description="Number of rotated log backups")


class SourceConfig(BaseModel):
    enabled: bool = Field(default=True)
    url: Optional[str] = None
    max_pages: Optional[int] = 3
    max_jobs: Optional[int] = 50
    count: Optional[int] = 30
    custom_headers: Optional[dict] = None


class ScrapersConfig(BaseModel):
    default_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) JobAlertBot/1.0",
        description="User agent for HTTP scraping"
    )
    request_timeout_seconds: int = Field(default=15, description="Timeout for web requests in seconds")
    rate_limit_delay_seconds: float = Field(default=1.5, description="Polite delay between requests to same host")
    sources: dict[str, SourceConfig] = Field(default_factory=dict)


class AppConfig(BaseModel):
    bot: BotConfig = Field(default_factory=BotConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    filters: FilterConfig = Field(default_factory=FilterConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scrapers: ScrapersConfig = Field(default_factory=ScrapersConfig)

    @classmethod
    def load_from_file(cls, config_path: str = "config/config.yaml") -> "AppConfig":
        """Load configuration from a YAML file, falling back to defaults if missing."""
        path = Path(config_path)
        if not path.exists():
            # Try finding relative to project root
            base_dir = Path(__file__).resolve().parent.parent
            path = base_dir / config_path

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return cls(**data)
        
        return cls()

    def get_source_config(self, source_name: str) -> SourceConfig:
        """Helper to get config for a specific source."""
        return self.scrapers.sources.get(source_name, SourceConfig(enabled=True))
