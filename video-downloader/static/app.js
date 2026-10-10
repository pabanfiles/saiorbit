/* =========================================================================
   ORBIT VIDEO — Frontend logic
   ✅ FIXED: Dedup formats + direct fast download
   ========================================================================= */

const API_BASE = 'https://sai-digital.onrender.com';
const API_INFO = API_BASE + '/api/info';
const API_DOWNLOAD = API_BASE + '/api/download-direct';
const FETCH_TIMEOUT_MS = 90000;
const DOWNLOAD_TIMEOUT_MS = 240000;

const $ = (id) => document.getElementById(id);

const urlInput = $('video-url-input');
const btnPaste = $('btn-paste');
const btnSubmit = $('btn-submit');
const platformChip = $('platform-chip');
const platformChipName = $('platform-chip-name');
const loadingState = $('loading-state');
const loadingText = $('loading-status-text');
const resultsSection = $('results-section');
const resultThumb = $('result-thumbnail');
const resultTitle = $('result-title');
const resultDuration = $('result-duration');
const resultPlatform = $('result-platform');
const resultAuthor = $('result-author');
const tabVideo = $('tab-video');
const tabAudio = $('tab-audio');
const videoGrid = $('video-formats-grid');
const audioGrid = $('audio-formats-grid');

let currentInfo = null;

// ---- Platform detect ----------------------------------------------------
const PLATFORM_MAP = [
    { name: 'Facebook',  re: /(facebook\.com|fb\.watch|fb\.com)/i, color: '#1877f2' },
    { name: 'Instagram', re: /(instagram\.com|instagr\.am)/i,      color: '#e4405f' },
    { name: 'TikTok',    re: /tiktok\.com/i,                      color: '#69c9d0' },
    { name: 'Twitter/X', re: /(twitter\.com|x\.com)/i,            color: '#ffffff' },
    { name: 'Pinterest', re: /(pinterest\.com|pin\.it)/i,         color: '#e60023' },
    { name: 'Reddit',    re: /(reddit\.com|redd\.it)/i,           color: '#ff4500' },
    { name: 'Vimeo',     re: /vimeo\.com/i,                       color: '#1ab7ea' },
    { name: 'Threads',   re: /(threads\.net|threads\.com)/i,      color: '#ffffff' },
];

function detectPlatform(url) {
    for (const p of PLATFORM_MAP) if (p.re.test(url)) return p;
    return null;
}

if (urlInput) {
    urlInput.addEventListener('input', () => {
        const url = urlInput.value.trim();
        if (!url || !platformChip) return;
        const p = detectPlatform(url);
        if (p) {
            platformChip.classList.add('active');
            platformChip.style.background = p.color + '22';
            platformChip.style.borderColor = p.color;
            platformChipName.textContent = p.name + ' detected';
        } else {
            platformChip.classList.remove('active');
            platformChipName.textContent = 'Unknown platform';
        }
    });
}

// ---- Paste button -------------------------------------------------------
if (btnPaste) {
    btnPaste.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            urlInput.value = text.trim();
            urlInput.dispatchEvent(new Event('input'));
        } catch {
            showToast('Paste Not Allowed', 'Please paste manually (Ctrl+V).', 'error');
        }
    });
}

// ---- Toast --------------------------------------------------------------
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-body">
          <div class="toast-title">${title}</div>
          <div class="toast-desc">${message}</div>
        </div>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4500);
}

function showLoading(text) {
    if (loadingState) {
        loadingState.style.display = 'flex';
        if (loadingText) loadingText.textContent = text;
    }
}
function hideLoading() {
    if (loadingState) loadingState.style.display = 'none';
}

// ---- Fetch with timeout -------------------------------------------------
async function fetchWithTimeout(url, options, timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } finally {
        clearTimeout(timer);
    }
}

// ---- Submit -------------------------------------------------------------
if (btnSubmit) {
    btnSubmit.addEventListener('click', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) {
            showToast('Missing URL', 'Please paste a video URL first.', 'error');
            return;
        }
        if (!detectPlatform(url)) {
            showToast('Unsupported Platform', 'This platform is not supported yet.', 'error');
            return;
        }

        btnSubmit.disabled = true;
        showLoading('Analyzing media...');
        if (resultsSection) resultsSection.style.display = 'none';

        try {
            const res = await fetchWithTimeout(API_INFO, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            }, FETCH_TIMEOUT_MS);

            let data;
            try {
                data = await res.json();
            } catch {
                throw new Error('Server returned invalid response. Try again.');
            }

            if (!res.ok) {
                throw new Error(data.detail || 'Could not fetch media info.');
            }

            currentInfo = { ...data, url };
            renderResults(data);

        } catch (err) {
            console.error('Fetch error:', err);
            let msg = 'Failed to fetch. ';
            if (err.name === 'AbortError') {
                msg = 'Server took too long. Please try again.';
            } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
                msg = 'Cannot reach server. Backend may be starting up — please wait 30s and retry.';
            } else {
                msg = err.message || 'Failed to fetch info.';
            }
            showToast('Error', msg, 'error');
        } finally {
            hideLoading();
            btnSubmit.disabled = false;
        }
    });
}

