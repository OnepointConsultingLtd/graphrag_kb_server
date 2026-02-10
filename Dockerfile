# Use Python 3.12.10 as the base image
FROM python:3.12.10

# 1. Prepare frpc
RUN mkdir -p /frpc/
COPY docker/run_frpc.sh /frpc/
ADD https://github.com/fatedier/frp/releases/download/v0.65.0/frp_0.65.0_linux_amd64.tar.gz /tmp/frp.tar.gz
RUN tar -xzf /tmp/frp.tar.gz -C /tmp/ && \
    mv /tmp/frp_0.65.0_linux_amd64/frpc /frpc/frpc && \
    chmod +x /frpc/frpc /frpc/run_frpc.sh && \
    rm -rf /tmp/frp.tar.gz /tmp/frp_0.65.0_linux_amd64

# Set working directory for application code
WORKDIR /opt/graphrag_kb_server

# Install system dependencies: build tools, WeasyPrint (Cairo/Pango), Chromium, Node.js
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    python3-dev \
    libssl-dev \
    curl \
    dos2unix \
    wget \
    unzip \
    ca-certificates \
    gnupg \
    # WeasyPrint (HTML-to-PDF) system dependencies
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    # Chromium and dependencies for Selenium (LinkedIn scraping)
    chromium \
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
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verify Node.js 22 is installed and enable Yarn
RUN node --version | grep -E '^v22\.' && \
    corepack enable && \
    corepack prepare yarn@stable --activate && \
    yarn --version

# Install ChromeDriver matching installed Chromium (Debian Chromium version)
RUN CHROMIUM_VERSION=$(chromium --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1) \
    && CHROME_MAJOR="${CHROMIUM_VERSION%%.*}" \
    && CHROMEDRIVER_URL=$(curl -sS "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | grep -o "\"https://storage.googleapis.com/chrome-for-testing-public/[^\"]*${CHROME_MAJOR}[^\"]*linux64[^\"]*chromedriver[^\"]*\.zip\"" | head -1 | tr -d '"') \
    && if [ -z "$CHROMEDRIVER_URL" ]; then \
         CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROMIUM_VERSION}/linux64/chromedriver-linux64.zip"; \
       fi \
    && wget -q -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL" || true \
    && if [ -f /tmp/chromedriver.zip ]; then \
         unzip -o /tmp/chromedriver.zip -d /tmp && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && chmod +x /usr/local/bin/chromedriver && rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64; \
       fi

# Install uv
RUN pip install uv

# Create necessary directories
# Read-only application directories

# Writable data directories (/var/graphrag will be mounted as volume)
RUN mkdir -p /var/graphrag/upload \
    /var/graphrag/tennants \
    /var/graphrag/config \
    /var/graphrag/jwt_gen

# Copy project files
COPY pyproject.toml .
COPY uv.lock .
COPY graphrag_kb_server/ ./graphrag_kb_server/
COPY prompts/ ./prompts/
COPY front_end/ ./front_end/
COPY front_end_chat/ ./front_end_chat/
COPY run.sh .
COPY README.md .
COPY config/security.yaml config/security.yaml
COPY docker/run.sh docker/run.sh

# Convert line endings and make scripts executable
RUN dos2unix run.sh && chmod +x run.sh && \
    dos2unix docker/run.sh && chmod +x docker/run.sh && \
    dos2unix /frpc/run_frpc.sh && chmod +x /frpc/run_frpc.sh

# Copy and rename configuration files
COPY .env_docker .env

# Install Python dependencies using uv
RUN uv pip install --system .

RUN uv venv
RUN uv pip install --no-binary lancedb --force-reinstall lancedb

# Build front_end (GraphRAG) with yarn
RUN cd /opt/graphrag_kb_server/front_end \
    && node --version \
    && cp server_prod.js server.ts \
    && yarn \
    && yarn build \
    && cd /opt/graphrag_kb_server

# Build front_end_chat with yarn
RUN cd /opt/graphrag_kb_server/front_end_chat \
    && node --version \
    && cp src/lib/server_prod.ts src/lib/server.ts \
    && yarn \
    && yarn build \
    && VERSION=1.0.1 \
    && sed -i "s/index-fixed\.css?v=[0-9]\+/index-fixed.css/g" ./dist/index.html \
    && sed -i "s/index-fixed.css/index-fixed.css?v=$VERSION/g" ./dist/index.html \
    && sed -i "s/index-fixed\.js?v=[0-9]\+/index-fixed.js/g" ./dist/index.html \
    && sed -i "s/index-fixed.js/index-fixed.js?v=$VERSION/g" ./dist/index.html \
    && cd /opt/graphrag_kb_server

WORKDIR /var/graphrag
COPY config/administration_local.yaml config/administration.yaml

# Return to main working directory
WORKDIR /opt/graphrag_kb_server

# Expose the port specified in .env
EXPOSE 9999

# Remember to set environment variables on startup

# Command to run the application using docker/run.sh
CMD ["./docker/run.sh"]