# ─── Build dlib (CPU-only, no X11/GUI needed) ─────────────────────────────────
FROM python:3.11-slim AS base

# Install OS-level build tools required by dlib and opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libopenblas-dev \
        liblapack-dev \
        libboost-all-dev \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (copy first for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Ensure runtime directories exist
RUN mkdir -p static/faces database

# Run with gunicorn: 1 worker (shared SQLite cache), 4 threads
EXPOSE 5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120"]