// ---- Render results -----------------------------------------------------
function renderResults(info) {
    if (!resultsSection) return;

    if (resultThumb) resultThumb.src = info.thumbnail || 'static/img/placeholder.svg';
    if (resultTitle) resultTitle.textContent = info.title || 'Untitled';
    if (resultAuthor) resultAuthor.textContent = info.uploader || 'Unknown';
    if (resultPlatform) {
        resultPlatform.textContent = info.platform || 'Media';
        const p = detectPlatform(info.webpage_url || '');
        if (p) {
            resultPlatform.style.background = p.color + '22';
            resultPlatform.style.borderColor = p.color;
            resultPlatform.style.color = p.color;
        }
    }
    if (resultDuration && info.duration) {
        resultDuration.textContent = formatDuration(info.duration);
    } else if (resultDuration) {
        resultDuration.style.display = 'none';
    }

    renderFormats(info.formats || [], info.media_type || 'video');

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function formatDuration(sec) {
    if (!sec || isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatBytes(bytes) {
    if (!bytes || isNaN(bytes) || bytes === 0) return 'Unknown size';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
    return `${bytes.toFixed(1)} ${units[i]}`;
}

// ---- Render formats -----------------------------------------------------
function renderFormats(formats, mediaType) {
    if (!videoGrid || !audioGrid) return;

    videoGrid.innerHTML = '';
    audioGrid.innerHTML = '';

    // Photo / Carousel
    if (mediaType === 'photo' || mediaType === 'carousel') {
        formats.forEach((f) => {
            videoGrid.appendChild(buildFormatCard(f, 'photo', f.format_id === 'photo' || f.format_id === 'carousel_0'));
        });
        tabVideo.textContent = mediaType === 'carousel' ? `Media (${formats.length})` : 'Photo';
        if (tabAudio) tabAudio.style.display = 'none';
        tabVideo.classList.add('active');
        videoGrid.style.display = 'grid';
        audioGrid.style.display = 'none';
        return;
    }

    // Reset tabs
    if (tabAudio) tabAudio.style.display = '';
    tabVideo.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="23 7 16 12 23 17 23 7"></polygon>
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
        </svg>
        Video (MP4)
    `;

    // ✅ FIX: Dedup by height (frontend safety)
    const seenHeights = new Set();
    const videos = [];

    for (const f of formats) {
        if (!f.has_video) continue;
        const h = f.height || 0;
        if (seenHeights.has(h)) continue;
        seenHeights.add(h);
        videos.push(f);
    }

    videos.sort((a, b) => (b.height || 0) - (a.height || 0));

    if (videos.length === 0) {
        videoGrid.innerHTML = '<div class="format-card">No video formats found</div>';
    } else {
        videos.slice(0, 8).forEach((f, i) => {
            videoGrid.appendChild(buildFormatCard(f, 'video', i === 0));
        });
    }

    // Audio tab
    const bestForAudio = videos[0] || formats[0];
    if (bestForAudio) audioGrid.appendChild(buildFormatCard(bestForAudio, 'audio', true));
    formats.filter(f => f.has_audio && !f.has_video).forEach((f) => {
        audioGrid.appendChild(buildFormatCard(f, 'audio', false));
    });

    tabVideo.classList.add('active');
    tabAudio.classList.remove('active');
    videoGrid.style.display = 'grid';
    audioGrid.style.display = 'none';
}

// ---- Build format card --------------------------------------------------
function buildFormatCard(fmt, type, recommended) {
    const card = document.createElement('div');
    card.className = 'format-card' + (recommended ? ' recommended' : '');

    let quality = fmt.quality || '';
    if (!quality) {
        if (fmt.height) quality = `${fmt.height}p`;
        else if (fmt.ext) quality = fmt.ext.toUpperCase();
        else quality = 'Standard';
    }
    quality = quality.replace(/dash\s*/gi, '').trim() || 'Standard';

    const size = formatBytes(fmt.filesize);

    const iconSvg = type === 'audio'
        ? '<path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>'
        : type === 'photo'
        ? '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline>'
        : '<polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>';

    let subtitle = '';
    if (type === 'audio') {
        subtitle = 'MP3 192kbps';
    } else if (type === 'photo') {
        subtitle = fmt.ext?.toUpperCase() || 'JPG';
    } else {
        const ext = (fmt.ext || 'mp4').toUpperCase();
        const sound = fmt.has_audio !== false ? ' · 🔊 Sound' : '';
        subtitle = `${ext}${sound}`;
    }

    card.innerHTML = `
        ${recommended ? '<div class="format-badge">Recommended</div>' : ''}
        <div class="format-title-group">
            <div class="format-quality">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    ${iconSvg}
                </svg>
                <span>${quality}</span>
            </div>
            <div class="format-sub">${subtitle}</div>
        </div>
        <div class="format-footer">
            <span class="format-size">${size}</span>
            <button class="btn-card-download" type="button">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Download
            </button>
        </div>
    `;

    card.querySelector('.btn-card-download').addEventListener('click', (e) => {
        e.stopPropagation();
        triggerDownload(fmt, type);
    });

    return card;
}

// ---- Trigger download ---------------------------------------------------
async function triggerDownload(fmt, type) {
    if (!currentInfo) return;

    // ✅ FAST: Progressive format → direct download (instant)
    if (fmt.is_progressive && fmt.direct_url) {
        showToast('Fast Download', 'Starting direct download...', 'info');

        const a = document.createElement('a');
        a.href = fmt.direct_url;
        const safeTitle = (currentInfo.title || 'video')
            .replace(/[^\w\s-]/g, '')
            .slice(0, 40)
            .trim() || 'video';
        a.download = `orbit-${safeTitle}.${fmt.ext || 'mp4'}`;
        a.target = '_blank';
        a.rel = 'noopener';
        document.body.appendChild(a);
        a.click();
        a.remove();

        return;
    }

    // Photo/Carousel direct
    if ((type === 'photo' || fmt.is_direct) && fmt.direct_url) {
        window.open(fmt.direct_url, '_blank', 'noopener');
        showToast('Opening Photo', 'Long-press → Save image', 'info');
        return;
    }

    // Backend download
    showLoading(
        type === 'audio'
            ? 'Preparing MP3... (may take 30-90s)'
            : 'Downloading video... (may take 30-120s)'
    );

    try {
        const res = await fetchWithTimeout(API_DOWNLOAD, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: currentInfo.url,
                format_id: fmt.format_id || 'best',
                type: type,
                direct_url: null,
            }),
        }, DOWNLOAD_TIMEOUT_MS);

        if (!res.ok) {
            let detail = 'Download failed.';
            try {
                const j = await res.json();
                detail = j.detail || detail;
            } catch { /* ignore */ }
            throw new Error(detail);
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const safeTitle = (currentInfo.title || 'video')
            .replace(/[^\w\s-]/g, '')
            .slice(0, 60)
            .trim() || 'video';

        const ext = type === 'audio' ? 'mp3' : (fmt.ext || 'mp4');
        a.download = `orbit-${safeTitle}.${ext}`;

        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        showToast('Download Started', 'Check your browser downloads.', 'success');
    } catch (err) {
        console.error('Download error:', err);
        if (err.name === 'AbortError') {
            showToast('Timeout', 'Server busy — please try again in a minute.', 'error');
        } else if (err.message.includes('Failed to fetch')) {
            showToast('Network Error', 'Cannot reach server. Retry in 30s.', 'error');
        } else {
            showToast('Download Failed', err.message || 'Try again later.', 'error');
        }
    } finally {
        hideLoading();
    }
}

// ---- Tab switching ------------------------------------------------------
if (tabVideo && tabAudio) {
    tabVideo.addEventListener('click', () => {
        tabVideo.classList.add('active');
        tabAudio.classList.remove('active');
        if (videoGrid) videoGrid.style.display = 'grid';
        if (audioGrid) audioGrid.style.display = 'none';
    });
    tabAudio.addEventListener('click', () => {
        tabAudio.classList.add('active');
        tabVideo.classList.remove('active');
        if (videoGrid) videoGrid.style.display = 'none';
        if (audioGrid) audioGrid.style.display = 'grid';
    });
}

// ---- Reveal on scroll ---------------------------------------------------
(function revealOnScroll() {
    const els = document.querySelectorAll('.reveal');
    if (!els.length) return;
    const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
            if (e.isIntersecting) {
                e.target.classList.add('visible');
                io.unobserve(e.target);
            }
        });
    }, { threshold: 0.1 });
    els.forEach((el) => io.observe(el));
})();
