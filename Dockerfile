# ==============================================================================
# Job Alert Bot - Hugging Face Spaces & Production Dockerfile
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and config
COPY config/ ./config/
COPY src/ ./src/
COPY main.py .
COPY pytest.ini .

# Create volume directories for SQLite database and logs
RUN mkdir -p /app/data /app/logs

# Non-root user for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Hugging Face default port
EXPOSE 7860

# Persistent data volumes
VOLUME ["/app/data", "/app/logs"]

# Start 24/7 background daemon (Scrapers + Telegram Command Bot + Status Server)
CMD ["python", "main.py", "daemon"]
