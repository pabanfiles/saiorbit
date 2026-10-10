# PDFEdit

- `site/`    – static website (index.html = PDF editor, tools.html = all PDF tools). No build step.
- `backend/` – FastAPI + PyMuPDF server (real text replacement, Bangla fonts, protect/unlock/compress, Word/Excel conversion).

## 1. Host the website on Cloudflare Pages
Workers & Pages → Create → Pages → Connect to Git → pick this repo.
- Framework preset: None
- Build command: (leave empty)
- Build output directory: `site`

## 2. Host the backend (needed for real text deletion, Bangla, Protect/Unlock, Word conversion)
See `backend/DEPLOY.md` (Hugging Face Spaces / Render / Fly.io). Upload only the files inside `backend/`.

## 3. Connect them
Open your site → ⚙ Backend → paste the backend URL → Save. The chip should turn green: "Real edit mode".
Without a backend the site still works in Browser mode (old text is covered, not deleted).
