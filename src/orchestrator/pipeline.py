"""
Pipeline Orchestrator.
Executes the complete 5-stage workflow:
Fetch (Stage 1) -> Normalize (Stage 2) -> Dedupe & Store (Stage 3) -> Filter (Stage 4) -> Notify (Stage 5)
"""

import time
from typing import Dict, List, Optional
from config.settings import AppConfig
from src.filters.dynamic_keywords import DynamicKeywordStore
from src.filters.keyword_filter import JobFilterEngine
from src.models.canonical_job import JobPosting
from src.models.raw_job import RawJobPosting
from src.normalizers.base_normalizer import JobNormalizer
from src.notifiers.base import BaseNotifier
from src.notifiers.console_notifier import ConsoleNotifier
from src.notifiers.telegram_notifier import TelegramNotifier
from src.scrapers.base import BaseScraper
from src.scrapers.dynamic_channels import DynamicChannelStore
from src.scrapers.registry import ScraperRegistry
from src.storage.database import DatabaseManager
from src.storage.deduplicator import Deduplicator
from src.storage.repository import JobRepository
from src.utils.logger import setup_logger

logger = setup_logger("pipeline")


class JobAlertPipeline:
    """
    Main pipeline coordinator that links all 5 modular subsystems.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load_from_file()
        
        # 1. Initialize Storage & Deduplicator (Module 3)
        self.db_manager = DatabaseManager(self.config.database.db_path)
        self.repository = JobRepository(self.db_manager)
        self.keyword_store = DynamicKeywordStore(self.db_manager)
        self.channel_store = DynamicChannelStore(self.db_manager)
        self.deduplicator = Deduplicator(
            repository=self.repository,
            fuzzy_threshold=self.config.database.fuzzy_threshold,
        )

        # 2. Initialize Filter Engine (Module 4)
        self.filter_engine = JobFilterEngine(self.config.filters, keyword_store=self.keyword_store)

        # 3. Initialize Notifiers (Module 5)
        self.notifiers: List[BaseNotifier] = []
        mode = self.config.bot.mode.lower()
        if mode in ["telegram", "both"] and self.config.bot.telegram_token:
            self.notifiers.append(TelegramNotifier(self.config.bot))
        if mode in ["console", "both"] or not self.notifiers:
            self.notifiers.append(ConsoleNotifier())

        # 4. Initialize Scrapers (Module 1)
        self.scrapers: List[BaseScraper] = []
        self._init_scrapers()

    def _init_scrapers(self) -> None:
        """Instantiate enabled scrapers from configuration."""
        for name in ScraperRegistry.list_available():
            src_cfg = self.config.get_source_config(name)
            if src_cfg.enabled:
                try:
                    kwargs = {
                        "rate_limit_delay": self.config.scrapers.rate_limit_delay_seconds,
                    }
                    if name == "telegram_channels":
                        kwargs["channel_store"] = self.channel_store
                        if src_cfg.channels:
                            kwargs["channels"] = src_cfg.channels
                    if src_cfg.url:
                        kwargs["base_url"] = src_cfg.url
                    if src_cfg.max_pages and name == "ethiojobs":
                        kwargs["max_pages"] = src_cfg.max_pages
                    if src_cfg.max_jobs and name == "remoteok":
                        kwargs["max_jobs"] = src_cfg.max_jobs
                    if src_cfg.count and name == "jobicy":
                        kwargs["count"] = src_cfg.count

                    scraper = ScraperRegistry.create_scraper(name, **kwargs)
                    self.scrapers.append(scraper)
                except Exception as e:
                    logger.error(f"Failed to initialize scraper [{name}]: {e}")

    def verify_system(self) -> bool:
        """Runs startup health checks across all components."""
        logger.info("Running pre-flight system checks...")
        all_ok = True
        for notifier in self.notifiers:
            if not notifier.verify_connection():
                all_ok = False
        return all_ok

    def run_pipeline(self) -> Dict[str, int]:
        """
        Executes a single end-to-end pipeline run across all 5 stages.
        Returns a metrics summary dict.
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("PIPELINE RUN STARTED")
        logger.info("=" * 60)

        # -------------------------------------------------------------
        # STAGE 1: Fetch Raw Postings from Enabled Scrapers
        # -------------------------------------------------------------
        logger.info(f"Stage 1: Fetching jobs from {len(self.scrapers)} active sources...")
        raw_postings: List[RawJobPosting] = []
        source_counts: Dict[str, int] = {}

        for scraper in self.scrapers:
            postings = scraper.safe_fetch()
            raw_postings.extend(postings)
            source_counts[scraper.source_name] = len(postings)
            logger.info(f"  Source [{scraper.source_name}]: {len(postings)} postings fetched.")

        total_raw = len(raw_postings)
        logger.info(f"Stage 1 Complete: {total_raw} raw postings collected.")

        if total_raw == 0:
            logger.info("No postings fetched. Pipeline cycle finished.")
            return {"raw_fetched": 0, "normalized": 0, "unique_saved": 0, "matched": 0, "notified": 0}

        # -------------------------------------------------------------
        # STAGE 2: Normalization
        # -------------------------------------------------------------
        logger.info("Stage 2: Normalizing raw postings into canonical JobPosting schema...")
        normalized_jobs = JobNormalizer.normalize_batch(raw_postings)
        logger.info(f"Stage 2 Complete: {len(normalized_jobs)} postings successfully normalized.")

        # -------------------------------------------------------------
        # STAGE 3: Deduplication & Persistent Storage
        # -------------------------------------------------------------
        logger.info("Stage 3: Deduplicating (Intra-source SHA-256 + Cross-source Fuzzy RapidFuzz)...")
        unique_jobs = self.deduplicator.filter_unique_postings(normalized_jobs)
        logger.info(f"Stage 3 Complete: {len(unique_jobs)} new unique postings stored in SQLite.")

        if not unique_jobs:
            logger.info("No new unique postings found in this run. Pipeline cycle complete.")
            return {
                "raw_fetched": total_raw,
                "normalized": len(normalized_jobs),
                "unique_saved": 0,
                "matched": 0,
                "notified": 0,
            }

        # -------------------------------------------------------------
        # STAGE 4: Keyword & Exclusion Filtering
        # -------------------------------------------------------------
        logger.info(f"Stage 4: Filtering {len(unique_jobs)} postings by user keywords...")
        matched_jobs = self.filter_engine.filter_batch(unique_jobs)
        logger.info(f"Stage 4 Complete: {len(matched_jobs)} postings matched target criteria.")

        # -------------------------------------------------------------
        # STAGE 5: Notification Dispatch
        # -------------------------------------------------------------
        logger.info(f"Stage 5: Dispatching notifications for {len(matched_jobs)} matching postings...")
        notified_count = 0
        for job in matched_jobs:
            success = False
            for notifier in self.notifiers:
                if notifier.send_notification(job):
                    success = True
            if success and job.id:
                self.repository.mark_as_notified(job.id)
                notified_count += 1

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(
            f"PIPELINE RUN COMPLETED in {elapsed:.2f}s | "
            f"Fetched: {total_raw} | Unique New: {len(unique_jobs)} | "
            f"Matched: {len(matched_jobs)} | Alerts Sent: {notified_count}"
        )
        logger.info("=" * 60)

        return {
            "raw_fetched": total_raw,
            "normalized": len(normalized_jobs),
            "unique_saved": len(unique_jobs),
            "matched": len(matched_jobs),
            "notified": notified_count,
        }
