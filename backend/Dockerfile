# ── ContractGuard Backend ──────────────────────────────────────────
# Python 3.11-slim base with WeasyPrint system dependencies
FROM python:3.11-slim

# ── System dependencies for WeasyPrint PDF generation ───────────
# libpango, libharfbuzz, libgdk-pixbuf, cairo, and fontconfig
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libgdk-pixbuf-2.0-0 \
    libgdk-pixbuf2.0-common \
    libcairo2 \
    libpangocairo-1.0-0 \
    libffi-dev \
    libpango1.0-dev \
    libcairo2-dev \
    fonts-liberation \
    fonts-dejavu-core \
    fontconfig \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Application ─────────────────────────────────────────────────
WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code (startup.sh must be executable)
COPY . .
RUN chmod +x /app/startup.sh

# Create directories for uploads and reports
RUN mkdir -p /app/uploads /app/reports /app/qdrant_data

# Expose the application port (Render sets PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/api/health')" || exit 1

# Startup command — uses startup.sh for auto-seed logic
CMD ["/app/startup.sh"]
