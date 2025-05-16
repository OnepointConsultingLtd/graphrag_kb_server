# Use Python 3.12.10 as the base image
FROM python:3.12.10

# Set working directory for application code
WORKDIR /opt/graphrag_kb_server

# Install system dependencies and Node.js
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    python3-dev \
    libssl-dev \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Create necessary directories
# Read-only application directories

# Writable data directories (will be mounted as volumes)
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
COPY run.sh .
COPY README.md .
COPY config/security.yaml config/security.yaml

# Convert line endings and make run.sh executable
RUN dos2unix run.sh && chmod +x run.sh

# Copy and rename configuration files
COPY .env_docker .env

# Install Python dependencies using uv
RUN uv pip install --system .

# Install front-end dependencies and build
WORKDIR /opt/graphrag_kb_server/front_end
RUN rm -rf package-lock.json
RUN npm install
RUN npm ci --production=false
RUN npm run build
# Clean up development dependencies
RUN npm ci --production=true
RUN rm -rf node_modules/.cache

WORKDIR /var/graphrag
COPY config/administration_local.yaml config/administration.yaml

# Return to main working directory
WORKDIR /opt/graphrag_kb_server

# Expose the port specified in .env
EXPOSE 9999

# Set environment variables
ENV PYTHONPATH=/opt/graphrag_kb_server
ENV UPLOAD_DIR=/var/graphrag/upload
ENV GRAPHRAG_ROOT_DIR=/var/graphrag/tennants

# Command to run the application using run.sh
CMD ["./run.sh"]