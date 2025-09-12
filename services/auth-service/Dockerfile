# Auth Service Dockerfile
FROM python:3.11-slim

# Metadata
LABEL maintainer="RepitBot Team"
LABEL service="auth-service"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV AUTH_SERVICE_HOST=0.0.0.0
ENV AUTH_SERVICE_PORT=8002

# Security environment variables
ENV JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
ENV JWT_ALGORITHM=HS256
ENV ACCESS_TOKEN_EXPIRE_MINUTES=15
ENV REFRESH_TOKEN_EXPIRE_DAYS=30

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8002/health')" || exit 1

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "-m", "app.main"]