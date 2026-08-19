"""
Job Alert Bot — Gradio Web App & 24/7 Autonomous Engine for Render.com & Cloud.
Runs the background scraper scheduler every 8 minutes, Telegram bot polling,
and keep-alive mechanisms to prevent free cloud containers from idling.
"""

import asyncio
from datetime import datetime, timezone
import inspect
import os
import threading
import time
import urllib.request
import gradio as gr
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from config.settings import AppConfig
from src.filters.dynamic_keywords import DynamicKeywordStore
from src.notifiers.telegram_commands import TelegramCommandHandler
from src.orchestrator.pipeline import JobAlertPipeline
from src.scrapers.dynamic_channels import DynamicChannelStore
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
channel_store = pipeline.channel_store
command_handler = TelegramCommandHandler(
    config=config,
    pipeline=pipeline,
    db_manager=db_manager,
    keyword_store=keyword_store,
    channel_store=channel_store,
)

start_time = datetime.now(timezone.utc)
last_run_time: datetime | None = None
run_count: int = 0

# ------------------------------------------------------------------------------
# 1. 24/7 Autonomous Scheduler (Runs every 8 minutes)
# ------------------------------------------------------------------------------
def execute_scheduled_scrape():
    """Executes the automatic recurring scrape cycle with full logging."""
    global last_run_time, run_count
    run_count += 1
    last_run_time = datetime.now(timezone.utc)
    command_handler.last_scrape_time = last_run_time

    logger.info(f"⏰ [AUTONOMOUS 8-MIN TRIGGER #{run_count}] Starting automatic job pipeline at {last_run_time.strftime('%H:%M:%S UTC')}...")
    try:
        metrics = pipeline.run_pipeline()
        logger.info(
            f"✅ [AUTONOMOUS RUN #{run_count} COMPLETE] Fetched: {metrics.get('raw_fetched', 0)} | "
            f"New Unique: {metrics.get('unique_saved', 0)} | "
            f"Matched: {metrics.get('matched', 0)} | "
            f"Alerts Dispatched: {metrics.get('notified', 0)}"
        )
    except Exception as exc:
        logger.error(f"❌ [AUTONOMOUS RUN ERROR]: {exc}", exc_info=True)


scheduler = BackgroundScheduler()
scheduler.add_job(
    execute_scheduled_scrape,
    "interval",
    minutes=config.scheduler.interval_minutes, # 8 minutes
    id="job_scrape_pipeline",
    replace_existing=True,
)
scheduler.start()

# Trigger immediate background scrape on boot
def initial_boot_scrape():
    time.sleep(5) # Brief delay to let web server bind
    logger.info("🚀 [STARTUP] Triggering initial scrape cycle on boot...")
    execute_scheduled_scrape()

boot_thread = threading.Thread(target=initial_boot_scrape, daemon=True)
boot_thread.start()

# ------------------------------------------------------------------------------
# 2. Telegram Bot Polling Thread
# ------------------------------------------------------------------------------
def run_telegram_polling():
    """Runs Telegram bot polling in a dedicated background thread."""
    if not config.bot.telegram_token:
        return

    try:
        logger.info("🤖 Starting Telegram Bot command listener in background thread...")
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
# 3. 24/7 Keep-Alive Self-Pinger (Prevents Free Host Spin-Down)
# ------------------------------------------------------------------------------
def run_keep_alive():
    """Pings local server every 5 minutes so Render/Cloud containers never sleep."""
    port = int(os.environ.get("PORT", 7860))
    url = f"http://127.0.0.1:{port}/"
    while True:
        time.sleep(300) # 5 minutes
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception:
            pass

keep_alive_thread = threading.Thread(target=run_keep_alive, daemon=True)
keep_alive_thread.start()

