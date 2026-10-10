FROM python:3.11-slim

# Install ffmpeg + minimal deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade yt-dlp

# Copy app
COPY . .

# Create downloads dir
RUN mkdir -p downloads

# Env defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DOWNLOADS_DIR=downloads
ENV MAX_FILE_AGE_SECONDS=300

EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --limit-concurrency 8 --timeout-keep-alive 30"]
