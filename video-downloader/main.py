"""
Sai Digital — FastAPI backend, memory-safe for Render Free tier.
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
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from downloader import (
    extract_info,
    download_video,
    download_audio,
    cleanup_old_files,
    get_queue_status,
    DOWNLOADS_DIR,
    DOWNLOAD_SEMAPHORE,
    FFMPEG_SEMAPHORE,
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
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))
ENABLE_YOUTUBE = os.getenv("ENABLE_YOUTUBE", "false").lower() == "true"
MAX_FILE_AGE_SECONDS = int(os.getenv("MAX_FILE_AGE_SECONDS", "300"))

ALLOWED_ORIGINS = [
    "https://sd.ssssobankura.org",
    "https://sai-digital.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


# ============================================================================
# URL VALIDATION (allow-list)
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
]
if ENABLE_YOUTUBE:
    ALLOWED_DOMAINS += ["youtube.com", "youtu.be", "m.youtube.com"]


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


# ============================================================================
# RATE LIMITING (in-memory, per-IP)
# ============================================================================
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    window = 60.0
    bucket = _rate_buckets[ip]
    # keep only recent entries
    _rate_buckets[ip] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[ip]) >= RATE_LIMIT_PER_MINUTE:
        return False
    _rate_buckets[ip].append(now)
    return True


def get_client_ip(request: Request) -> str:
    # Cloudflare / Render proxy headers
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# ============================================================================
# BACKGROUND CLEANUP TASK
# ============================================================================
async def periodic_cleanup():
    """Runs every 60s — deletes files older than MAX_FILE_AGE_SECONDS."""
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
    logger.info(f"ENABLE_YOUTUBE = {ENABLE_YOUTUBE}")
    logger.info(f"RATE_LIMIT = {RATE_LIMIT_PER_MINUTE}/min")
    logger.info("Concurrency: download=1, ffmpeg=1 (tuned for 512 MB RAM)")
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
    version="4.3",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ============================================================================
# PAGE ROUTES
# ============================================================================
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@app.get("/disclaimer", response_class=HTMLResponse)
async def disclaimer_page(request: Request):
    return templates.TemplateResponse("disclaimer.html", {"request": request})


# --- BLOG ROUTES (adjust to your existing blog loader) ---------------------
try:
    from blog_loader import get_all_posts, get_post_by_slug, get_categories
except ImportError:
    # Fallback if blog_loader not present
    def get_all_posts(q=None, category=None):
        return []
    def get_post_by_slug(slug):
        return None
    def get_categories():
        return []


@app.get("/blog", response_class=HTMLResponse)
async def blog_page(request: Request, q: str = "", category: str = ""):
    posts = get_all_posts(q=q, category=category)
    return templates.TemplateResponse("blog.html", {
        "request": request,
        "posts": posts,
        "categories": get_categories(),
        "search_query": q,
        "current_category": category,
    })


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_page(request: Request, slug: str):
    post = get_post_by_slug(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    related = [p for p in get_all_posts() if p.get("slug") != slug][:3]
    return templates.TemplateResponse("post.html", {
        "request": request,
        "post": post,
        "related_posts": related,
    })


# ============================================================================
# API — HEALTH
# ============================================================================
@app.get("/health")
async def health():
    status = get_queue_status()
    return {
        "status": "ok",
        "version": "4.3",
        "environment": ENVIRONMENT,
        "queue": status,
        "downloads_dir": str(DOWNLOADS_DIR),
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

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "platform": info.get("extractor_key") or info.get("extractor"),
        "formats": _filter_formats(info.get("formats") or []),
        "webpage_url": info.get("webpage_url"),
    }


def _filter_formats(formats):
    """Trim and normalize formats for frontend."""
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
    """
    Download a video/audio and stream it back.
    Uses semaphore so only 1 job runs at a time.
    """
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

    # Log queue status
    if DOWNLOAD_SEMAPHORE.locked() and media_type == "video":
        logger.info("video slot busy — request will queue")
    if FFMPEG_SEMAPHORE.locked() and media_type == "audio":
        logger.info("audio slot busy — request will queue")

    started = time.time()

    if media_type == "audio":
        file_path = await download_audio(url, format_id)
    else:
        file_path = await download_video(url, format_id)

    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=502,
            detail="Download failed. Video may be private, region-locked, or removed.",
        )

    suffix = file_path.suffix.lower()
    if suffix == ".mp3":
        media = "audio/mpeg"
    elif suffix == ".mp4":
        media = "video/mp4"
    else:
        media = "application/octet-stream"

    filename = f"sai-digital-{int(time.time())}{suffix}"

    logger.info(
        f"Serving {file_path.name} ({file_path.stat().st_size / 1e6:.1f} MB) "
        f"after {time.time() - started:.1f}s"
    )

    async def _delete_later():
        await asyncio.sleep(5)
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"deleted after serve: {file_path.name}")
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
# API — CONTACT (stub — adapt to your real implementation)
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

    # TODO: integrate with email service (Resend, SendGrid, or SMTP) if desired
    logger.info(f"Contact form: {name} <{email}>")

    return {"success": True, "message": "Thank you! We'll get back to you soon."}
