###DOCKERFILE
# Use slim Python image
FROM python:3.11-slim

# Non-interactive installs
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies + Chrome + unzip + fonts + libraries
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (stable)
RUN wget -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update && apt-get install -y /tmp/google-chrome.deb \
    && rm /tmp/google-chrome.deb

# Install ChromeDriver (Chrome for Testing stable)
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/143.0.7499.40/linux64/chromedriver-linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/bin/ \
    && chmod +x /usr/bin/chromedriver-linux64 \
    && rm /tmp/chromedriver.zip

# Set working directory
WORKDIR /app

# Use non-root user for safer permissions
RUN groupadd -g 3002 appuser && useradd -m -u 3002 -g 3002 appuser
USER appuser

# Default command
CMD ["python"]
