# Analytics Service Dockerfile
FROM python:3.11-slim

LABEL maintainer="RepitBot Team"
LABEL service="analytics-service"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    build-essential \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN adduser --disabled-password --gecos '' analytics

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/reports /app/templates /app/logs

# Set permissions
RUN chown -R analytics:analytics /app
USER analytics

# Expose port
EXPOSE 8007

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

# Start command
CMD ["python", "-m", "app.main"]