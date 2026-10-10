"""
Sai Digital — Memory-safe downloader for Render Free tier (512 MB RAM).
Uses semaphore to enforce single concurrent download + low-buffer streaming.
"""

import os
import time
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yt_dlp

logger = logging.getLogger("sai_digital.downloader")

# ============================================================================
# GLOBAL CONCURRENCY CONTROL — CRITICAL for 512 MB RAM
# ============================================================================
# Only ONE download at a time. Others wait in queue.
# Increase to 2 only if you upgrade to Render Starter or Oracle Cloud.
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(1)
FFMPEG_SEMAPHORE = asyncio.Semaphore(1)

DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", "downloads"))
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_AGE_SECONDS = int(os.getenv("MAX_FILE_AGE_SECONDS", "300"))


# ============================================================================
# MEMORY-SAFE YT-DLP OPTIONS
# ============================================================================
def _base_ydl_opts() -> Dict[str, Any]:
    """
    Shared yt-dlp opts designed for 512 MB RAM.
    """
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "no_part": True,
        "nocheckcertificate": True,
        "concurrent_fragment_downloads": 1,
        "buffersize": 1024 * 1024,  # 1 MB
        "retries": 2,
        "fragment_retries": 2,
        "socket_timeout": 20,
        "http_chunk_size": 1024 * 1024,  # 1 MB chunks
        "noprogress": True,
        "logtostderr": False,
        "skip_download": False,
    }


# ============================================================================
# METADATA EXTRACTION
# ============================================================================
async def extract_info(url: str) -> Optional[Dict[str, Any]]:
    """Extract video metadata without downloading."""
    ydl_opts = _base_ydl_opts()
    ydl_opts["skip_download"] = True

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await asyncio.to_thread(_extract)
        return info
    except Exception as e:
        logger.error(f"extract_info failed for {url}: {e}")
        return None


# ============================================================================
# VIDEO DOWNLOAD (MP4)
# ============================================================================
async def download_video(url: str, format_id: str = "best") -> Optional[Path]:
    """Download video with semaphore guard."""
    async with DOWNLOAD_SEMAPHORE:
        logger.info(f"[SEMAPHORE ACQUIRED] video download: {url}")
        started = time.time()

        file_id = uuid.uuid4().hex[:12]
        out_template = str(DOWNLOADS_DIR / f"{file_id}.%(ext)s")

        ydl_opts = _base_ydl_opts()
        ydl_opts.update({
            "format": format_id,
            "outtmpl": out_template,
            "merge_output_format": "mp4",
            "postprocessors": [],
        })

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.wait_for(
                asyncio.to_thread(_download),
                timeout=180,
            )
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] video download exceeded 180s: {url}")
            _cleanup_partial(file_id)
            return None
        except Exception as e:
            logger.error(f"download_video failed: {e}")
            _cleanup_partial(file_id)
            return None

        result = _find_downloaded_file(file_id)
        if result:
            logger.info(f"[DONE] video in {time.time() - started:.1f}s → {result.name}")
        return result


# ============================================================================
# AUDIO DOWNLOAD (MP3)
# ============================================================================
async def download_audio(url: str, format_id: str = "bestaudio") -> Optional[Path]:
    """Download audio and convert to MP3."""
    async with FFMPEG_SEMAPHORE:
        logger.info(f"[FFMPEG SEMAPHORE] audio download: {url}")
        started = time.time()

        file_id = uuid.uuid4().hex[:12]
        out_template = str(DOWNLOADS_DIR / f"{file_id}.%(ext)s")

        ydl_opts = _base_ydl_opts()
        ydl_opts.update({
            "format": format_id,
            "outtmpl": out_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "postprocessor_args": {
                "ffmpeg": ["-threads", "1", "-bufsize", "1M"],
            },
        })

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.wait_for(
                asyncio.to_thread(_download),
                timeout=240,
            )
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] audio download exceeded 240s: {url}")
            _cleanup_partial(file_id)
            return None
        except Exception as e:
            logger.error(f"download_audio failed: {e}")
            _cleanup_partial(file_id)
            return None

        result = _find_downloaded_file(file_id)
        if result:
            logger.info(f"[DONE] audio in {time.time() - started:.1f}s → {result.name}")
        return result


# ============================================================================
# HELPERS
# ============================================================================
def _find_downloaded_file(file_id: str) -> Optional[Path]:
    """Find the downloaded file by its uuid prefix."""
    matches = list(DOWNLOADS_DIR.glob(f"{file_id}.*"))
    matches = [m for m in matches if not m.name.endswith(".part")]
    if not matches:
        return None
    for ext in (".mp4", ".mp3", ".webm", ".m4a"):
        for m in matches:
            if m.suffix == ext:
                return m
    return matches[0]


def _cleanup_partial(file_id: str) -> None:
    """Remove any partial files for a failed download."""
    for f in DOWNLOADS_DIR.glob(f"{file_id}.*"):
        try:
            f.unlink()
        except Exception:
            pass


async def cleanup_old_files(max_age_seconds: int = MAX_FILE_AGE_SECONDS) -> int:
    """Delete files older than max_age_seconds."""
    now = time.time()
    removed = 0
    for f in DOWNLOADS_DIR.glob("*"):
        if not f.is_file():
            continue
        try:
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink()
                removed += 1
        except Exception:
            pass
    return removed


def get_queue_status() -> Dict[str, Any]:
    """Return current semaphore state."""
    return {
        "download_active": DOWNLOAD_SEMAPHORE.locked(),
        "ffmpeg_active": FFMPEG_SEMAPHORE.locked(),
        "download_slots": 1,
        "ffmpeg_slots": 1,
    }
