"""
Scheduler Module (FR-6).
Runs the Job Alert Pipeline on a recurring schedule using APScheduler.
"""

import time
from apscheduler.schedulers.blocking import BlockingScheduler
from config.settings import AppConfig
from src.orchestrator.pipeline import JobAlertPipeline
from src.utils.logger import setup_logger

logger = setup_logger("scheduler")


class PipelineScheduler:
    """Manages scheduled unattended execution of the job alert pipeline."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.pipeline = JobAlertPipeline(config)
        self.scheduler = BlockingScheduler()

    def start(self) -> None:
        """Starts the scheduler in the foreground."""
        logger.info("Initializing Job Alert Bot Scheduler...")

        # Verify connectivity first
        if not self.pipeline.verify_system():
            logger.warning("One or more system pre-flight checks failed. Check configuration.")

        interval = self.config.scheduler.interval_minutes
        logger.info(f"Scheduling pipeline run every {interval} minutes.")

        self.scheduler.add_job(
            self.pipeline.run_pipeline,
            "interval",
            minutes=interval,
            id="job_scrape_pipeline",
            replace_existing=True,
        )

        # Trigger immediate run on startup if configured
        if self.config.scheduler.run_on_startup:
            logger.info("Triggering initial run on boot...")
            self.pipeline.run_pipeline()

        logger.info("Scheduler running. Press Ctrl+C to terminate.")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler terminated by user.")
