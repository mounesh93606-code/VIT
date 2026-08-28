# Production Secure Dockerfile for Supply Chain Finance (SCF Nexus) Platform
FROM python:3.11-slim

WORKDIR /app

# Create non-root unprivileged app user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Install system dependencies required for build and clean up build compilers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install email-validator explicitly first (required by pydantic[email])
RUN pip install --no-cache-dir email-validator>=2.1.0

# Copy dependency requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase and grant permissions to appuser
COPY . .
RUN chown -R appuser:appgroup /app

# Switch to non-root user context
USER appuser

# Expose port
EXPOSE 8000

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run database initialization & migrations, then start FastAPI with production Gunicorn ASGI workers
CMD ["sh", "-c", "python database/init_db.py && gunicorn -w 2 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:${PORT:-8000}"]
