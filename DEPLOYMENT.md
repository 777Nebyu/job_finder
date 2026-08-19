# 🚀 Complete Free 24/7 Deployment Guide on Hugging Face Spaces

This guide walks you through deploying your **Job Alert Bot** to **Hugging Face Spaces** so it runs **24 hours a day, 7 days a week for $0 (100% Free forever)**.

---

## 🌟 Why Hugging Face Spaces?

| Feature | Hugging Face Spaces | Other Free Hosts |
| :--- | :--- | :--- |
| **Cost** | **$0 / month forever** | Often limited to trial periods |
| **Hardware** | **2 vCPUs · 16 GB RAM · 50 GB Storage** | Usually 256MB–512MB RAM |
| **Sleep / Inactivity** | **Never sleeps (Runs 24/7)** | Free tiers sleep after 15 mins |
| **Credit Card Required?** | **NO** | Often requires card verification |
| **Live Status Page** | **Yes (Built-in Port 7860 Dashboard)** | None |

---

## 📋 Prerequisites

1. A free account on [Hugging Face](https://huggingface.co/join) (takes 1 minute).
2. Your GitHub repository: `https://github.com/777Nebyu/job_finder`.

---

## 🛠️ Step-by-Step Deployment (Takes 3 Minutes)

### Step 1: Create a New Space on Hugging Face

1. Go to: **[huggingface.co/new-space](https://huggingface.co/new-space)**
2. Fill out the form:
   * **Space name**: `job-alert-bot` (or any name you like)
   * **License**: `mit`
   * **Select the Space SDK**: Click **Docker** $\rightarrow$ choose **Blank**.
   * **Space Hardware**: Select **Free (CPU basic · 2 vCPU · 16 GB)**.
   * **Visibility**: **Private** (recommended) or **Public**.
3. Click **Create Space**.

---

### Step 2: Push Your Code to the Hugging Face Space

Hugging Face Spaces are standard Git repositories. You can push your code directly using your terminal or Git:

1. On your newly created Space page, click the **Settings** or **Files** tab, or copy your Space's clone URL:
   `https://huggingface.co/spaces/<YOUR_HF_USERNAME>/job-alert-bot`

2. Open your terminal in your project directory and run:
   ```bash
   # 1. Add Hugging Face as a remote
   git remote add space https://huggingface.co/spaces/<YOUR_HF_USERNAME>/job-alert-bot

   # 2. Push to Hugging Face Space
   git push -u space main
   ```
   *(When prompted for password, enter your Hugging Face **User Access Token** from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) with `write` permission).*

---

### Step 3: Verify Your Bot is Running 24/7

1. Go to your Hugging Face Space URL:
   `https://huggingface.co/spaces/<YOUR_HF_USERNAME>/job-alert-bot`
2. You will see the **Build Log** building the Docker container (takes ~1 minute).
3. Once built, the status badge will turn **🟢 Running**.
4. You will see the live **Job Alert Bot 24/7 Status Dashboard** showing:
   * Total stored jobs
   * Active scrapers (Ethiojobs, Telegram Channels, RemoteOK, Jobicy)
   * Uptime clock
5. Open your Telegram group (`Job filter`) and test sending:
   * **`/status`**
   * **`/scrape_now`**
   * **`/listkeywords`**

The bot will reply immediately!

---

## 🔄 Optional: Automatic Auto-Sync from GitHub to Hugging Face

To have Hugging Face update automatically whenever you push to GitHub:

1. In your GitHub repository (`777Nebyu/job_finder`), go to **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**.
2. Click **New repository secret**:
   * Name: `HF_TOKEN`
   * Value: Your Hugging Face write token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
3. We have included a ready GitHub Actions workflow file in `.github/workflows/sync_to_hf.yml` that syncs every GitHub commit to Hugging Face automatically!

---

## 🛠️ Useful Telegram Bot Commands

| Command | Action |
| :--- | :--- |
| **`/status`** | Shows system health, stored jobs count, and uptime |
| **`/scrape_now`** | Triggers an immediate scrape and alert cycle on demand |
| **`/addkeyword <word>`** | Adds a new search keyword on the fly (e.g. `/addkeyword Frontend`) |
| **`/removekeyword <word>`** | Removes a search keyword |
| **`/listkeywords`** | Lists all active include & exclude keywords |
| **`/pause`** | Temporarily pauses notifications |
| **`/resume`** | Resumes notifications |
| **`/help`** | Displays the command menu |