# ------------------------------------------------------------------------------
# 4. Gradio Dashboard UI
# ------------------------------------------------------------------------------
def get_dashboard_stats():
    total_jobs = repository.count_total_jobs()
    uptime = str(datetime.now(timezone.utc) - start_time).split(".")[0]
    dyn_kw = len(keyword_store.get_all_dynamic_keywords("include"))
    total_kw = len(config.filters.include_keywords) + dyn_kw
    last_str = last_run_time.strftime("%H:%M:%S UTC") if last_run_time else "Starting..."
    return (
        f"🟢 Active (Scraping every {config.scheduler.interval_minutes}m)",
        str(total_jobs),
        str(total_kw),
        f"{uptime} (Runs: {run_count})",
    )


def fetch_stored_jobs(search_query: str = ""):
    jobs = repository.get_recent_jobs(limit=100)
    if not jobs:
        return pd.DataFrame(columns=["Title", "Company", "Location", "Remote", "Deadline", "Source", "Link"])

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
            "Deadline": j.deadline.strftime("%Y-%m-%d") if j.deadline else "Open / Not stated",
            "Source": j.source,
            "Link": j.url,
        })
    return pd.DataFrame(data)


def trigger_manual_scrape():
    execute_scheduled_scrape()
    return "✅ Scrape completed across all sources!", fetch_stored_jobs()


def add_keyword_ui(kw: str):
    if not kw.strip():
        return "⚠️ Please enter a keyword.", get_keywords_text()
    added, _ = keyword_store.add_multiple_keywords(kw.strip(), kind="include")
    pipeline.filter_engine.reload()
    return f"✅ Added: {', '.join(added)}", get_keywords_text()


def remove_keyword_ui(kw: str):
    if not kw.strip():
        return "⚠️ Please enter a keyword.", get_keywords_text()
    removed, _ = keyword_store.remove_multiple_keywords(kw.strip())
    pipeline.filter_engine.reload()
    return f"✅ Removed: {', '.join(removed)}", get_keywords_text()


def get_keywords_text():
    dyn = keyword_store.get_all_dynamic_keywords("include")
    all_inc = list(dict.fromkeys(config.filters.include_keywords + dyn))
    lines = [f"• {k}" for k in all_inc]
    return "\n".join(lines)


def add_channel_ui(ch: str):
    if not ch.strip():
        return "⚠️ Please enter a Telegram channel handle.", get_channels_text()
    added, _ = channel_store.add_multiple_channels(ch.strip())
    return f"✅ Added: {', '.join(added)}", get_channels_text()


def remove_channel_ui(ch: str):
    if not ch.strip():
        return "⚠️ Please enter a Telegram channel handle.", get_channels_text()
    removed, _ = channel_store.remove_multiple_channels(ch.strip())
    return f"✅ Removed: {', '.join(removed)}", get_channels_text()


def get_channels_text():
    cfg_channels = []
    src_cfg = config.get_source_config("telegram_channels")
    if src_cfg.channels:
        cfg_channels = src_cfg.channels

    defaults = [
        "freelance_ethio",
        "Ethiojobsofficial",
        "hahujobs",
        "shegerjobs",
        "harmeejobs",
        "effoi_jobs",
        "elelanajobs",
        "qefirajobs",
        "asham_jobs",
        "tikvahjobs",
    ]
    dyn = channel_store.get_all_dynamic_channels()
    all_ch = list(dict.fromkeys(cfg_channels + defaults + dyn))
    lines = [f"• @{c}" for c in all_ch]
    return "\n".join(lines)


