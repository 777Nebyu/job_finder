# Job Alert Bot (Tier 1 + Interactive Commands & Scrapers)

A modular, multi-source job scraping and alert pipeline designed to monitor job boards (Ethiojobs, Telegram Channels, RemoteOK, Jobicy, Afriwork, Josad), deduplicate listings, filter by customizable inclusion/exclusion rules, and send formatted alert cards directly to Telegram channels, groups, or private chats.

---

## 🌟 Key Features

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

4. **100% Free 24/7 Cloud Deployment:**
   - Dockerized with non-root security and persistent SQLite storage.
   - 1-click free deployment on **Koyeb**, **Render**, or **Hugging Face Spaces**.

---

## 📌 Architecture

```
[ Scrapers (Module 1) ] 
       │ (Ethiojobs, Telegram Channels, RemoteOK, Jobicy)
       ▼
[ Normalization (Module 2) ] (HTML Stripping, Universal Date Parser)
       │
       ▼
[ Deduplication & Storage (Module 3) ] (SHA-256 + RapidFuzz + SQLite)
       │
       ▼
[ Filter Engine (Module 4) ] (Dynamic & Static Keyword Rules)
       │
       ▼
[ Telegram Bot (Module 5) ] (HTML Alert Cards + Interactive Commands)
```

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
# Run a single scrape & notify cycle:
python main.py run

# Start 24/7 background scheduler & interactive Telegram bot:
python main.py daemon

# Run pre-flight diagnostics:
python main.py check

# Test a specific scraper (e.g., telegram_channels, ethiojobs):
python main.py test-source telegram_channels

# View database statistics:
python main.py stats

# Run full automated test suite:
pytest
```

---

## ☁️ 24/7 Free Cloud Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for step-by-step instructions to deploy on:
- **Koyeb** (100% Free 24/7 Eco Instance)
- **Render.com** (Free Web/Worker Service)
- **Hugging Face Spaces** (Free Docker Container 24/7)
- **Docker Compose & Linux Systemd**
