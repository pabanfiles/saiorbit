# Deploying the backend

Folder contents: `main.py`, `requirements.txt`, `Dockerfile`. Default port: 7860.
After deploy, open `<your-url>/health` — expect `{"status":"ok","fonts_loaded":N,"libreoffice_available":true,...}`
and `<your-url>/api/config` to see enabled features. Then paste the URL into ⚙ Backend on the site.

## Hugging Face Spaces (free CPU, 16 GB RAM, best option)
1. New Space → SDK: **Docker**. Upload the 3 files plus a `README.md` that starts with:
   ```
   ---
   title: PDF Backend
   sdk: docker
   app_port: 7860
   ---
   ```
2. URL: `https://<user>-<space>.hf.space`

## Render (Docker web service)
New → Web Service → connect repo (root dir = backend) → Runtime: Docker. Health check path: `/health`.
Free tier has 512 MB RAM: text edit/protect/compress are fine, LibreOffice conversions may run out of memory
(use a paid instance for Word/Excel/PPT → PDF).

## Fly.io
```
fly launch --no-deploy        # in backend/, accept Dockerfile; set internal_port = 7860 in fly.toml
fly scale memory 1024         # LibreOffice needs more than the 256 MB default
fly deploy
```
Add to fly.toml: `[http_service]  internal_port = 7860  force_https = true`
and optionally `[[http_service.checks]] path = "/health"  interval = "30s"  timeout = "5s"`.

## Custom Bengali fonts
Drop extra `.ttf` files into `backend/fonts/` (or set `FONT_DIR`); names starting with
`NotoSansBengali` / `NotoSerifBengali` are picked up automatically.
