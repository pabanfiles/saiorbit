"""
Sai Digital — FastAPI backend (Fixed: format labels + sound + Instagram).
YouTube removed.
"""

import os
import re
import time
import asyncio
import logging
from contextlib import asynccontextmanager
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sai_digital")

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
MAX_FILE_AGE_SECONDS = int(os.getenv("MAX_FILE_AGE_SECONDS", "300"))

ALLOWED_ORIGINS = [
    "https://saiorbit.pages.dev",
    "https://saiorbit.com",
    "https://www.saiorbit.com",
    "https://sai-digital.onrender.com",
    "https://sd.ssssobankura.org",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
]

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


async def periodic_cleanup():
    while True:
        try:
            removed = await cleanup_old_files()
            if removed:
                logger.info(f"cleanup: removed {removed} old file(s)")
        except Exception as e:
            logger.warning(f"cleanup error: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Sai Digital starting up...")
    logger.info(f"DOWNLOADS_DIR = {DOWNLOADS_DIR.resolve()}")
    logger.info(f"ENVIRONMENT = {ENVIRONMENT}")
    logger.info("=" * 60)
    task = asyncio.create_task(periodic_cleanup())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Sai Digital shutting down.")


app = FastAPI(
    title="Sai Digital — Video Downloader",
    version="6.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.saiorbit\.pages\.dev",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length"],
    max_age=3600,
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Sai Digital Video Downloader",
        "version": "6.1",
    }


@app.get("/health")
async def health():
    status = get_queue_status()
    return {
        "status": "ok",
        "version": "6.1",
        "environment": ENVIRONMENT,
        "queue": status,
        "timestamp": time.time(),
    }


# ============================================================================
# ✅ FIXED: Format label logic
# ============================================================================
def _get_quality_label(f: dict) -> str:
    """
    Format label ঠিকভাবে বানাও।
    Priority: height (720p) > format_note > resolution > ext
    """
    # 1. Height দিয়ে (সবচেয়ে ভালো)
    height = f.get("height")
    if height:
        return f"{height}p"
    
    # 2. Resolution string
    resolution = f.get("resolution")
    if resolution and resolution != "audio only":
        return resolution
    
    # 3. Format note (কিন্তু "DASH video" বাদ দাও)
    format_note = f.get("format_note")
    if format_note:
        # "DASH video" → "Video"
        clean = re.sub(r'\bdash\b', '', format_note, flags=re.I).strip()
        if clean:
            return clean
    
    # 4. Format string থেকে height বের করো
    fmt_str = f.get("format") or ""
    m = re.search(r'(\d{3,4})p', fmt_str)
    if m:
        return f"{m.group(1)}p"
    
    # 5. Audio only
    if f.get("acodec") and f.get("vcodec") in (None, "none"):
        abr = f.get("abr")
        if abr:
            return f"Audio {int(abr)}kbps"
        return "Audio"
    
    # 6. Fallback: ext
    ext = (f.get("ext") or "").upper()
    return ext if ext else "Standard"


def _filter_formats(formats):
    """
    ✅ FIXED: Video+Audio formats আলাদা করে দেখাও।
    Merged detection improve করো।
    """
    out = []
    
    for f in formats:
        if not f.get("url"):
            continue
        
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        has_video = vcodec not in (None, "none")
        has_audio = acodec not in (None, "none")
        
        # ✅ FIXED: Audio-only বাদ দাও video list থেকে
        # (audio tab-এ আলাদাভাবে দেখাব)
        if not has_video:
            continue
        
        # Filesize calculation
        filesize = f.get("filesize") or f.get("filesize_approx")
        
        quality = _get_quality_label(f)
        
        out.append({
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "quality": quality,
            "height": f.get("height"),
            "filesize": filesize,
            "vcodec": vcodec,
            "acodec": acodec,
            "has_video": has_video,
            "has_audio": has_audio,
            "is_merged": has_video and has_audio,  # একই stream-এ দুটোই
            "is_direct": False,
            "fps": f.get("fps"),
            "tbr": f.get("tbr"),
        })
    
    # ✅ Sort: Height অনুযায়ী (720p > 480p > 360p)
    out.sort(key=lambda x: (
        -(x.get("height") or 0),
        -(x.get("tbr") or 0),
    ))
    
    return out


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
            detail="Could not extract video info. Content may be private, removed, or region-locked.",
        )

    instagram = is_instagram(url)
    instagram_story = is_instagram_story(url)
    media_type = "video"

    if instagram:
        if "entries" in info and info["entries"]:
            media_type = "carousel"
        elif info.get("ext", "").lower() in ("jpg", "jpeg", "png", "webp"):
            media_type = "photo"

    formats = []
    
    # ✅ FIXED: Carousel handling
    if media_type == "carousel" and info.get("entries"):
        for idx, entry in enumerate(info["entries"]):
            if not entry:
                continue
            entry_ext = entry.get("ext", "jpg")
            is_photo = entry_ext.lower() in ("jpg", "jpeg", "png", "webp")
            formats.append({
                "format_id": f"carousel_{idx}",
                "ext": entry_ext,
                "quality": f"Item {idx + 1} ({'Photo' if is_photo else 'Video'})",
                "height": None,
                "filesize": entry.get("filesize"),
                "vcodec": None if is_photo else "h264",
                "acodec": None if is_photo else "aac",
                "has_video": not is_photo,
                "has_audio": not is_photo,
                "is_merged": not is_photo,
                "direct_url": entry.get("url"),
                "is_photo": is_photo,
                "is_direct": True,
            })
    else:
        formats = _filter_formats(info.get("formats") or [])

    # ✅ FIXED: Photo detection robust
    if media_type == "photo":
        photo_url = (
            info.get("url")
            or (info.get("thumbnails") or [{}])[-1].get("url")
        )
        if photo_url:
            formats = [{
                "format_id": "photo",
                "ext": info.get("ext", "jpg"),
                "quality": "Original Photo",
                "height": None,
                "filesize": info.get("filesize"),
                "vcodec": None,
                "acodec": None,
                "has_video": False,
                "has_audio": False,
                "is_merged": False,
                "direct_url": photo_url,
                "is_photo": True,
                "is_direct": True,
            }]

    return {
        "title": info.get("title") or "Media",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "platform": info.get("extractor_key") or info.get("extractor") or "Unknown",
        "formats": formats,
        "webpage_url": info.get("webpage_url") or url,
        "media_type": media_type,
        "is_instagram": instagram,
        "is_instagram_story": instagram_story,
    }


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
    direct_url = body.get("direct_url")

    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    if not is_allowed_url(url):
        raise HTTPException(status_code=400, detail="Unsupported platform or invalid URL")

    # ✅ Direct URL (photo/carousel) — باckend download করবে না
    if direct_url:
        return JSONResponse({
            "type": "direct",
            "url": direct_url,
            "message": "Direct download URL",
        })

    started = time.time()

    try:
        if media_type == "audio":
            file_path = await download_audio(url, format_id)
        elif is_instagram(url) and media_type in ("photo", "carousel", "story"):
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
    filename = f"orbit-video-{int(time.time())}{suffix}"

    logger.info(
        f"Serving {file_path.name} ({file_path.stat().st_size / 1e6:.1f} MB) "
        f"after {time.time() - started:.1f}s"
    )

    async def _delete_later():
        await asyncio.sleep(15)
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
