# Works on Hugging Face Spaces (Docker), Render (Docker) and Fly.io.
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=7860

# LibreOffice (Word/Excel/PPT -> PDF), Noto fonts incl. Bengali, runtime libs for pdf2docx/opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-writer libreoffice-calc libreoffice-impress \
      fonts-noto-core fontconfig libglib2.0-0 libgl1 \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# Fail the build loudly if no Bengali font is installed
RUN test -n "$(fc-list :lang=bn)" && fc-list :lang=bn | head -3

# Non-root user (Hugging Face Spaces runs containers as uid 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --user -r requirements.txt
ENV PATH="/home/user/.local/bin:${PATH}"

COPY --chown=user main.py .

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/health'%os.environ.get('PORT','7860'))" || exit 1

# Render injects $PORT; Hugging Face expects 7860; Fly uses internal_port (set it to 7860).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
