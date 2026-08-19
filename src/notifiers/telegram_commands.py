"""
Interactive Telegram Bot Command Handlers.
Implements interactive commands for runtime control:
/start, /help, /status, /addkeyword, /removekeyword, /listkeywords,
/addchannel, /removechannel, /listchannels, /scrape_now, /pause, /resume
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
from src.scrapers.dynamic_channels import DynamicChannelStore
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
        channel_store: Optional[DynamicChannelStore] = None,
    ):
        self.config = config
        self.pipeline = pipeline
        self.db_manager = db_manager or DatabaseManager(config.database.db_path)
        self.repository = JobRepository(self.db_manager)
        self.keyword_store = keyword_store or DynamicKeywordStore(self.db_manager)
        self.channel_store = channel_store or DynamicChannelStore(self.db_manager)
        self.is_paused = not config.bot.enabled
        self.last_scrape_time: Optional[datetime] = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /start and /help commands."""
        help_text = (
            "👋 <b>Job Alert Bot — Command Menu</b>\n\n"
            "📊 <b>/status</b> — System health, total jobs stored & status\n"
            "🔍 <b>/scrape_now</b> — Trigger an immediate on-demand scrape\n\n"
            "<b>🎯 Keywords Management:</b>\n"
            "➕ <b>/addkeyword &lt;keyword&gt;</b> — Add search keyword (e.g. <code>/addkeyword Receptionist</code>)\n"
            "➖ <b>/removekeyword &lt;keyword&gt;</b> — Remove search keyword\n"
            "📋 <b>/listkeywords</b> — View all active keywords\n\n"
            "<b>📡 Telegram Channels Management:</b>\n"
            "➕ <b>/addchannel &lt;@channel&gt;</b> — Add a Telegram channel to scrape (e.g. <code>/addchannel @harmeejobs</code>)\n"
            "➖ <b>/removechannel &lt;@channel&gt;</b> — Remove a Telegram channel\n"
            "📋 <b>/listchannels</b> — List all monitored Telegram channels\n\n"
            "<b>⚙️ Controls:</b>\n"
            "⏸️ <b>/pause</b> — Pause automatic alerts\n"
            "▶️ <b>/resume</b> — Resume automatic alerts\n"
            "ℹ️ <b>/help</b> — Show this help menu"
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

        channels_count = 6 + len(self.channel_store.get_all_dynamic_channels())

        status_text = (
            "📊 <b>Job Alert Bot — System Status</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>State:</b> {status_state}\n"
            f"📦 <b>Total Stored Postings:</b> <code>{total_jobs}</code>\n"
            f"🎯 <b>Active Target Keywords:</b> <code>{total_keywords}</code>\n"
            f"📡 <b>Monitored Channels:</b> <code>{channels_count}</code>\n"
            f"⏱️ <b>Scrape Interval:</b> Every <code>{self.config.scheduler.interval_minutes}m</code>\n"
            f"🕒 <b>Last Pipeline Cycle:</b> <code>{last_run_str}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        if update.effective_message:
            await update.effective_message.reply_html(status_text)

    async def add_keyword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /addkeyword <word> command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify a keyword to add.\nExample: /addkeyword IT Officer"
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
                    "⚠️ Please specify a keyword to remove.\nExample: /removekeyword IT Officer"
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

    async def add_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /addchannel <@channel> command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify a Telegram channel username to add.\nExample: /addchannel @harmeejobs"
                )
            return

        ch = context.args[0].strip()
        success, msg = self.channel_store.add_channel(ch)
        if update.effective_message:
            await update.effective_message.reply_text(msg)

    async def remove_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /removechannel <@channel> command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify a Telegram channel username to remove.\nExample: /removechannel @harmeejobs"
                )
            return

        ch = context.args[0].strip()
        success, msg = self.channel_store.remove_channel(ch)
        if update.effective_message:
            await update.effective_message.reply_text(msg)

    async def list_channels_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /listchannels command."""
        defaults = [
            "freelance_ethio",
            "Ethiojobsofficial",
            "hahujobs",
            "shegerjobs",
            "harmeejobs",
            "effoi_jobs",
        ]
        dyn = self.channel_store.get_all_dynamic_channels()
        all_ch = list(dict.fromkeys(defaults + dyn))

        ch_items = "\n".join([f"  • @{html.escape(c)}" for c in all_ch])

        text = (
            f"📡 <b>Monitored Telegram Channels ({len(all_ch)})</b>\n\n"
            f"{ch_items}\n\n"
            f"<i>You can add new channels anytime with <code>/addchannel @channel_name</code></i>"
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
            await update.effective_message.reply_text("🚀 Starting on-demand scrape cycle across all job channels & sources...")

        if self.pipeline:
            self.last_scrape_time = datetime.now(timezone.utc)
            metrics = self.pipeline.run_pipeline()
            summary = (
                f"✅ <b>Scrape Complete!</b>\n\n"
                f"• Raw Fetched: <code>{metrics.get('raw_fetched', 0)}</code>\n"
                f"• New Unique: <code>{metrics.get('unique_saved', 0)}</code>\n"
                f"• Matched Criteria (Active & Valid Deadline): <code>{metrics.get('matched', 0)}</code>\n"
                f"• Telegram Alerts Sent: <code>{metrics.get('notified', 0)}</code>"
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
        app.add_handler(CommandHandler("addchannel", self.add_channel_command))
        app.add_handler(CommandHandler("removechannel", self.remove_channel_command))
        app.add_handler(CommandHandler("listchannels", self.list_channels_command))
        app.add_handler(CommandHandler("scrape_now", self.scrape_now_command))
        app.add_handler(CommandHandler("pause", self.pause_command))
        app.add_handler(CommandHandler("resume", self.resume_command))

        return app
