"""
Lightweight Web Status Server for Hugging Face Spaces (Port 7860).
Provides a status dashboard and keeps Hugging Face Space alive 24/7.
"""

from datetime import datetime, timezone
import http.server
import json
import socketserver
import threading
from typing import Optional
from config.settings import AppConfig
from src.storage.database import DatabaseManager
from src.storage.repository import JobRepository
from src.utils.logger import setup_logger

logger = setup_logger("web_status")


class StatusHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP handler returning a clean HTML status page and JSON health endpoint."""

    config: Optional[AppConfig] = None
    db_manager: Optional[DatabaseManager] = None
    repository: Optional[JobRepository] = None
    start_time: datetime = datetime.now(timezone.utc)

    def do_GET(self):
        if self.path == "/health" or self.path == "/api/status":
            self._handle_json()
        else:
            self._handle_html()

    def _handle_json(self):
        total_jobs = self.repository.count_total_jobs() if self.repository else 0
        uptime = str(datetime.now(timezone.utc) - self.start_time).split(".")[0]
        data = {
            "status": "healthy",
            "bot_running": True,
            "total_jobs_stored": total_jobs,
            "uptime": uptime,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _handle_html(self):
        total_jobs = self.repository.count_total_jobs() if self.repository else 0
        uptime = str(datetime.now(timezone.utc) - self.start_time).split(".")[0]
        recent_jobs = self.repository.get_recent_jobs(limit=8) if self.repository else []

        recent_rows = ""
        for j in recent_jobs:
            badge = '<span style="background:#10b981;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">Remote</span>' if j.remote_flag else '<span style="background:#6b7280;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">On-site</span>'
            recent_rows += f"""
            <tr style="border-bottom:1px solid #374151;">
                <td style="padding:10px;font-weight:600;color:#f3f4f6;"><a href="{j.url}" target="_blank" style="color:#60a5fa;text-decoration:none;">{j.title}</a></td>
                <td style="padding:10px;color:#d1d5db;">{j.company}</td>
                <td style="padding:10px;color:#9ca3af;">{j.location} {badge}</td>
                <td style="padding:10px;color:#9ca3af;">{j.source}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Alert Bot — 24/7 Status Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #111827; color: #f9fafb; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .card {{ background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        .badge {{ background: #10b981; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-size: 13px; font-weight: bold; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }}
        .stat-box {{ background: #111827; padding: 15px; border-radius: 8px; border: 1px solid #374151; }}
        .stat-val {{ font-size: 24px; font-weight: bold; color: #60a5fa; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #111827; padding: 10px; text-align: left; color: #9ca3af; font-size: 12px; text-transform: uppercase; border-bottom: 2px solid #374151; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h1 style="margin:0; font-size:22px;">🔔 Job Alert Bot 24/7</h1>
                <span class="badge">● Running Active</span>
            </div>
            <p style="color:#9ca3af; margin-top:8px; margin-bottom:0;">Continuous Multi-Source Job Scraper & Telegram Notification Engine on Hugging Face Spaces</p>
            
            <div class="grid">
                <div class="stat-box">
                    <div style="font-size:12px; color:#9ca3af;">TOTAL JOBS STORED</div>
                    <div class="stat-val">{total_jobs}</div>
                </div>
                <div class="stat-box">
                    <div style="font-size:12px; color:#9ca3af;">UPTIME</div>
                    <div class="stat-val">{uptime}</div>
                </div>
                <div class="stat-box">
                    <div style="font-size:12px; color:#9ca3af;">ACTIVE SOURCES</div>
                    <div class="stat-val" style="font-size:16px; margin-top:10px;">Ethiojobs, Telegram, RemoteOK, Jobicy</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3 style="margin-top:0;">📋 Recently Stored Job Postings</h3>
            <table>
                <thead>
                    <tr>
                        <th>Job Title</th>
                        <th>Company</th>
                        <th>Location</th>
                        <th>Source</th>
                    </tr>
                </thead>
                <tbody>
                    {recent_rows or '<tr><td colspan="4" style="padding:20px;text-align:center;color:#6b7280;">Initial scrape in progress...</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default stderr logging to keep logs clean
        pass


def run_status_server(config: AppConfig, port: int = 7860) -> threading.Thread:
    """Starts the status web server in a daemon thread on port 7860 (Hugging Face default)."""
    db_manager = DatabaseManager(config.database.db_path)
    repository = JobRepository(db_manager)

    StatusHTTPHandler.config = config
    StatusHTTPHandler.db_manager = db_manager
    StatusHTTPHandler.repository = repository

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = ReusableTCPServer(("0.0.0.0", port), StatusHTTPHandler)
    logger.info(f"Hugging Face status server listening on http://0.0.0.0:{port}")

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return server_thread
