FROM python:3.12-slim

# Install system dependencies required by Playwright and email
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    msmtp \
    msmtp-mta \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY pyproject.toml setup.cfg README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Install Playwright and its system dependencies
# This installs all required system libraries
RUN playwright install --with-deps firefox

# Create logs directory
RUN mkdir -p logs

# Copy msmtp configuration script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Run the application via entrypoint (which sets up cron)
ENTRYPOINT ["/docker-entrypoint.sh"]
