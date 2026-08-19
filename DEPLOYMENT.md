# 🚀 Free 24/7 Deployment Guide for Job Alert Bot

This guide covers how to deploy the **Job Alert Bot** to run **24/7 continuously in the cloud for $0 (100% Free)**.

---

## 🏆 Top 3 Recommended 100% Free Hosting Platforms

| Platform | Free Allowance | Card Required? | Best For |
| :--- | :--- | :--- | :--- |
| **1. Koyeb** *(Recommended)* | 1 Free Nano/Eco Instance 24/7 (512MB RAM) | No | Continuous background worker from GitHub |
| **2. Render.com** | Free Web / Background Service | No | Easiest 1-click GitHub setup |
| **3. Hugging Face Spaces** | 2 vCPU, 16GB RAM Free Docker Space 24/7 | No | High performance, runs Docker 24/7 |

---

## 🛠️ Option A: Deploy on Koyeb (100% Free — Recommended)

1. **Sign Up**: Create a free account at [koyeb.com](https://www.koyeb.com).
2. **Create App**: Click **Create App** $\rightarrow$ select **GitHub**.
3. **Select Repository**: Select `777Nebyu/job_finder`.
4. **Configuration**:
   * **Builder**: Dockerfile (automatically detected).
   * **Instance Type**: **Free (Nano / Eco)**.
   * **Run Command**: `python main.py daemon`
5. **Deploy**: Click **Deploy**. Koyeb will build the Docker container and start your 24/7 bot immediately.

---

## 🛠️ Option B: Deploy on Render.com (100% Free)

1. Go to [render.com](https://render.com) and log in with GitHub.
2. Click **New +** $\rightarrow$ **Web Service** (or **Background Worker**).
3. Connect your repository: `777Nebyu/job_finder`.
4. Configure:
   * **Environment**: `Python 3` (or `Docker`)
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python main.py daemon`
   * **Plan**: **Free**
5. Click **Create Web Service**.

---

## 🛠️ Option C: Deploy on Hugging Face Spaces (100% Free Docker Container)

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and create a free Space.
2. Select **SDK: Docker** $\rightarrow$ **Blank**.
3. Clone the space repo or connect your GitHub repository `777Nebyu/job_finder`.
4. The space will build the `Dockerfile` and keep your bot online 24/7 with 16GB RAM for free.

---

## 🛠️ Option D: Deploy on a Linux VPS / Server via Docker or Systemd

If you ever get a free VPS (e.g. Oracle Cloud Always Free VM or AWS Free Tier):

### Using Docker Compose:
```bash
git clone https://github.com/777Nebyu/job_finder.git
cd job_finder
docker compose up -d
```

### Using Linux Systemd:
```bash
git clone https://github.com/777Nebyu/job_finder.git
cd job_finder
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup systemd service
sudo cp systemd/job_alert_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now job_alert_bot
sudo systemctl status job_alert_bot
```
