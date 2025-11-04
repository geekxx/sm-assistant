# Use Python 3.11 slim base image
FROM python:3.11-slim

# Force rebuild timestamp: Nov 4, 2025 20:56
# Set working directory
WORKDIR /app

# Install system dependencies (add Node.js for frontend build)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend dependencies and build
COPY src/frontend/package.json ./src/frontend/
RUN cd src/frontend && npm install

# Copy all source code
COPY src/ ./src/
COPY .env.example .env

# Verify correct version is being built
RUN grep -q "version.*2.2.0" src/backend/main_simple_api.py || (echo "ERROR: Wrong version being built!" && exit 1)

# Build frontend
RUN cd src/frontend && npm run build

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose ports (Railway uses PORT env var)
EXPOSE 8005 3001
ENV PORT=8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8005/health || exit 1

# Run application (Railway optimized)
CMD ["python", "src/backend/main_simple_api.py"]