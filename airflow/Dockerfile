FROM apache/airflow:2.7.3-python3.11

# Switch to root to install system dependencies
USER root

# Install system dependencies for web scraping
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome (optional - for local debugging, not needed with Selenium Grid)
# Uncomment if you want Chrome in the Airflow containers themselves
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#     && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
#     && apt-get update \
#     && apt-get install -y google-chrome-stable \
#     && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /opt/airflow/scrapers \
    /opt/airflow/data \
    /opt/airflow/scraped_jobs \
    /opt/airflow/secrets \
    && chown -R airflow:root /opt/airflow/scrapers \
    && chown -R airflow:root /opt/airflow/data \
    && chown -R airflow:root /opt/airflow/scraped_jobs \
    && chown -R airflow:root /opt/airflow/secrets

# Switch back to airflow user
USER airflow

# Copy requirements file
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r /requirements.txt

# Add ~/.local/bin to PATH so pip user installs (like dbt) are accessible
ENV PATH="/home/airflow/.local/bin:${PATH}"

# Set working directory
WORKDIR /opt/airflow
