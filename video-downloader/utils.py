import re
import os
import unicodedata
from typing import Dict, Any, Optional
from urllib.parse import urlparse

# Platform patterns and brand metadata
PLATFORM_PATTERNS = [
    {
        "id": "facebook",
        "name": "Facebook",
        "color": "#1877F2",
        "icon": "facebook",
        "pattern": r"(?:https?:\/\/)?(?:www\.|m\.|web\.)?(?:facebook\.com|fb\.watch|fb\.com)\/.*",
    },
    {
        "id": "instagram",
        "name": "Instagram",
        "color": "#E1306C",
        "icon": "instagram",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/(?:p|reel|tv|stories)\/.*",
    },
    {
        "id": "tiktok",
        "name": "TikTok",
        "color": "#FE2C55",
        "icon": "video",
        "pattern": r"(?:https?:\/\/)?(?:www\.|vm\.|vt\.)?tiktok\.com\/.*",
    },
    {
        "id": "twitter",
        "name": "X / Twitter",
        "color": "#1DA1F2",
        "icon": "twitter",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/.+\/status\/.*",
    },
    {
        "id": "pinterest",
        "name": "Pinterest",
        "color": "#E60023",
        "icon": "pin",
        "pattern": r"(?:https?:\/\/)?(?:[a-z]{2}\.)?(?:pinterest\.com|pin\.it)\/.*",
    },
    {
        "id": "reddit",
        "name": "Reddit",
        "color": "#FF4500",
        "icon": "message-square",
        "pattern": r"(?:https?:\/\/)?(?:www\.|old\.|v\.)?reddit\.com\/.*|https?:\/\/redd\.it\/.*",
    },
    {
        "id": "vimeo",
        "name": "Vimeo",
        "color": "#1AB7EA",
        "icon": "play-circle",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?vimeo\.com\/.*",
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "color": "#FF0000",
        "icon": "youtube",
        "pattern": r"(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be)\/.*",
    },
    {
        "id": "threads",
        "name": "Threads",
        "color": "#FFFFFF",
        "icon": "at-sign",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?threads\.net\/.*",
    },
]

def detect_platform(url: str) -> Dict[str, Any]:
    """Auto-detects the social platform from a URL string."""
    clean_url = url.strip()
    for p in PLATFORM_PATTERNS:
        if re.search(p["pattern"], clean_url, re.IGNORECASE):
            return {
                "id": p["id"],
                "name": p["name"],
                "color": p["color"],
                "icon": p["icon"],
                "is_supported": p["id"] != "youtube" or os.getenv("ENABLE_YOUTUBE", "false").lower() == "true",
            }

    parsed = urlparse(clean_url)
    domain = parsed.netloc.replace("www.", "") if parsed.netloc else "Web"
    return {
        "id": "generic",
        "name": domain.capitalize() if domain else "Universal",
        "color": "#8b5cf6",
        "icon": "globe",
        "is_supported": True,
    }

def format_duration(seconds: Optional[float | int]) -> str:
    """Formats numeric duration into MM:SS or HH:MM:SS format."""
    if not seconds or seconds < 0:
        return "Live / Unknown"
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_size(size_bytes: Optional[int | float]) -> str:
    """Formats raw byte count into human readable units (MB, GB, KB)."""
    if not size_bytes or size_bytes <= 0:
        return "Approx. Stream"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.1f} {units[unit_index]}"

def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Safely sanitizes a string to be used as a cross-platform filesystem filename."""
    if not filename:
        return "vidgrab_download"
    # Normalize unicode
    filename = unicodedata.normalize("NFKD", filename)
    # Remove prohibited filename characters: / \ : * ? " < > |
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    filename = re.sub(r"\s+", "_", filename.strip())
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename or "vidgrab_download"

def classify_error(err: Exception | str) -> Dict[str, str]:
    """
    Translates raw backend or yt-dlp error messages into bilingual,
    user-friendly English and Bengali explanations.
    """
    msg = str(err).lower()

    if "youtube temporarily unavailable" in msg or "youtube is disabled" in msg or "enable_youtube" in msg:
        return {
            "status_code": 403,
            "title": "YouTube Temporarily Disabled",
            "en": "YouTube temporarily unavailable",
            "detail": "YouTube downloads are disabled on this instance as per current policy.",
        }
    if "private video" in msg or "this video is private" in msg:
        return {
            "status_code": 403,
            "title": "Private Media",
            "en": "This video is private",
            "detail": "The owner has set privacy settings that restrict access.",
        }
    if "login required" in msg or "sign in" in msg or "authentication" in msg or "logged-in" in msg or "credentials" in msg:
        return {
            "status_code": 401,
            "title": "Authentication Required",
            "en": "Login required to access this media",
            "detail": "The platform requires user credentials to view this content.",
        }
    if "drm" in msg or "copyright" in msg or "protected" in msg:
        return {
            "status_code": 403,
            "title": "DRM Protected",
            "en": "DRM protected, cannot download",
            "detail": "This stream is encrypted by digital rights management.",
        }
    if "unsupported url" in msg or "not supported" in msg or "no suitable extractor" in msg:
        return {
            "status_code": 400,
            "title": "Unsupported Platform",
            "en": "Site or URL not supported",
            "detail": "Please verify that the link is a valid public video URL.",
        }
    if "rate limit" in msg or "too many requests" in msg or "429" in msg:
        return {
            "status_code": 429,
            "title": "Rate Limit Exceeded",
            "en": "Too many requests, please wait a minute",
            "detail": "Please wait a moment before downloading another video.",
        }
    if "video unavailable" in msg or "404" in msg or "not found" in msg or "deleted" in msg:
        return {
            "status_code": 404,
            "title": "Video Unavailable",
            "en": "Video not found or was removed",
            "detail": "The requested video link could not be located.",
        }

    return {
        "status_code": 500,
        "title": "Download Error",
        "en": "Could not extract video. Please check the URL",
        "detail": str(err)[:200],
    }
