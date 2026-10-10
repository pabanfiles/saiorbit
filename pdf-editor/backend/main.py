"""PDF editor backend: true text removal (redaction) + re-insertion with PyMuPDF,
Bangla font support (HarfBuzz-shaped), config/fonts/health endpoints, and PDF tools."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

import fitz  # PyMuPDF
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

try:  # optional: correct Bengali conjunct/vowel-sign shaping
    import uharfbuzz as hb
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    HAVE_SHAPING = True
except Exception:  # pragma: no cover
    HAVE_SHAPING = False

MAX_BYTES = 50 * 1024 * 1024
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="PDF Editor API", docs_url="/docs")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Font-Warnings", "X-Fonts-Used"],
)

# ----------------------------------------------------------------------------
# Font registry
# ----------------------------------------------------------------------------
BASE14 = {
    "helvetica": ("Helvetica", "helv"),
    "helvetica-bold": ("Helvetica Bold", "hebo"),
    "helvetica-italic": ("Helvetica Italic", "heit"),
    "times": ("Times", "tiro"),
    "times-bold": ("Times Bold", "tibo"),
    "times-italic": ("Times Italic", "tiit"),
    "courier": ("Courier", "cour"),
    "courier-bold": ("Courier Bold", "cobo"),
}


def _font_files() -> list[str]:
    roots = [
        os.environ.get("FONT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")),
        "/usr/share/fonts",
        "/usr/local/share/fonts",
    ]
    out: list[str] = []
    for root in roots:
        for dp, _dn, fns in os.walk(root):
            out += [os.path.join(dp, f) for f in fns if f.lower().endswith((".ttf", ".otf"))]
    return out


def _pick(files: list[str], family: str, bold: bool) -> str | None:
    cands = [
        p for p in files
        if os.path.basename(p).lower().startswith(family) and "ui" not in os.path.basename(p).lower()
    ]
    for p in cands:
        n = os.path.basename(p).lower()
        if any(x in n for x in ("condensed", "semibold", "extrabold", "italic")):
            continue
        if ("bold" in n) if bold else ("regular" in n):
            return p
    if bold:
        return None
    for p in cands:  # variable font, e.g. NotoSansBengali[wdth,wght].ttf (default instance)
        if "[" in os.path.basename(p):
            return p
    return cands[0] if cands else None


def build_registry() -> dict[str, dict[str, Any]]:
    files = _font_files()
    reg: dict[str, dict[str, Any]] = {}
    for fam, label in (("notosansbengali", "Noto Sans Bengali"), ("notoserifbengali", "Noto Serif Bengali")):
        for bold in (False, True):
            path = _pick(files, fam, bold)
            if path:
                fid = ("noto-sans-bengali" if "sans" in fam else "noto-serif-bengali") + ("-bold" if bold else "")
                reg[fid] = {"label": label + (" Bold" if bold else ""), "script": "bengali", "path": path}
    return reg


FONTS = build_registry()


def font_list() -> list[dict[str, Any]]:
    out = [{"id": k, "label": v[0], "script": "latin", "source": "builtin"} for k, v in BASE14.items()]
    out += [{"id": k, "label": v["label"], "script": v["script"], "source": "file"} for k, v in FONTS.items()]
    return out


def has_bengali_font() -> bool:
    return any(v["script"] == "bengali" for v in FONTS.values())


def _has(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


# ----------------------------------------------------------------------------
# HarfBuzz-shaped Bengali (drawn as vector glyph outlines so conjuncts are correct)
# ----------------------------------------------------------------------------
if HAVE_SHAPING:

    class _FitzPen(BasePen):
        def __init__(self, shape: fitz.Shape, ox: float, oy: float, k: float, glyph_set: Any) -> None:
            super().__init__(glyph_set)
            self.s, self.ox, self.oy, self.k = shape, ox, oy, k
            self.cur = self.start = fitz.Point(0, 0)

        def _p(self, pt: tuple[float, float]) -> fitz.Point:
            return fitz.Point(self.ox + pt[0] * self.k, self.oy - pt[1] * self.k)

        def _moveTo(self, pt):  # noqa: N802
            self.cur = self.start = self._p(pt)

        def _lineTo(self, pt):  # noqa: N802
            p = self._p(pt)
            self.s.draw_line(self.cur, p)
            self.cur = p

        def _curveToOne(self, p1, p2, p3):  # noqa: N802
            a, b, c = self._p(p1), self._p(p2), self._p(p3)
            self.s.draw_bezier(self.cur, a, b, c)
            self.cur = c

        def _qCurveToOne(self, p1, p2):  # noqa: N802
            q0, q1, q2 = self.cur, self._p(p1), self._p(p2)
            self.s.draw_bezier(q0, q0 + (q1 - q0) * (2 / 3), q2 + (q1 - q2) * (2 / 3), q2)
            self.cur = q2

        def _closePath(self):  # noqa: N802
            if self.cur != self.start:
                self.s.draw_line(self.cur, self.start)
            self.cur = self.start

    class ShapedFont:
        def __init__(self, path: str) -> None:
            self.face = hb.Face(hb.Blob.from_file_path(path))
            self.font = hb.Font(self.face)
            self.upem = self.face.upem
            self.tt = TTFont(path)
            self.gs = self.tt.getGlyphSet()

        def draw(self, page: fitz.Page, x: float, y: float, text: str, size: float, color: tuple) -> float:
            buf = hb.Buffer()
            buf.add_str(text)
            buf.guess_segment_properties()
            hb.shape(self.font, buf, {"kern": True, "liga": True})
            k = size / self.upem
            pen_x = 0.0
            shape = page.new_shape()
            for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
                name = self.tt.getGlyphName(info.codepoint)
                pen = _FitzPen(shape, x + (pen_x + pos.x_offset) * k, y - pos.y_offset * k, k, self.gs)
                self.gs[name].draw(pen)
                pen_x += pos.x_advance
            shape.finish(fill=color, color=None)
            shape.commit()
            return pen_x * k


_SHAPERS: dict[str, Any] = {}

BN = r"[\u0980-\u09FF\u0964\u0965\u200c\u200d]+"
BN_SPLIT = re.compile(rf"({BN}(?: +{BN})*)")


def split_runs(text: str) -> list[tuple[str, bool]]:
    return [(p, i % 2 == 1) for i, p in enumerate(BN_SPLIT.split(text)) if p]


# ----------------------------------------------------------------------------
# Font handling for edits
# ----------------------------------------------------------------------------
def strip_subset(name: str) -> str:
    return re.sub(r"^[A-Z]{6}\+", "", name)


def base14(name: str, flags: int) -> str:
    n = name.lower()
    bold = bool(flags & 16) or "bold" in n or "black" in n
    ital = bool(flags & 2) or "italic" in n or "oblique" in n
    if flags & 8 or "cour" in n or "mono" in n:
        fam = ("cour", "coit", "cobo", "cobi")
    elif flags & 4 or (any(k in n for k in ("times", "serif", "roman", "georgia", "garamond")) and "sans" not in n):
        fam = ("tiro", "tiit", "tibo", "tibi")
    else:
        fam = ("helv", "heit", "hebo", "hebi")
    return fam[(2 if bold else 0) + (1 if ital else 0)]


class FontManager:
    """Reuses the ORIGINAL embedded font; merges Noto Sans Bengali where glyphs are missing."""

    def __init__(self, doc: fitz.Document) -> None:
        self.doc = doc
        self.emb: dict[tuple[int, str], tuple[str | None, fitz.Font | None]] = {}
        self.reg: dict[tuple[int, str], tuple[str, fitz.Font]] = {}
        self.warnings: set[str] = set()
        self.used: dict[tuple[str, str, str], dict[str, str]] = {}

    def note(self, requested: str, used: str, source: str) -> None:
        self.used[(requested, used, source)] = {"requested": requested, "used": used, "source": source}

    def _embedded(self, page: fitz.Page, font: str) -> tuple[str | None, fitz.Font | None]:
        key = (page.number, font)
        if key in self.emb:
            return self.emb[key]
        res: tuple[str | None, fitz.Font | None] = (None, None)
        target = strip_subset(font)
        for f in page.get_fonts(full=True):
            xref, basefont = f[0], f[3]
            if strip_subset(basefont) != target:
                continue
            try:
                _n, _e, _t, buf = self.doc.extract_font(xref)
                if not buf:
                    continue
                fobj = fitz.Font(fontbuffer=buf)
                alias = f"EF{xref}"
                page.insert_font(fontname=alias, fontbuffer=buf)
                res = (alias, fobj)
                break
            except Exception:
                continue
        self.emb[key] = res
        return res

    def _registry(self, page: fitz.Page, fid: str) -> tuple[str, fitz.Font]:
        key = (page.number, fid)
        if key not in self.reg:
            with open(FONTS[fid]["path"], "rb") as fh:
                buf = fh.read()
            alias = f"RF{abs(hash(fid)) % 10**8}"
            page.insert_font(fontname=alias, fontbuffer=buf)
            self.reg[key] = (alias, fitz.Font(fontbuffer=buf))
        return self.reg[key]

    def _bengali_id(self, fid: str | None, flags: int) -> str | None:
        if fid and fid in FONTS and FONTS[fid]["script"] == "bengali":
            return fid
        serif, bold = bool(flags & 4), bool(flags & 16)
        for fam, b in (("serif" if serif else "sans", bold), ("serif" if serif else "sans", False), ("sans", False)):
            cand = f"noto-{fam}-bengali" + ("-bold" if b else "")
            if cand in FONTS:
                return cand
        return None

    def _latin_base(self, page: fitz.Page, font: str, flags: int, fid: str | None) -> tuple[str, fitz.Font]:
        if fid and fid in FONTS:
            self.note(font, FONTS[fid]["label"], "registry")
            return self._registry(page, fid)
        if fid and fid in BASE14:
            self.note(font, BASE14[fid][0], "base14")
            return BASE14[fid][1], fitz.Font(BASE14[fid][1])
        alias, fobj = self._embedded(page, font)
        if alias and fobj is not None:
            self.note(font, font, "embedded")
            return alias, fobj
        code = base14(font, flags)
        if not re.match(r"(helvetica|times|courier|arial)", strip_subset(font).lower()) and font != "helv":
            self.warnings.add(f"Font '{font}' is not embedded/loadable; used {code} instead.")
        self.note(font, code, "base14")
        return code, fitz.Font(code)

    def write(self, page: fitz.Page, e: dict[str, Any]) -> None:
        text = str(e.get("new_text", ""))
        if not text:
            return
        font = str(e.get("font", "helv"))
        flags = int(e.get("flags", 0))
        size = float(e.get("size", 12))
        c = int(e.get("color", 0))
        color = (((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255)
        x, y = float(e["origin"][0]), float(e["origin"][1])
        fid = e.get("font_id")

        runs = split_runs(text)
        base_alias, base_font = self._latin_base(page, font, flags, fid)
        for run, is_bn in runs:
            if is_bn:
                x += self._bengali(page, x, y, run, size, color, fid, flags, font)
                continue
            alias, fobj = base_alias, base_font
            missing = [ch for ch in run if not ch.isspace() and not fobj.has_glyph(ord(ch))]
            if missing:
                code = base14(font, flags)
                alias, fobj = code, fitz.Font(code)
                self.warnings.add(
                    f"Font '{font}' lacks glyphs for {''.join(sorted(set(missing)))!r}; used {code} for those edits."
                )
                self.note(font, code, "fallback")
            page.insert_text(fitz.Point(x, y), run, fontname=alias, fontsize=size, color=color)
            x += fobj.text_length(run, fontsize=size)

    def _bengali(self, page, x, y, run, size, color, fid, flags, font) -> float:
        bid = self._bengali_id(fid, flags)
        if not bid:
            self.warnings.add("No Bengali font installed on the server; Bengali text may show as empty boxes.")
            alias, fobj = ("helv", fitz.Font("helv"))
            page.insert_text(fitz.Point(x, y), run, fontname=alias, fontsize=size, color=color)
            return fobj.text_length(run, fontsize=size)
        path = FONTS[bid]["path"]
        label = FONTS[bid]["label"]
        if HAVE_SHAPING:
            try:
                sf = _SHAPERS.get(path) or _SHAPERS.setdefault(path, ShapedFont(path))
                w = sf.draw(page, x, y, run, size, color)
                self.note(font, label, "merged+shaped" if font != "helv" else "registry+shaped")
                return w
            except Exception as exc:
                self.warnings.add(f"Bengali shaping failed ({exc}); used unshaped text.")
        else:
            self.warnings.add("uharfbuzz/fonttools not installed: Bengali conjuncts and vowel signs may render incorrectly.")
        alias, fobj = self._registry(page, bid)
        page.insert_text(fitz.Point(x, y), run, fontname=alias, fontsize=size, color=color)
        self.note(font, label, "merged")
        return fobj.text_length(run, fontsize=size)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
async def read_pdf(file: UploadFile) -> bytes:
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (limit 50MB).")
    if b"%PDF" not in data[:1024]:
        raise HTTPException(400, "Not a valid PDF file.")
    return data


def open_pdf(data: bytes) -> fitz.Document:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise HTTPException(400, f"Cannot open PDF: {exc}") from exc
    if doc.needs_pass:
        doc.close()
        raise HTTPException(400, "Password-protected PDFs are not supported.")
    return doc


def pdf_response(out: bytes, name: str) -> Response:
    return Response(
        content=out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


# ----------------------------------------------------------------------------
# Info endpoints
# ----------------------------------------------------------------------------
@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok" if has_bengali_font() else "degraded",
        "fonts_loaded": len(FONTS),
        "libreoffice_available": bool(shutil.which("soffice")),
        "pymupdf": fitz.VersionBind,
    }


@app.get("/api/fonts")
def fonts() -> dict[str, Any]:
    return {"fonts": font_list()}


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "max_file_size": MAX_BYTES,
        "supported_fonts": font_list(),
        "features": {
            "true_text_edit": True,
            "whiteout_wipe": True,
            "protect": True,
            "unlock": True,
            "compress": True,
            "compress_images": hasattr(fitz.Document, "rewrite_images"),
            "bangla_fonts": has_bengali_font(),
            "bangla_shaping": HAVE_SHAPING and has_bengali_font(),
            "pdf_to_docx": _has("pdf2docx"),
            "pdf_to_xlsx": _has("pdfplumber") and _has("openpyxl"),
            "office_to_pdf": bool(shutil.which("soffice")),
        },
    }


# ----------------------------------------------------------------------------
# Extract
# ----------------------------------------------------------------------------
def extract_text_spans(doc: fitz.Document) -> dict[str, Any]:
    result: dict[str, Any] = {"page_count": doc.page_count, "pages": []}
    for page_num in range(doc.page_count):
        page = doc[page_num]
        page_data: dict[str, Any] = {
            "page": page_num,
            "width": page.rect.width,
            "height": page.rect.height,
            "spans": [],
        }
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    page_data["spans"].append(
                        {
                            "id": f"p{page_num}_s{len(page_data['spans'])}",
                            "text": span["text"],
                            "font": span["font"],
                            "size": round(span["size"], 2),
                            "color": span["color"],
                            "flags": span["flags"],
                            "bbox": list(span["bbox"]),
                            "origin": list(span["origin"]),
                        }
                    )
        result["pages"].append(page_data)
    return result


@app.post("/api/pdf/extract")
@limiter.limit("60/minute")
async def extract(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    data = await read_pdf(file)
    doc = open_pdf(data)
    try:
        return extract_text_spans(doc)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Extraction failed: {exc}") from exc
    finally:
        doc.close()


# ----------------------------------------------------------------------------
# Edit
# ----------------------------------------------------------------------------
def replace_text_in_pdf(doc: fitz.Document, edits: list[dict[str, Any]]) -> FontManager:
    by_page: dict[int, list[dict[str, Any]]] = {}
    for e in edits:
        by_page.setdefault(int(e["page"]), []).append(e)

    fm = FontManager(doc)
    for pno, items in sorted(by_page.items()):
        if not 0 <= pno < doc.page_count:
            continue
        page = doc[pno]

        # Step 1: truly delete original text (transparent redaction, no fill).
        redacted = False
        for e in items:
            if e.get("is_new") or e.get("wipe") or not e.get("bbox"):
                continue
            x0, y0, x1, y1 = e["bbox"]
            h = y1 - y0
            page.add_redact_annot(fitz.Rect(x0, y0 + h * 0.1, x1, y1 - h * 0.1), fill=False)
            redacted = True
        if redacted:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # Whiteout / image delete: remove text AND blank image pixels inside the area.
        wiped = False
        for e in items:
            if e.get("wipe") and e.get("bbox"):
                page.add_redact_annot(fitz.Rect(e["bbox"]), fill=(1, 1, 1))
                wiped = True
        if wiped:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

        # Step 2: write new text (original font first, Bengali merged from Noto).
        for e in items:
            fm.write(page, e)
    return fm


@app.post("/api/pdf/edit")
@limiter.limit("30/minute")
async def edit(request: Request, file: UploadFile = File(...), edits: str = Form(...)) -> Response:
    data = await read_pdf(file)
    try:
        items = json.loads(edits)
        if not isinstance(items, list):
            raise ValueError("edits must be a JSON array")
    except ValueError as exc:
        raise HTTPException(400, f"Invalid edits JSON: {exc}") from exc

    doc = open_pdf(data)
    try:
        fm = replace_text_in_pdf(doc, items)
        out = doc.tobytes(garbage=4, deflate=True)
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(400, f"Malformed edit: {exc!r}") from exc
    except Exception as exc:
        raise HTTPException(500, f"Edit failed: {exc}") from exc
    finally:
        doc.close()

    return Response(
        content=out,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="edited.pdf"',
            "X-Font-Warnings": json.dumps(sorted(fm.warnings)[:20]),
            "X-Fonts-Used": json.dumps(list(fm.used.values())[:30]),
        },
    )


# ----------------------------------------------------------------------------
# Protect / Unlock / Compress
# ----------------------------------------------------------------------------
@app.post("/api/pdf/protect")
@limiter.limit("30/minute")
async def protect(request: Request, file: UploadFile = File(...), password: str = Form(...)) -> Response:
    if not password:
        raise HTTPException(400, "Password required.")
    doc = open_pdf(await read_pdf(file))
    try:
        out = doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=password,
            permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY | fitz.PDF_PERM_ACCESSIBILITY,
            garbage=3,
            deflate=True,
        )
    except Exception as exc:
        raise HTTPException(500, f"Protect failed: {exc}") from exc
    finally:
        doc.close()
    return pdf_response(out, "protected.pdf")


@app.post("/api/pdf/unlock")
@limiter.limit("30/minute")
async def unlock(request: Request, file: UploadFile = File(...), password: str = Form("")) -> Response:
    data = await read_pdf(file)
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise HTTPException(400, f"Cannot open PDF: {exc}") from exc
    try:
        if doc.needs_pass and not doc.authenticate(password):
            raise HTTPException(400, "Wrong password.")
        out = doc.tobytes(encryption=fitz.PDF_ENCRYPT_NONE, garbage=3, deflate=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Unlock failed: {exc}") from exc
    finally:
        doc.close()
    return pdf_response(out, "unlocked.pdf")


@app.post("/api/pdf/compress")
@limiter.limit("20/minute")
async def compress(
    request: Request, file: UploadFile = File(...), quality: int = Form(60), dpi: int = Form(110)
) -> Response:
    doc = open_pdf(await read_pdf(file))
    try:
        if hasattr(doc, "rewrite_images"):  # recompresses images, keeps text selectable
            doc.rewrite_images(dpi_threshold=dpi + 30, dpi_target=dpi, quality=max(10, min(95, quality)))
        out = doc.tobytes(garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, clean=True)
    except Exception as exc:
        raise HTTPException(500, f"Compress failed: {exc}") from exc
    finally:
        doc.close()
    return pdf_response(out, "compressed.pdf")


# ----------------------------------------------------------------------------
# Converters
# ----------------------------------------------------------------------------
@app.post("/api/convert/pdf-to-docx")
@limiter.limit("10/minute")
async def pdf_to_docx(request: Request, file: UploadFile = File(...)) -> Response:
    data = await read_pdf(file)
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "in.pdf"), os.path.join(tmp, "out.docx")
        with open(src, "wb") as fh:
            fh.write(data)
        try:
            from pdf2docx import Converter

            cv = Converter(src)
            cv.convert(out)
            cv.close()
        except Exception as exc:
            raise HTTPException(500, f"Conversion failed: {exc}") from exc
        with open(out, "rb") as fh:
            return Response(fh.read(), media_type=DOCX_MIME, headers={"Content-Disposition": 'attachment; filename="converted.docx"'})


@app.post("/api/convert/pdf-to-xlsx")
@limiter.limit("10/minute")
async def pdf_to_xlsx(request: Request, file: UploadFile = File(...)) -> Response:
    data = await read_pdf(file)
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "in.pdf"), os.path.join(tmp, "out.xlsx")
        with open(src, "wb") as fh:
            fh.write(data)
        try:
            import pdfplumber
            from openpyxl import Workbook

            wb = Workbook()
            wb.remove(wb.active)
            with pdfplumber.open(src) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    ws = wb.create_sheet(f"Page {i}")
                    tables = page.extract_tables()
                    if tables:
                        for t in tables:
                            for row in t:
                                ws.append([c or "" for c in row])
                            ws.append([])
                    else:
                        for line in (page.extract_text() or "").splitlines():
                            ws.append([line])
            wb.save(out)
        except Exception as exc:
            raise HTTPException(500, f"Conversion failed: {exc}") from exc
        with open(out, "rb") as fh:
            return Response(fh.read(), media_type=XLSX_MIME, headers={"Content-Disposition": 'attachment; filename="converted.xlsx"'})


@app.post("/api/convert/office-to-pdf")
@limiter.limit("10/minute")
async def office_to_pdf(request: Request, file: UploadFile = File(...)) -> Response:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx"}:
        raise HTTPException(400, "Unsupported file type.")
    if not shutil.which("soffice"):
        raise HTTPException(501, "LibreOffice (soffice) is not installed on this server. Use the Dockerfile.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (limit 50MB).")
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in" + ext)
        with open(src, "wb") as fh:
            fh.write(data)
        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, src],
                check=True, timeout=180, env={**os.environ, "HOME": tmp}, capture_output=True,
            )
        except Exception as exc:
            raise HTTPException(500, f"Conversion failed: {exc}") from exc
        out = os.path.join(tmp, "in.pdf")
        if not os.path.exists(out):
            raise HTTPException(500, "Conversion produced no output.")
        with open(out, "rb") as fh:
            return pdf_response(fh.read(), "converted.pdf")


# Run: uvicorn main:app --reload --port 8000   (from the backend/ folder)
