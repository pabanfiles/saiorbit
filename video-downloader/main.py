"""
Sai Digital — FastAPI backend (fixed CORS + Instagram photo/story support).
"""

import os
import re
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from downloader import (
    extract_info,
    download_video,
    download_audio,
    download_instagram_media,
    cleanup_old_files,
    get_queue_status,
    DOWNLOADS_DIR,
)

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sai_digital")


# ============================================================================
# ENV
# ============================================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
MAX_FILE_AGE_SECONDS = int(os.getenv("MAX_FILE_AGE_SECONDS", "300"))

# ✅ FIXED: allow all Cloudflare Pages subdomains + localhost
ALLOWED_ORIGINS = [
    "https://saiorbit.pages.dev",
    "https://*.saiorbit.pages.dev",        # preview deployments
    "https://saiorbit.com",
    "https://www.saiorbit.com",
    "https://sai-digital.onrender.com",
    "https://sd.ssssobankura.org",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]


# ============================================================================
# URL VALIDATION
# ============================================================================
ALLOWED_DOMAINS = [
    "facebook.com", "fb.watch", "fb.com",
    "instagram.com", "instagr.am",
    "tiktok.com",
    "twitter.com", "x.com",
    "pinterest.com", "pin.it",
    "reddit.com", "redd.it",
    "vimeo.com",
    "threads.net", "threads.com",
    "youtube.com", "youtu.be", "m.youtube.com",
]


def is_allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False


def is_instagram(url: str) -> bool:
    return bool(re.search(r'instagram\.com|instagr\.am', url, re.I))


def is_instagram_story(url: str) -> bool:
    return bool(re.search(r'instagram\.com/stories/', url, re.I))


# ============================================================================
# RATE LIMITING
# ============================================================================
_rate_buckets: dict = defaultdict(list)


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    window = 60.0
    bucket = _rate_buckets[ip]
    _rate_buckets[ip] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[ip]) >= RATE_LIMIT_PER_MINUTE:
        return False
    _rate_buckets[ip].append(now)
    return True


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# ============================================================================
# BACKGROUND CLEANUP
# ============================================================================
async def periodic_cleanup():
    while True:
        try:
            removed = await cleanup_old_files()
            if removed:
                logger.info(f"cleanup: removed {removed} old file(s)")
        except Exception as e:
            logger.warning(f"cleanup error: {e}")
        await asyncio.sleep(60)


# ============================================================================
# LIFESPAN
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Sai Digital starting up...")
    logger.info(f"DOWNLOADS_DIR = {DOWNLOADS_DIR.resolve()}")
    logger.info(f"ENVIRONMENT = {ENVIRONMENT}")
    logger.info(f"RATE_LIMIT = {RATE_LIMIT_PER_MINUTE}/min")
    logger.info("=" * 60)
    task = asyncio.create_task(periodic_cleanup())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Sai Digital shutting down.")


# ============================================================================
# APP
# ============================================================================
app = FastAPI(
    title="Sai Digital — Video Downloader",
    version="5.0",
    lifespan=lifespan,
)

# ✅ FIXED CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.saiorbit\.pages\.dev",  # সব preview URL
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)


# ============================================================================
# HEALTH
# ============================================================================
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Sai Digital Video Downloader",
        "version": "5.0",
    }


@app.get("/health")
async def health():
    status = get_queue_status()
    return {
        "status": "ok",
        "version": "5.0",
        "environment": ENVIRONMENT,
        "queue": status,
        "timestamp": time.time(),
    }


# ============================================================================
# API — INFO
# ============================================================================
@app.post("/api/info")
async def api_info(request: Request):
    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    url = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    if not is_allowed_url(url):
        raise HTTPException(status_code=400, detail="Unsupported platform or invalid URL")

    info = await extract_info(url)
    if not info:
        raise HTTPException(
            status_code=502,
            detail="Could not extract video info. Check URL or try a different platform.",
        )

    # Instagram photo/carousel detection
    instagram = is_instagram(url)
    media_type = "video"
    
    if instagram:
        # Check if entries (carousel) or single
        if "entries" in info and info["entries"]:
            media_type = "carousel"
        elif info.get("ext", "").lower() in ("jpg", "jpeg", "png", "webp"):
            media_type = "photo"

    # Build formats list
    formats = _filter_formats(info.get("formats") or [])

    # For photos, add a direct download entry
    if media_type == "photo" and info.get("url"):
        formats = [{
            "format_id": "photo",
            "ext": info.get("ext", "jpg"),
            "quality": "Original",
            "filesize": None,
            "vcodec": "none",
            "acodec": "none",
            "has_video": False,
            "has_audio": False,
            "direct_url": info.get("url"),
            "is_photo": True,
        }]

    return {
        "title": info.get("title") or "Instagram Media",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "platform": info.get("extractor_key") or info.get("extractor") or "Unknown",
        "formats": formats,
        "webpage_url": info.get("webpage_url") or url,
        "media_type": media_type,
        "is_instagram": instagram,
    }


def _filter_formats(formats):
    out = []
    for f in formats:
        if not f.get("url"):
            continue
        out.append({
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "quality": f.get("format_note") or f.get("resolution") or f.get("format"),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "vcodec": f.get("vcodec"),
            "acodec": f.get("acodec"),
            "has_video": f.get("vcodec") not in (None, "none"),
            "has_audio": f.get("acodec") not in (None, "none"),
        })
    return out


# ============================================================================
# API — DOWNLOAD DIRECT
# ============================================================================
@app.post("/api/download-direct")
async def download_direct(request: Request):
    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    url = (body.get("url") or "").strip()
    format_id = body.get("format_id") or "best"
    media_type = body.get("type") or "video"

    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    if not is_allowed_url(url):
        raise HTTPException(status_code=400, detail="Unsupported platform or invalid URL")

    # Handle direct URL (Instagram photo)
    direct_url = body.get("direct_url")
    if direct_url:
        return JSONResponse({
            "type": "direct",
            "url": direct_url,
            "message": "Direct download URL — open in browser",
        })

    started = time.time()

    try:
        if media_type == "audio":
            file_path = await download_audio(url, format_id)
        elif is_instagram(url) and media_type in ("photo", "carousel"):
            file_path = await download_instagram_media(url)
        else:
            file_path = await download_video(url, format_id)
    except Exception as e:
        logger.error(f"download failed: {e}")
        raise HTTPException(status_code=502, detail=f"Download failed: {str(e)[:200]}")

    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=502,
            detail="Download failed. Content may be private, region-locked, or removed.",
        )

    suffix = file_path.suffix.lower()
    media_map = {
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    media = media_map.get(suffix, "application/octet-stream")
    filename = f"sai-digital-{int(time.time())}{suffix}"

    logger.info(
        f"Serving {file_path.name} ({file_path.stat().st_size / 1e6:.1f} MB) "
        f"after {time.time() - started:.1f}s"
    )

    async def _delete_later():
        await asyncio.sleep(10)
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

    asyncio.create_task(_delete_later())

    return FileResponse(
        path=file_path,
        media_type=media,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ============================================================================
# API — CONTACT
# ============================================================================
@app.post("/api/contact")
async def contact_api(request: Request):
    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    message = (body.get("message") or "").strip()

    if not name or not email or not message:
        raise HTTPException(status_code=400, detail="Name, email, and message are required")

    logger.info(f"Contact form: {name} <{email}>")
    return {"success": True, "message": "Thank you! We'll get back to you soon."}
