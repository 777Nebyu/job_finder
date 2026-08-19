# 🚀 100% Free 24/7 Deployment Guide on Render.com

This guide shows you how to deploy the **Job Alert Bot** on **Render.com** for **$0 (100% Free forever, no credit card required)**.

---

## 🌟 Why Render.com?

* **100% Free Tier**: $0/month.
* **Direct GitHub Sync**: Automatically updates whenever you push to GitHub.
* **Zero Configuration**: Ready with `render.yaml` Blueprint.
* **Live Dashboard & Telegram Bot**: Both your Gradio dashboard and your Telegram Bot run 24/7.

---

## 🛠️ Step-by-Step Deployment (Takes 2 Minutes)

### Step 1: Sign in to Render with GitHub
1. Go to: **[https://dashboard.render.com/register](https://dashboard.render.com/register)**
2. Click **Sign up with GitHub** (Free, no credit card required).

---

### Step 2: Create a New Web Service
1. In your Render Dashboard, click the **New +** button (top right) $\rightarrow$ select **Web Service**.
2. Select **Build and deploy from a Git repository** $\rightarrow$ Click **Next**.
3. Choose your repository: **`777Nebyu/job_finder`** (Click **Connect**).

---

### Step 3: Configure Settings (Takes 30 Seconds)
Render will automatically detect the settings from `render.yaml`, or you can confirm:

* **Name**: `job-alert-bot`
* **Region**: Any (e.g., `Oregon (US West)` or `Frankfurt (EU)`)
* **Branch**: `main`
* **Runtime**: `Python 3`
* **Build Command**: `pip install -r requirements.txt`
* **Start Command**: `python app.py`
* **Instance Type**: Select **Free** ($0 / month)

---

### Step 4: Click "Deploy Web Service"
1. Scroll to the bottom and click **Create Web Service** (or **Deploy Web Service**).
2. Render will clone your GitHub repository, install the dependencies, and start the bot.
3. In ~1 minute, the status will show **🟢 Live**!

---

### Step 5: Test Your Bot in Telegram!
Once live:
1. Open your Telegram group (**`Job filter`**).
2. Send:
   * **`/status`**
   * **`/scrape_now`**
   * **`/listkeywords`**
3. The bot will reply immediately and run **24/7 continuously in the cloud for $0**!
