# 🚀 100% Free 24/7 Deployment Guide on Hugging Face Spaces (Gradio)

This guide shows you how to deploy the **Job Alert Bot** on **Hugging Face Spaces** using the **Gradio SDK** (which is **100% Free with NO credit card and NO payment required**).

---

## 🌟 Why Hugging Face Gradio Space?

| Feature | Hugging Face Gradio Free Tier |
| :--- | :--- |
| **Cost** | **$0 / month forever (100% Free)** |
| **Credit Card Required?** | **NO** (Sign up with just an email) |
| **Hardware** | **2 vCPUs · 16 GB RAM · 50 GB Disk** |
| **Uptime** | **Runs 24/7 continuously** |
| **Live Web UI** | **Included** (Live Job Explorer, Keyword Manager, Trigger Scrape button) |

---

## 🛠️ Step-by-Step Deployment (Takes 2 Minutes)

### Step 1: Create a Free Account on Hugging Face
1. Go to: **[huggingface.co/join](https://huggingface.co/join)** and create your free account.

---

### Step 2: Create a New Space
1. Open this link: **[huggingface.co/new-space](https://huggingface.co/new-space)**
2. Fill in the form:
   * **Space name**: `job-alert-bot` (or any name you want)
   * **License**: `mit`
   * **Select the Space SDK**: Click **Gradio** *(Do NOT select Docker; Gradio is 100% free with no credit card!)*
   * **Space Hardware**: Select **Free (CPU basic · 2 vCPU · 16 GB)**
   * **Visibility**: **Public** or **Private**
3. Click **Create Space**.

---

### Step 3: Get Your Free Hugging Face Write Token
1. Go to: **[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)**
2. Click **Create new token**.
3. Select **Token type:** **`Write`** and name it `bot-deploy`.
4. Click **Generate a token** and **copy** it.

---

### Step 4: Push Your Code to Hugging Face

Open your computer's terminal (or Command Prompt) inside your `job_finder` repository folder and run:

```bash
# 1. Add your Hugging Face Space as a remote
git remote add space https://huggingface.co/spaces/<YOUR_HF_USERNAME>/job-alert-bot

# 2. Push to Hugging Face
git push -u space main
```

*When prompted:*
* **Username**: Your Hugging Face username.
* **Password**: The **Write Token** (`hf_...`) you copied in Step 3.

---

### Step 5: That's It! Your Bot is Live 24/7!

1. Open your Space URL:
   `https://huggingface.co/spaces/<YOUR_HF_USERNAME>/job-alert-bot`
2. Hugging Face will install dependencies and start `app.py`.
3. In under 1 minute, your Space will show **🟢 Running** with:
   * **Live Job Explorer**: Browse and search all scraped jobs.
   * **Keyword Filter Manager**: Add or remove search keywords from the web.
   * **On-Demand Scrape**: Click to trigger a scrape anytime.
   * **24/7 Background Scheduler**: Automatically scrapes Ethiojobs, Telegram Channels, RemoteOK, and Jobicy every 30 minutes.
   * **Telegram Bot Listener**: Continuously listens for commands in your Telegram group (`Job filter`).

---

## 📱 Interactive Telegram Commands

You can control the bot directly from your Telegram group (`Job filter`):

| Command | Action |
| :--- | :--- |
| **`/status`** | View uptime, total stored postings, and scraper state |
| **`/scrape_now`** | Triggers an immediate scrape across all sources |
| **`/addkeyword <word>`** | Adds a search keyword on the fly (e.g. `/addkeyword DevOps`) |
| **`/removekeyword <word>`** | Removes an existing keyword |
| **`/listkeywords`** | Displays all active include & exclude keywords |
| **`/pause` & `/resume`** | Pause or resume automated alerts |
| **`/help`** | Displays command menu |
