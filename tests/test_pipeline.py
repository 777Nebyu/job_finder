"""
Integration tests for Module 6: End-to-End Pipeline Workflow.
"""

import tempfile
from pathlib import Path
from config.settings import AppConfig, BotConfig, DatabaseConfig, FilterConfig
from src.orchestrator.pipeline import JobAlertPipeline


def test_full_pipeline_run():
    """Verify that a full 5-stage pipeline run executes without error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_pipeline.db")
        config = AppConfig(
            bot=BotConfig(mode="console", enabled=True),
            database=DatabaseConfig(db_path=db_path),
            filters=FilterConfig(
                include_keywords=["Officer", "Specialist", "Engineer", "Manager", "Technician", "Consultant"],
                exclude_keywords=["unpaid"],
            ),
        )

        pipeline = JobAlertPipeline(config)
        metrics = pipeline.run_pipeline()

        assert metrics["raw_fetched"] > 0
        assert metrics["normalized"] == metrics["raw_fetched"]
        assert metrics["unique_saved"] > 0
        
        # Subsequent immediate run on same data should detect virtually all as duplicates
        second_run_metrics = pipeline.run_pipeline()
        assert second_run_metrics["unique_saved"] < metrics["unique_saved"]
