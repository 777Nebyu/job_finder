"""
Scheduler and Bot Runner Module (FR-6).
Runs the Job Alert Pipeline on a recurring schedule alongside the interactive Telegram command bot.
"""

import asyncio
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from config.settings import AppConfig
from src.notifiers.telegram_commands import TelegramCommandHandler
from src.orchestrator.pipeline import JobAlertPipeline
from src.server.web_status import run_status_server
from src.utils.logger import setup_logger

logger = setup_logger("scheduler")


class PipelineScheduler:
    """Manages scheduled unattended execution and Telegram command polling."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.pipeline = JobAlertPipeline(config)
        self.scheduler = BackgroundScheduler()
        self.command_handler = TelegramCommandHandler(
            config=self.config,
            pipeline=self.pipeline,
            db_manager=self.pipeline.db_manager,
            keyword_store=self.pipeline.keyword_store,
        )

    def _scheduled_run(self):
        """Wrapper for periodic scraper execution."""
        try:
            self.command_handler.last_scrape_time = self.pipeline._init_scrapers and None
            metrics = self.pipeline.run_pipeline()
            self.command_handler.last_scrape_time = self.command_handler.last_scrape_time or None
        except Exception as e:
            logger.error(f"Error during scheduled pipeline run: {e}", exc_info=True)

    def start(self) -> None:
        """Starts the scheduler, status web server, and Telegram bot polling 24/7."""
        logger.info("Initializing Job Alert Bot 24/7 Service...")

        # 1. Start Hugging Face Status Dashboard (Port 7860)
        try:
            run_status_server(self.config, port=7860)
        except Exception as e:
            logger.warning(f"Could not start status web server on port 7860: {e}")

        # 2. Verify system pre-flight
        if not self.pipeline.verify_system():
            logger.warning("One or more system pre-flight checks failed. Check configuration.")

        # 2. Add recurring scraper job to background scheduler
        interval = self.config.scheduler.interval_minutes
        logger.info(f"Configuring recurring scraper job every {interval} minutes.")
        self.scheduler.add_job(
            self.pipeline.run_pipeline,
            "interval",
            minutes=interval,
            id="job_scrape_pipeline",
            replace_existing=True,
        )
        self.scheduler.start()

        # 3. Initial run on boot if configured
        if self.config.scheduler.run_on_startup:
            logger.info("Triggering initial scrape run on boot...")
            try:
                self.pipeline.run_pipeline()
            except Exception as e:
                logger.error(f"Initial scrape run error: {e}")

        # 4. Start interactive Telegram bot polling
        if self.config.bot.telegram_token:
            logger.info("Starting Telegram interactive command listener (/status, /scrape_now, /addkeyword)...")
            app = self.command_handler.create_application()
            try:
                app.run_polling(drop_pending_updates=True)
            except (KeyboardInterrupt, SystemExit):
                logger.info("Service interrupted by user.")
            finally:
                self.scheduler.shutdown()
        else:
            # Console / headless mode without Telegram polling
            logger.info("Running in headless scheduler mode. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                self.scheduler.shutdown()
                logger.info("Scheduler terminated.")
