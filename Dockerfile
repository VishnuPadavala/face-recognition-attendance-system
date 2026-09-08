# ─── Face Recognition Attendance System ──────────────────────────────────────
# Uses python:3.10-slim with pre-built dlib wheel to avoid long compilation
FROM python:3.10-slim

# Install OS-level deps needed by dlib, face_recognition, and opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libopenblas-dev \
        liblapack-dev \
        libx11-dev \
        libgtk-3-dev \
        libboost-python-dev \
        libboost-thread-dev \
        python3-dev \
        wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Step 1: Install dlib first (slow compile step — kept in its own layer for caching)
RUN pip install --no-cache-dir dlib==19.24.2

# ── Step 2: Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Step 3: Copy application source
COPY . .

# ── Step 4: Ensure runtime directories exist
RUN mkdir -p static/faces database

# Expose port and run with gunicorn
EXPOSE 10000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--workers", "1", "--threads", "4", "--timeout", "120"]
