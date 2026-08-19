"""
Job Alert Bot CLI Entrypoint.
Commands:
  run          - Execute a single end-to-end pipeline run
  daemon       - Run continuously on a schedule (FR-6)
  check        - Verify Telegram bot credentials and database connectivity (FR-13)
  test-source  - Test a single scraper source (e.g., ethiojobs, remoteok)
  stats        - Display database metrics and stored job statistics
"""

import argparse
import sys
from config.settings import AppConfig
from src.orchestrator.pipeline import JobAlertPipeline
from src.orchestrator.scheduler import PipelineScheduler
from src.scrapers.registry import ScraperRegistry
from src.storage.database import DatabaseManager
from src.storage.repository import JobRepository
from src.utils.logger import setup_logger

logger = setup_logger("cli")


def cmd_run(config: AppConfig, args):
    """Execute a single pipeline cycle."""
    pipeline = JobAlertPipeline(config)
    metrics = pipeline.run_pipeline()
    print("\n--- Pipeline Run Summary ---")
    for k, v in metrics.items():
        print(f"  {k.replace('_', ' ').capitalize()}: {v}")


def cmd_daemon(config: AppConfig, args):
    """Start continuous scheduled execution."""
    scheduler = PipelineScheduler(config)
    scheduler.start()


def cmd_check(config: AppConfig, args):
    """Verify system connectivity and database health."""
    print("--- System Pre-Flight Diagnostics ---")
    pipeline = JobAlertPipeline(config)
    is_ok = pipeline.verify_system()
    db_count = pipeline.repository.count_total_jobs()
    print(f"  Database Path : {config.database.db_path}")
    print(f"  Stored Jobs   : {db_count}")
    print(f"  System Health : {'PASSED (Ready)' if is_ok else 'WARNING (Check Logs)'}")


def cmd_test_source(config: AppConfig, args):
    """Test a specific scraper source."""
    source_name = args.source.lower()
    if source_name not in ScraperRegistry.list_available():
        print(f"Error: Unknown source '{source_name}'. Available sources: {ScraperRegistry.list_available()}")
        sys.exit(1)

    print(f"Testing scraper [{source_name}]...")
    src_cfg = config.get_source_config(source_name)
    kwargs = {}
    if src_cfg.url:
        kwargs["base_url"] = src_cfg.url
    if src_cfg.max_pages:
        kwargs["max_pages"] = src_cfg.max_pages

    scraper = ScraperRegistry.create_scraper(source_name, **kwargs)
    results = scraper.safe_fetch()

    print(f"\nSource [{source_name}] returned {len(results)} raw postings.")
    for i, job in enumerate(results[:5], 1):
        print(f"\n[{i}] {job.title}")
        print(f"    Company : {job.company}")
        print(f"    Location: {job.location} (Remote: {job.remote_flag})")
        print(f"    URL     : {job.url}")


def cmd_stats(config: AppConfig, args):
    """Display database statistics."""
    db = DatabaseManager(config.database.db_path)
    repo = JobRepository(db)
    total = repo.count_total_jobs()
    recent = repo.get_recent_jobs(limit=5)
    print(f"\n--- Stored Job Statistics ---")
    print(f"Total Stored Jobs: {total}")
    if recent:
        print("\nLatest 5 Stored Postings:")
        for j in recent:
            print(f"  - [{j.source}] {j.title} @ {j.company} ({j.first_seen.strftime('%Y-%m-%d %H:%M')})")


def main():
    parser = argparse.ArgumentParser(description="Job Alert Bot CLI")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="Path to config YAML file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    subparsers.add_parser("run", help="Run a single pipeline scrape & alert cycle")

    # daemon command
    subparsers.add_parser("daemon", help="Start background scheduler for unattended 24/7 scraping")

    # check command
    subparsers.add_parser("check", help="Verify Telegram bot credentials and system health")

    # test-source command
    p_test = subparsers.add_parser("test-source", help="Test a single scraper source")
    p_test.add_argument("source", help="Scraper source name (e.g. ethiojobs, remoteok, jobicy)")

    # stats command
    subparsers.add_parser("stats", help="Show database metrics and stored postings")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = AppConfig.load_from_file(args.config)

    commands = {
        "run": cmd_run,
        "daemon": cmd_daemon,
        "check": cmd_check,
        "test-source": cmd_test_source,
        "stats": cmd_stats,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        cmd_fn(config, args)


if __name__ == "__main__":
    main()
