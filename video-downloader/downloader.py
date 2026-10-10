"""
Sai Digital — Memory-safe downloader + Instagram photo/story support.
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
# GLOBAL CONCURRENCY CONTROL
# ============================================================================
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(1)
FFMPEG_SEMAPHORE = asyncio.Semaphore(1)

DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", "downloads"))
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_AGE_SECONDS = int(os.getenv("MAX_FILE_AGE_SECONDS", "300"))


# ============================================================================
# MEMORY-SAFE YT-DLP OPTIONS
# ============================================================================
def _base_ydl_opts() -> Dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,  # ← IMPORTANT: Instagram carousel = playlist
        "no_part": True,
        "nocheckcertificate": True,
        "concurrent_fragment_downloads": 1,
        "buffersize": 1024 * 1024,
        "retries": 2,
        "fragment_retries": 2,
        "socket_timeout": 30,
        "http_chunk_size": 1024 * 1024,
        "noprogress": True,
        "logtostderr": False,
        "skip_download": False,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }


# ============================================================================
# METADATA EXTRACTION
# ============================================================================
async def extract_info(url: str) -> Optional[Dict[str, Any]]:
    ydl_opts = _base_ydl_opts()
    ydl_opts["skip_download"] = True
    # Don't expand playlist for video URLs
    if "instagram.com" not in url.lower():
        ydl_opts["noplaylist"] = True

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
    async with DOWNLOAD_SEMAPHORE:
        logger.info(f"[SEMAPHORE] video download: {url}")
        started = time.time()

        file_id = uuid.uuid4().hex[:12]
        out_template = str(DOWNLOADS_DIR / f"{file_id}.%(ext)s")

        ydl_opts = _base_ydl_opts()
        ydl_opts.update({
            "format": format_id,
            "outtmpl": out_template,
            "merge_output_format": "mp4",
        })

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.wait_for(asyncio.to_thread(_download), timeout=180)
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] video: {url}")
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
    async with FFMPEG_SEMAPHORE:
        logger.info(f"[FFMPEG] audio download: {url}")
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
        })

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.wait_for(asyncio.to_thread(_download), timeout=240)
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] audio: {url}")
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
# INSTAGRAM PHOTO / CAROUSEL DOWNLOAD
# ============================================================================
async def download_instagram_media(url: str) -> Optional[Path]:
    """
    Download Instagram photo or carousel (multiple images/videos).
    Returns the FIRST media file (for carousel, yt-dlp will download all).
    """
    async with DOWNLOAD_SEMAPHORE:
        logger.info(f"[INSTAGRAM] downloading media: {url}")
        started = time.time()

        file_id = uuid.uuid4().hex[:12]
        out_template = str(DOWNLOADS_DIR / f"{file_id}_%(playlist_index)s.%(ext)s")

        ydl_opts = _base_ydl_opts()
        ydl_opts.update({
            "format": "best",
            "outtmpl": out_template,
            "noplaylist": False,  # carousel support
        })

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.wait_for(asyncio.to_thread(_download), timeout=180)
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] instagram: {url}")
            return None
        except Exception as e:
            logger.error(f"instagram download failed: {e}")
            return None

        # Find any downloaded file
        matches = list(DOWNLOADS_DIR.glob(f"{file_id}*"))
        matches = [m for m in matches if not m.name.endswith(".part")]
        if not matches:
            return None

        # Prefer video, then image
        for ext in (".mp4", ".jpg", ".jpeg", ".png", ".webp"):
            for m in matches:
                if m.suffix == ext:
                    logger.info(f"[DONE] instagram in {time.time() - started:.1f}s → {m.name}")
                    return m
        return matches[0]


# ============================================================================
# HELPERS
# ============================================================================
def _find_downloaded_file(file_id: str) -> Optional[Path]:
    matches = list(DOWNLOADS_DIR.glob(f"{file_id}.*"))
    matches = [m for m in matches if not m.name.endswith(".part")]
    if not matches:
        return None
    for ext in (".mp4", ".mp3", ".webm", ".m4a", ".jpg", ".jpeg", ".png", ".webp"):
        for m in matches:
            if m.suffix == ext:
                return m
    return matches[0]


def _cleanup_partial(file_id: str) -> None:
    for f in DOWNLOADS_DIR.glob(f"{file_id}.*"):
        try:
            f.unlink()
        except Exception:
            pass


async def cleanup_old_files(max_age_seconds: int = MAX_FILE_AGE_SECONDS) -> int:
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
    return {
        "download_active": DOWNLOAD_SEMAPHORE.locked(),
        "ffmpeg_active": FFMPEG_SEMAPHORE.locked(),
        "download_slots": 1,
        "ffmpeg_slots": 1,
    }
