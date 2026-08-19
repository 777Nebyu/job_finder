"""
Job Alert Bot — Gradio Web App & 24/7 Engine for Hugging Face Spaces.
Runs the background scraper scheduler, Telegram bot polling, and a live web dashboard.
"""

import asyncio
from datetime import datetime, timezone
import inspect
import threading
import time
import gradio as gr
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from config.settings import AppConfig
from src.filters.dynamic_keywords import DynamicKeywordStore
from src.notifiers.telegram_commands import TelegramCommandHandler
from src.orchestrator.pipeline import JobAlertPipeline
from src.storage.database import DatabaseManager
from src.storage.repository import JobRepository
from src.utils.logger import setup_logger

logger = setup_logger("gradio_app")

# Initialize Pipeline & Services
config = AppConfig.load_from_file("config/config.yaml")
pipeline = JobAlertPipeline(config)
db_manager = pipeline.db_manager
repository = pipeline.repository
keyword_store = pipeline.keyword_store
command_handler = TelegramCommandHandler(
    config=config,
    pipeline=pipeline,
    db_manager=db_manager,
    keyword_store=keyword_store,
)

start_time = datetime.now(timezone.utc)

# ------------------------------------------------------------------------------
# 1. Background Services (APScheduler + Telegram Bot Polling)
# ------------------------------------------------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(
    pipeline.run_pipeline,
    "interval",
    minutes=config.scheduler.interval_minutes,
    id="job_scrape_pipeline",
    replace_existing=True,
)
scheduler.start()


