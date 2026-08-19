"""
Interactive Telegram Bot Command Handlers.
Implements interactive commands for runtime control:
/start, /help, /status, /addkeyword, /removekeyword, /listkeywords, /scrape_now, /pause, /resume
"""

from datetime import datetime, timezone
import html
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from config.settings import AppConfig
from src.filters.dynamic_keywords import DynamicKeywordStore
from src.storage.database import DatabaseManager
from src.storage.repository import JobRepository
from src.utils.logger import setup_logger

logger = setup_logger("telegram_commands")


class TelegramCommandHandler:
    """
    Manages interactive Telegram bot commands.
    """

    def __init__(
        self,
        config: AppConfig,
        pipeline=None,
        db_manager: Optional[DatabaseManager] = None,
        keyword_store: Optional[DynamicKeywordStore] = None,
    ):
        self.config = config
        self.pipeline = pipeline
        self.db_manager = db_manager or DatabaseManager(config.database.db_path)
        self.repository = JobRepository(self.db_manager)
        self.keyword_store = keyword_store or DynamicKeywordStore(self.db_manager)
        self.is_paused = not config.bot.enabled
        self.last_scrape_time: Optional[datetime] = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /start and /help commands."""
        help_text = (
            "👋 <b>Welcome to Job Alert Bot!</b>\n\n"
            "Here are the available commands:\n\n"
            "📊 <b>/status</b> — System health, total jobs stored, and scraper status\n"
            "🔍 <b>/scrape_now</b> — Trigger an immediate scrape and alert cycle\n"
            "➕ <b>/addkeyword &lt;keyword&gt;</b> — Add a new search keyword on the fly\n"
            "➖ <b>/removekeyword &lt;keyword&gt;</b> — Remove an existing dynamic keyword\n"
            "📋 <b>/listkeywords</b> — View all active include & exclude keywords\n"
            "⏸️ <b>/pause</b> — Temporarily pause automated alerts\n"
            "▶️ <b>/resume</b> — Resume automated alerts\n"
            "ℹ️ <b>/help</b> — Show this help menu\n\n"
            "<i>The bot continuously scrapes Ethiojobs, Telegram Channels, RemoteOK, and Jobicy 24/7!</i>"
        )
        if update.effective_message:
            await update.effective_message.reply_html(help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /status command."""
        total_jobs = self.repository.count_total_jobs()
        dynamic_count = len(self.keyword_store.get_all_dynamic_keywords("include"))
        total_keywords = len(self.config.filters.include_keywords) + dynamic_count
        status_state = "⏸️ <b>Paused</b>" if self.is_paused else "🟢 <b>Active (Running 24/7)</b>"

        last_run_str = (
            self.last_scrape_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            if self.last_scrape_time
            else "Pending first run"
        )

        status_text = (
            "📊 <b>Job Alert Bot — System Status</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>State:</b> {status_state}\n"
            f"📦 <b>Total Stored Postings:</b> <code>{total_jobs}</code>\n"
            f"🎯 <b>Active Target Keywords:</b> <code>{total_keywords}</code>\n"
            f"⏱️ <b>Scrape Interval:</b> Every <code>{self.config.scheduler.interval_minutes}m</code>\n"
            f"🕒 <b>Last Pipeline Cycle:</b> <code>{last_run_str}</code>\n"
            f"📡 <b>Monitored Sources:</b> Ethiojobs, Telegram Channels, RemoteOK, Jobicy\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        if update.effective_message:
            await update.effective_message.reply_html(status_text)

    async def add_keyword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /addkeyword <word> command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify a keyword to add.\nExample: /addkeyword Python Developer"
                )
            return

        kw = " ".join(context.args).strip()
        success, msg = self.keyword_store.add_keyword(kw, kind="include")
        if self.pipeline and hasattr(self.pipeline, "filter_engine"):
            self.pipeline.filter_engine.reload()

        if update.effective_message:
            await update.effective_message.reply_text(msg)

    async def remove_keyword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /removekeyword <word> command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify a keyword to remove.\nExample: /removekeyword Python Developer"
                )
            return

        kw = " ".join(context.args).strip()
        success, msg = self.keyword_store.remove_keyword(kw)
        if self.pipeline and hasattr(self.pipeline, "filter_engine"):
            self.pipeline.filter_engine.reload()

        if update.effective_message:
            await update.effective_message.reply_text(msg)

    async def list_keywords_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /listkeywords command."""
        dyn_includes = self.keyword_store.get_all_dynamic_keywords("include")
        config_includes = self.config.filters.include_keywords
        all_includes = list(dict.fromkeys(config_includes + dyn_includes))
        all_excludes = self.config.filters.exclude_keywords

        inc_items = "\n".join([f"  • {html.escape(k)}" for k in all_includes]) or "  <i>None</i>"
        exc_items = "\n".join([f"  • {html.escape(k)}" for k in all_excludes]) or "  <i>None</i>"

        text = (
            "📋 <b>Active Job Keywords</b>\n\n"
            f"✅ <b>Include Keywords ({len(all_includes)}):</b>\n{inc_items}\n\n"
            f"🚫 <b>Exclude Keywords ({len(all_excludes)}):</b>\n{exc_items}"
        )
        if update.effective_message:
            await update.effective_message.reply_html(text)

    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /pause command."""
        self.is_paused = True
        if self.pipeline and hasattr(self.pipeline, "config"):
            self.pipeline.config.bot.enabled = False
        if update.effective_message:
            await update.effective_message.reply_text("⏸️ Automated job notifications paused.")

    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /resume command."""
        self.is_paused = False
        if self.pipeline and hasattr(self.pipeline, "config"):
            self.pipeline.config.bot.enabled = True
        if update.effective_message:
            await update.effective_message.reply_text("▶️ Automated job notifications resumed!")

    async def scrape_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /scrape_now on-demand command."""
        if update.effective_message:
            await update.effective_message.reply_text("🚀 Starting on-demand scrape cycle across all job sources...")

        if self.pipeline:
            self.last_scrape_time = datetime.now(timezone.utc)
            metrics = self.pipeline.run_pipeline()
            summary = (
                f"✅ <b>Scrape Complete!</b>\n\n"
                f"• Fetched: <code>{metrics.get('raw_fetched', 0)}</code>\n"
                f"• New Unique: <code>{metrics.get('unique_saved', 0)}</code>\n"
                f"• Matched Criteria: <code>{metrics.get('matched', 0)}</code>\n"
                f"• Alerts Sent: <code>{metrics.get('notified', 0)}</code>"
            )
            if update.effective_message:
                await update.effective_message.reply_html(summary)
        else:
            if update.effective_message:
                await update.effective_message.reply_text("⚠️ Pipeline instance not linked to bot command handler.")

    def create_application(self) -> Application:
        """Constructs and returns the configured python-telegram-bot Application."""
        app = ApplicationBuilder().token(self.config.bot.telegram_token).build()

        app.add_handler(CommandHandler(["start", "help"], self.start_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("addkeyword", self.add_keyword_command))
        app.add_handler(CommandHandler("removekeyword", self.remove_keyword_command))
        app.add_handler(CommandHandler("listkeywords", self.list_keywords_command))
        app.add_handler(CommandHandler("scrape_now", self.scrape_now_command))
        app.add_handler(CommandHandler("pause", self.pause_command))
        app.add_handler(CommandHandler("resume", self.resume_command))

        return app
