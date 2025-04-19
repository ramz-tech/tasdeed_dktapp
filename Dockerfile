# Use Python 3.12 slim as base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by Playwright’s Chromium
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    gnupg \
    libssl-dev \
    libsasl2-dev \
    zlib1g-dev \
    software-properties-common \
    librdkafka-dev \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    libxshmfence1 \
    libdbus-glib-1-2 && \
    curl -fsSL https://packages.confluent.io/deb/7.7/archive.key | gpg --dearmor -o /usr/share/keyrings/confluent-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/confluent-archive-keyring.gpg] https://packages.confluent.io/deb/7.7 stable main" | tee /etc/apt/sources.list.d/confluent.list && \
    apt-get update && apt-get install -y --no-install-recommends librdkafka-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Copy requirements early (cache!)
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright + Chromium
RUN playwright install
RUN playwright install-deps

# Copy the rest of your app
COPY . .

# Create any runtime directories
RUN mkdir -p output data_extractor

# Set env vars
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/browser

# Switch to a non‑root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Default command
CMD ["python", "main.py"]