def run_telegram_polling():
    """Runs Telegram bot polling in a dedicated background thread with its own event loop."""
    if not config.bot.telegram_token:
        return

    try:
        logger.info("Starting Telegram Bot command listener in background thread...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app = command_handler.create_application()
        app.run_polling(
            stop_signals=None,
            drop_pending_updates=True,
            close_loop=False,
        )
    except Exception as e:
        logger.error(f"Telegram polling thread error: {e}", exc_info=True)


tg_thread = threading.Thread(target=run_telegram_polling, daemon=True)
tg_thread.start()

# ------------------------------------------------------------------------------
# 2. Gradio Dashboard Helper Functions
# ------------------------------------------------------------------------------
def get_dashboard_stats():
    """Returns overview metrics."""
    total_jobs = repository.count_total_jobs()
    uptime = str(datetime.now(timezone.utc) - start_time).split(".")[0]
    dyn_kw = len(keyword_store.get_all_dynamic_keywords("include"))
    total_kw = len(config.filters.include_keywords) + dyn_kw
    return (
        "🟢 Running 24/7",
        str(total_jobs),
        str(total_kw),
        uptime,
    )


def fetch_stored_jobs(search_query: str = ""):
    """Fetch stored jobs into a DataFrame."""
    jobs = repository.get_recent_jobs(limit=100)
    if not jobs:
        return pd.DataFrame(columns=["Title", "Company", "Location", "Remote", "Source", "Date", "Link"])

    data = []
    q = search_query.lower().strip()
    for j in jobs:
        if q and q not in f"{j.title} {j.company} {j.location} {' '.join(j.tags)}".lower():
            continue
        data.append({
            "Title": j.title,
            "Company": j.company,
            "Location": j.location,
            "Remote": "✅ Yes" if j.remote_flag else "🏢 On-site",
            "Source": j.source,
            "Date": j.posted_date.strftime("%Y-%m-%d") if j.posted_date else "N/A",
            "Link": j.url,
        })
    return pd.DataFrame(data)


def trigger_manual_scrape():
    """Triggers an on-demand scrape cycle."""
    metrics = pipeline.run_pipeline()
    msg = (
        f"✅ Scrape Complete!\n\n"
        f"• Raw Fetched: {metrics.get('raw_fetched', 0)}\n"
        f"• Unique Saved: {metrics.get('unique_saved', 0)}\n"
        f"• Matched Criteria: {metrics.get('matched', 0)}\n"
        f"• Telegram Alerts Sent: {metrics.get('notified', 0)}"
    )
    return msg, fetch_stored_jobs()


def add_keyword_ui(kw: str):
    if not kw.strip():
        return "⚠️ Please enter a keyword.", get_keywords_text()
    ok, msg = keyword_store.add_keyword(kw.strip(), kind="include")
    pipeline.filter_engine.reload()
    return msg, get_keywords_text()


def remove_keyword_ui(kw: str):
    if not kw.strip():
        return "⚠️ Please enter a keyword.", get_keywords_text()
    ok, msg = keyword_store.remove_keyword(kw.strip())
    pipeline.filter_engine.reload()
    return msg, get_keywords_text()


def get_keywords_text():
    dyn = keyword_store.get_all_dynamic_keywords("include")
    all_inc = list(dict.fromkeys(config.filters.include_keywords + dyn))
    lines = [f"• {k}" for k in all_inc]
    return "\n".join(lines)


# ------------------------------------------------------------------------------
# 3. Gradio Interface Construction
# ------------------------------------------------------------------------------
with gr.Blocks(title="Job Alert Bot 24/7") as demo:
    gr.Markdown("# 🔔 Job Alert Bot — 24/7 Control Center")
    gr.Markdown("Automated multi-source scraper, deduplicator, and Telegram alert engine running continuously.")

    with gr.Row():
        status_box = gr.Textbox(label="System Status", value="🟢 Running 24/7", interactive=False)
        total_jobs_box = gr.Textbox(label="Total Jobs Stored", value=str(repository.count_total_jobs()), interactive=False)
        keywords_count_box = gr.Textbox(label="Active Keywords", value=str(len(config.filters.include_keywords)), interactive=False)
        uptime_box = gr.Textbox(label="Uptime", value="00:00:00", interactive=False)

    with gr.Tabs():
        with gr.TabItem("📋 Live Job Explorer"):
            with gr.Row():
                search_input = gr.Textbox(label="Search Jobs", placeholder="Filter by title, company, or keyword...")
                search_btn = gr.Button("🔍 Search")
            jobs_table = gr.Dataframe(value=fetch_stored_jobs, interactive=False)
            search_btn.click(fetch_stored_jobs, inputs=[search_input], outputs=[jobs_table])

        with gr.TabItem("🚀 On-Demand Scrape"):
            gr.Markdown("Click the button below to immediately trigger a scrape across Ethiojobs, Telegram Channels, RemoteOK, and Jobicy.")
            scrape_btn = gr.Button("⚡ Trigger Scrape Now", variant="primary")
            scrape_output = gr.Textbox(label="Scrape Results Summary", interactive=False)
            scrape_btn.click(trigger_manual_scrape, outputs=[scrape_output, jobs_table])

        with gr.TabItem("🎯 Keyword Filter Management"):
            with gr.Row():
                with gr.Column():
                    kw_input = gr.Textbox(label="New Keyword", placeholder="e.g. Flutter Developer, Receptionist")
                    with gr.Row():
                        add_btn = gr.Button("➕ Add Keyword", variant="primary")
                        rem_btn = gr.Button("➖ Remove Keyword", variant="stop")
                    kw_status = gr.Textbox(label="Status", interactive=False)
                with gr.Column():
                    kw_list_display = gr.Textbox(label="Currently Active Keywords", value=get_keywords_text, lines=10, interactive=False)

            add_btn.click(add_keyword_ui, inputs=[kw_input], outputs=[kw_status, kw_list_display])
            rem_btn.click(remove_keyword_ui, inputs=[kw_input], outputs=[kw_status, kw_list_display])

        with gr.TabItem("ℹ️ Telegram Bot Integration"):
            gr.Markdown(f"""
            ### Connected Telegram Destination:
            * **Bot Name:** `@sth7Bot` (`job_filtro`)
            * **Target Group:** `Job filter` (Chat ID: `-5412714799`)
            * **Scrape Interval:** Every `{config.scheduler.interval_minutes}` minutes
            
            ### Interactive Commands:
            Send any of these commands inside your Telegram group:
            * `/status` — View uptime and total stored postings.
            * `/scrape_now` — Trigger an immediate scrape cycle.
            * `/addkeyword <word>` — Add a new search keyword on the fly.
            * `/removekeyword <word>` — Remove an existing keyword.
            * `/listkeywords` — List all active keywords.
            * `/pause` & `/resume` — Control notifications.
            """)

    demo.load(get_dashboard_stats, outputs=[status_box, total_jobs_box, keywords_count_box, uptime_box])

if __name__ == "__main__":
    launch_kwargs = {
        "server_name": "0.0.0.0",
        "server_port": 7860,
    }
    if "ssr_mode" in inspect.signature(demo.launch).parameters:
        launch_kwargs["ssr_mode"] = False

    demo.launch(**launch_kwargs)
