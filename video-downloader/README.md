# Sai Digital — Premium Universal Video Downloader & Tech Blog

Sai Digital is a modern, high-performance, single-page Universal Video Downloader and AdSense-ready tech publication built with **Python 3.11**, **FastAPI**, **Uvicorn**, **yt-dlp**, and **FFmpeg**.

> **Note**: This application is strictly a video downloading, audio conversion, and tech education utility for public media. It is **NOT** a proxy or VPN and contains no proxy/VPN logic.

---

## 🎨 UI / UX Highlights

- **Design Language**: Glassmorphism + Neumorphism hybrid on deep navy background (`#0a0e27`).
- **Gradient Accents**: Purple (`#8b5cf6`) → Pink (`#ec4899`) → Cyan (`#06b6d4`).
- **Typography**: Inter / Plus Jakarta Sans with crystal-clear readability and typography hierarchy.
- **Responsive Layout**: Mobile-first architecture tested on phones, tablets, and wide desktop displays with a sleek mobile drawer menu.
- **One-Click Instant Download**: Paste link → Auto-detects platform → Fetch formats → Click format card → Immediate file download.
- **Full Blog System**: AdSense-ready knowledge base with rich markdown rendering, category filters, real-time search, and social media share tools.

---

## 🚀 Key Features

- **Universal Platform Auto-Detection**: Instant client and server detection for Facebook, Instagram, TikTok, Twitter / X, Pinterest, Reddit, Vimeo, Threads, and generic web streams.
- **Fast In-Memory Cache & Direct Streaming**: Sub-millisecond format retrieval and direct CDN streaming starting downloads in under 1 second.
- **Video Resolutions**: Categorized and sorted from 144p up to 4K Ultra HD in clean MP4 containers with auto-muxed audio.
- **Studio MP3 Audio Extraction**: Dynamic conversion to MP3 at 320 kbps (Ultra), 192 kbps (High Quality), and 128 kbps (Standard) powered by FFmpeg.
- **AdSense & Policy Pages**: Complete suite of compliant pages including About Us, Privacy Policy (GDPR + India DPDP Act), Terms of Service with DMCA policy, Disclaimer, and Contact Form.
- **SEO & Social Sharing**: Dynamic `/sitemap.xml`, `/robots.txt`, OpenGraph tags, JSON-LD Schema.org metadata, and social share buttons (Facebook, X/Twitter, WhatsApp, LinkedIn, Reddit, Copy Link).

---

## 📁 Project Structure

```
├── Dockerfile              # Hugging Face Spaces deployment config (port 7860)
├── requirements.txt        # Python dependency manifest
├── .env.example            # Environment template
├── .env                    # Local environment settings
├── main.py                 # FastAPI application, rate limiter, routing & lifespan
├── downloader.py           # yt-dlp & FFmpeg media extraction & conversion logic
├── blog_manager.py         # Blog markdown loader, parser, search & category engine
├── utils.py                # Platform regex patterns, sizing helpers & bilingual errors
├── blog_posts/             # 5 SEO-rich 800-1200 word articles
├── templates/
│   ├── index.html          # Main downloader interface
│   ├── blog.html           # Blog archive & search page
│   ├── post.html           # Individual article layout with social shares
│   ├── about.html          # About Sai Digital story & team
│   ├── privacy.html        # GDPR + India compliant Privacy Policy
│   ├── terms.html          # Terms of Service & DMCA notice
│   ├── contact.html        # Contact form & social channels
│   └── disclaimer.html     # Non-affiliation notice
├── static/
│   ├── style.css           # Glassmorphism, animations, responsive grid & typography
│   └── app.js              # One-click download controller & toast system
├── downloads/              # Temporary cache directory for generated media
└── README.md               # Documentation
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Server host binding |
| `PORT` | `7860` | Server port (7860 for Hugging Face Spaces) |
| `DOWNLOADS_DIR` | `downloads` | Local folder for temporary downloads |
| `MAX_FILE_AGE_SECONDS`| `1800` | Expiration time for cached files (30 mins) |
| `RATE_LIMIT_PER_MINUTE` | `5` | Request rate limit per IP |
| `ENABLE_YOUTUBE` | `false` | Disable or enable YouTube extractor |
| `ENVIRONMENT` | `production` | Deployment environment |

---

## 🛠️ Local Development

### 1. Requirements
- Python 3.10 or 3.11
- FFmpeg installed (`sudo apt install ffmpeg` or `brew install ffmpeg`)

### 2. Installation
```bash
git clone <repo-url>
cd vidgrab

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Server
```bash
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```
Open your browser at `http://localhost:7860`.

---

## 🐳 Hugging Face Spaces Deployment

VidGrab includes a production-ready `Dockerfile` specifically tuned for Hugging Face Spaces:

1. Create a new Space on **Hugging Face** with **Docker** SDK.
2. Push this repository to your Space.
3. Hugging Face Spaces automatically builds the Docker image and exposes port `7860`.

---

## 📡 API Endpoints

- `GET /` — Serves the frontend single-page web app.
- `GET /health` — Returns backend health, engine status, and yt-dlp version.
- `POST /api/info` — Body: `{"url": "..."}`. Returns video metadata, thumbnail, duration, and available formats.
- `POST /api/download` — Body: `{"url": "...", "format_id": "...", "type": "video"|"audio", "quality": "..."}`. Initiates download and returns the media file with `Content-Disposition: attachment`.
- `GET /api/download-direct` — Direct download endpoint query params (`url`, `format_id`, `type`, `quality`).

---

## ⚖️ License & Disclaimer

VidGrab is built for personal archiving and educational research. Always adhere to the terms of service of the media platform and respect content copyright owners.
