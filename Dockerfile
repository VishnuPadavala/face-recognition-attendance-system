# ─── Face Recognition Attendance System ──────────────────────────────────────
# Uses Miniconda to install pre-compiled dlib from conda-forge
# This avoids compiling dlib from source, which OOMs on Render free tier (512MB RAM)
FROM continuumio/miniconda3:latest

# Install system libs needed by opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Step 1: Install pre-compiled dlib from conda-forge (no C++ compilation!)
RUN conda install -c conda-forge -y python=3.10 dlib=19.24.1 \
    && conda clean -afy

# ── Step 2: Install remaining Python packages via pip
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Step 3: Copy application source
WORKDIR /app
COPY . .

# ── Step 4: Ensure runtime directories exist
RUN mkdir -p static/faces database

# Expose Render's default port and start gunicorn
EXPOSE 10000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--workers", "1", "--threads", "4", "--timeout", "120"]
