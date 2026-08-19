"""
Interactive Telegram Bot Command Handlers.
Implements interactive commands for runtime control:
/start, /help, /status, /addkeyword, /removekeyword, /listkeywords,
/addchannel, /removechannel, /listchannels, /scrape_now, /pause, /resume
Supports single and bulk operations.
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
            "📊 <b>/status</b> — System health & total jobs stored\n"
            "🔍 <b>/scrape_now</b> — Trigger an immediate on-demand scrape\n\n"
            "<b>📡 Telegram Channels (Bulk Supported):</b>\n"
            "➕ <b>/addchannel @ch1 @ch2 @ch3</b> — Add multiple channels at once\n"
            "➖ <b>/removechannel @ch1 @ch2</b> — Remove channels\n"
            "📋 <b>/listchannels</b> — List all monitored channels\n\n"
            "<b>🎯 Keywords Management (Bulk Supported):</b>\n"
            "➕ <b>/addkeyword word1, word2, word3</b> — Add multiple keywords\n"
            "➖ <b>/removekeyword word1, word2</b> — Remove keywords\n"
            "📋 <b>/listkeywords</b> — View all active keywords\n\n"
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
        """Handles /addkeyword word1, word2, word3 command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify one or more keywords (comma-separated).\nExample: /addkeyword IT Officer, Receptionist, Accountant"
                )
            return

        raw_kw = " ".join(context.args)
        added, skipped = self.keyword_store.add_multiple_keywords(raw_kw, kind="include")
        if self.pipeline and hasattr(self.pipeline, "filter_engine"):
            self.pipeline.filter_engine.reload()

        msg = ""
        if added:
            msg += f"✅ Added {len(added)} keyword(s):\n" + "\n".join([f"• {k}" for k in added])
        if skipped:
            if msg:
                msg += "\n\n"
            msg += f"⚠️ Already existed: {', '.join(skipped)}"

        if update.effective_message:
            await update.effective_message.reply_text(msg or "⚠️ No valid keywords provided.")

    async def remove_keyword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /removekeyword word1, word2 command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify one or more keywords to remove.\nExample: /removekeyword IT Officer, Receptionist"
                )
            return

        raw_kw = " ".join(context.args)
        removed, not_found = self.keyword_store.remove_multiple_keywords(raw_kw)
        if self.pipeline and hasattr(self.pipeline, "filter_engine"):
            self.pipeline.filter_engine.reload()

        msg = ""
        if removed:
            msg += f"✅ Removed {len(removed)} keyword(s):\n" + "\n".join([f"• {k}" for k in removed])
        if not_found:
            if msg:
                msg += "\n\n"
            msg += f"⚠️ Not found in dynamic list: {', '.join(not_found)}"

        if update.effective_message:
            await update.effective_message.reply_text(msg or "⚠️ No valid keywords provided.")

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
        """Handles /addchannel @ch1 @ch2 @ch3 bulk command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify one or more Telegram channels (separated by space or comma).\nExample: /addchannel @harmeejobs @effoi_jobs @elelanajobs"
                )
            return

        raw_input = " ".join(context.args)
        added, skipped = self.channel_store.add_multiple_channels(raw_input)

        msg = ""
        if added:
            msg += f"✅ Successfully added {len(added)} channel(s) to monitor:\n" + "\n".join([f"• {c}" for c in added])
        if skipped:
            if msg:
                msg += "\n\n"
            msg += f"⚠️ Already being monitored: {', '.join(skipped)}"

        if update.effective_message:
            await update.effective_message.reply_text(msg or "⚠️ No valid channel handles provided.")

    async def remove_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles /removechannel @ch1 @ch2 command."""
        if not context.args:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Please specify one or more Telegram channels to remove.\nExample: /removechannel @harmeejobs @effoi_jobs"
                )
            return

        raw_input = " ".join(context.args)
        removed, not_found = self.channel_store.remove_multiple_channels(raw_input)

        msg = ""
        if removed:
            msg += f"✅ Removed {len(removed)} channel(s):\n" + "\n".join([f"• {c}" for c in removed])
        if not_found:
            if msg:
                msg += "\n\n"
            msg += f"⚠️ Not found in custom channels: {', '.join(not_found)}"

        if update.effective_message:
            await update.effective_message.reply_text(msg or "⚠️ No valid channel handles provided.")

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
            f"<i>Add multiple channels anytime: <code>/addchannel @ch1 @ch2 @ch3</code></i>"
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
                f"• Matched Criteria (Valid Deadline): <code>{metrics.get('matched', 0)}</code>\n"
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
