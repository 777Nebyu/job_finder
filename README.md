---
title: Job Alert Bot 24/7
emoji: 🔔
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.24.0
app_file: app.py
pinned: false
---

# 🔔 Job Alert Bot (Tier 1 + Telegram Commands & Gradio Dashboard)

A modular, multi-source job scraping and alert engine designed to monitor job boards (Ethiojobs, Telegram Channels, RemoteOK, Jobicy, Afriwork, Josad), deduplicate listings with SHA-256 and fuzzy matching, filter by customizable inclusion/exclusion rules, and send formatted alert cards directly to Telegram.

---

## 🌟 Features

1. **Multi-Source Scraping Engine:**
   - **Ethiojobs.net:** Server-rendered Next.js pagination parser.
   - **Telegram Public Channels:** Web scraper for `@freelance_ethio`, `@Ethiojobsofficial`, `@hahujobs`, `@shegerjobs` without requiring Telegram API keys.
   - **RemoteOK & Jobicy:** Public JSON APIs for worldwide & Africa-eligible remote positions.
   - **Afriwork & Josad:** Scrapers with isolated error containment.

2. **Dual-Layer Deduplication:**
   - **Intra-Source:** Deterministic SHA-256 hash lookup ($O(1)$ fast check).
   - **Cross-Source:** Fuzzy string matching via `RapidFuzz` on normalized title + company to prevent duplicate alerts from multiple boards.

3. **Interactive Telegram Commands (24/7 Control):**
   - `/status` — View total jobs stored, last scrape time, and active sources.
   - `/scrape_now` — Trigger an immediate on-demand scrape and alert cycle.
   - `/addkeyword <word>` — Add a new search keyword dynamically on the fly.
   - `/removekeyword <word>` — Remove an existing dynamic keyword.
   - `/listkeywords` — View all active include and exclude keywords.
   - `/pause` & `/resume` — Temporarily pause or resume alerts.
   - `/help` — View command manual.

4. **100% Free 24/7 Cloud Deployment on Hugging Face Spaces (Gradio SDK):**
   - Built-in Gradio web dashboard (`app.py`).
   - Runs 24/7 on Free CPU basic (2 vCPU · 16 GB RAM) with **$0 cost & NO credit card required**.

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Settings
Edit `config/config.yaml` to set your:
- Telegram Bot Token & Chat ID
- Include & Exclude Keywords
- Enabled Job Sources

### 3. Run Commands
```bash
# Run Gradio Web Dashboard + 24/7 Background Bot:
python app.py

# Or run CLI daemon:
python main.py daemon

# Run a single scrape & notify cycle:
python main.py run

# Run pre-flight diagnostics:
python main.py check

# Test a specific scraper (e.g., telegram_channels, ethiojobs):
python main.py test-source telegram_channels

# Run full automated test suite:
pytest
```

---

## ☁️ Hugging Face Spaces Free Deployment Guide

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the complete step-by-step guide.