with gr.Blocks(title="Job Alert Bot 24/7") as demo:
    gr.Markdown("# 🔔 Job Alert Bot — 24/7 Autonomous Control Center")
    gr.Markdown("Automated multi-source scraper, deduplicator, deadline evaluator, and Telegram alert engine running every 8 minutes.")

    with gr.Row():
        status_box = gr.Textbox(label="System Status", value="🟢 Active (Every 8m)", interactive=False)
        total_jobs_box = gr.Textbox(label="Total Jobs Stored", value=str(repository.count_total_jobs()), interactive=False)
        keywords_count_box = gr.Textbox(label="Active Keywords", value=str(len(config.filters.include_keywords)), interactive=False)
        uptime_box = gr.Textbox(label="Uptime & Execution Count", value="00:00:00", interactive=False)

    with gr.Tabs():
        with gr.TabItem("📋 Live Job Explorer"):
            with gr.Row():
                search_input = gr.Textbox(label="Search Jobs", placeholder="Filter by title, company, location, or keyword...")
                search_btn = gr.Button("🔍 Search")
            jobs_table = gr.Dataframe(value=fetch_stored_jobs, interactive=False)
            search_btn.click(fetch_stored_jobs, inputs=[search_input], outputs=[jobs_table])

        with gr.TabItem("🚀 On-Demand Scrape"):
            gr.Markdown("Click the button below to immediately trigger an on-demand scrape cycle.")
            scrape_btn = gr.Button("⚡ Trigger Scrape Now", variant="primary")
            scrape_output = gr.Textbox(label="Scrape Results Summary", interactive=False)
            scrape_btn.click(trigger_manual_scrape, outputs=[scrape_output, jobs_table])

        with gr.TabItem("🎯 Keyword Filters"):
            with gr.Row():
                with gr.Column():
                    kw_input = gr.Textbox(label="New Keyword(s)", placeholder="e.g. IT Officer, Receptionist, Data Analyst")
                    with gr.Row():
                        add_btn = gr.Button("➕ Add Keyword(s)", variant="primary")
                        rem_btn = gr.Button("➖ Remove Keyword(s)", variant="stop")
                    kw_status = gr.Textbox(label="Status", interactive=False)
                with gr.Column():
                    kw_list_display = gr.Textbox(label="Currently Active Keywords", value=get_keywords_text, lines=10, interactive=False)

            add_btn.click(add_keyword_ui, inputs=[kw_input], outputs=[kw_status, kw_list_display])
            rem_btn.click(remove_keyword_ui, inputs=[kw_input], outputs=[kw_status, kw_list_display])

        with gr.TabItem("📡 Monitored Telegram Channels"):
            with gr.Row():
                with gr.Column():
                    ch_input = gr.Textbox(label="New Telegram Channel Handle(s)", placeholder="e.g. @harmeejobs @effoi_jobs")
                    with gr.Row():
                        add_ch_btn = gr.Button("➕ Add Channel(s)", variant="primary")
                        rem_ch_btn = gr.Button("➖ Remove Channel(s)", variant="stop")
                    ch_status = gr.Textbox(label="Status", interactive=False)
                with gr.Column():
                    ch_list_display = gr.Textbox(label="Currently Monitored Channels", value=get_channels_text, lines=10, interactive=False)

            add_ch_btn.click(add_channel_ui, inputs=[ch_input], outputs=[ch_status, ch_list_display])
            rem_ch_btn.click(remove_channel_ui, inputs=[ch_input], outputs=[ch_status, ch_list_display])

        with gr.TabItem("ℹ️ Telegram Bot Integration"):
            gr.Markdown(f"""
            ### Connected Telegram Destination:
            * **Bot Name:** `@sth7Bot` (`job_filtro`)
            * **Target Group:** `Job filter` (Chat ID: `-5412714799`)
            * **Scrape Frequency:** Autonomous every `{config.scheduler.interval_minutes}` minutes
            
            ### Interactive Commands:
            Send any of these commands inside your Telegram group:
            * `/status` — View uptime, execution count, and total stored postings.
            * `/scrape_now` — Trigger an immediate on-demand scrape cycle.
            * `/addkeyword <word1, word2>` — Add search keywords.
            * `/removekeyword <word1, word2>` — Remove search keywords.
            * `/listkeywords` — List all active keywords.
            * `/addchannel <@ch1 @ch2>` — Add Telegram channels.
            * `/removechannel <@ch1 @ch2>` — Remove Telegram channels.
            * `/listchannels` — List all monitored channels.
            * `/clear` — Clean chat history or reset keywords/channels.
            * `/pause` & `/resume` — Control notifications.
            """)

    demo.load(get_dashboard_stats, outputs=[status_box, total_jobs_box, keywords_count_box, uptime_box])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    launch_kwargs = {
        "server_name": "0.0.0.0",
        "server_port": port,
    }
    if "ssr_mode" in inspect.signature(demo.launch).parameters:
        launch_kwargs["ssr_mode"] = False

    demo.launch(**launch_kwargs)
