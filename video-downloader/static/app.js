/* =========================================================================
   SAI DIGITAL — Frontend download logic (memory-safe / queue-aware)
   ========================================================================= */

const API_INFO = '/api/info';
const API_DOWNLOAD = '/api/download-direct';
const FETCH_TIMEOUT_MS = 180000;   // 3 min (queue + download)
const DOWNLOAD_TIMEOUT_MS = 240000; // 4 min

// ---- DOM refs (with safe lookups) ---------------------------------------
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
    for (const p of PLATFORM_MAP) {
        if (p.re.test(url)) return p;
    }
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

// ---- Loading state ------------------------------------------------------
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

// ---- Submit — Fetch video info -----------------------------------------
if (btnSubmit) {
    btnSubmit.addEventListener('click', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) {
            showToast('Missing URL', 'Please paste a video URL first.', 'error');
            return;
        }
        if (!detectPlatform(url)) {
            showToast('Unsupported Platform', 'This platform is not supported.', 'error');
            return;
        }

        btnSubmit.disabled = true;
        showLoading('Analyzing video stream...');
        if (resultsSection) resultsSection.style.display = 'none';

        try {
            const res = await fetchWithTimeout(API_INFO, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            }, FETCH_TIMEOUT_MS);

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Could not fetch video info.');
            }

            currentInfo = { ...data, url };
            renderResults(data);

        } catch (err) {
            if (err.name === 'AbortError') {
                showToast('Timeout', 'Server took too long. Please try again.', 'error');
            } else {
                showToast('Error', err.message || 'Failed to fetch info.', 'error');
            }
        } finally {
            hideLoading();
            btnSubmit.disabled = false;
        }
    });
}

// ---- Render results -----------------------------------------------------
function renderResults(info) {
    if (!resultsSection) return;

    if (resultThumb) resultThumb.src = info.thumbnail || '/static/img/placeholder.jpg';
    if (resultTitle) resultTitle.textContent = info.title || 'Untitled';
    if (resultAuthor) resultAuthor.textContent = info.uploader || 'Unknown';
    if (resultPlatform) {
        resultPlatform.textContent = info.platform || 'Video';
        const p = detectPlatform(info.webpage_url || '');
        if (p) {
            resultPlatform.style.background = p.color + '22';
            resultPlatform.style.borderColor = p.color;
            resultPlatform.style.color = p.color;
        }
    }
    if (resultDuration && info.duration) {
        resultDuration.textContent = formatDuration(info.duration);
    }

    renderFormats(info.formats || []);

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
    if (!bytes || isNaN(bytes)) return 'Unknown size';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
    }
    return `${bytes.toFixed(1)} ${units[i]}`;
}

// ---- Render formats -----------------------------------------------------
function renderFormats(formats) {
    if (!videoGrid || !audioGrid) return;

    const videos = formats.filter(f => f.has_video);
    const audios = formats.filter(f => f.has_audio && !f.has_video);
    const audioFromVideo = formats.filter(f => f.has_video); // for mp3 extraction

    videoGrid.innerHTML = '';
    audioGrid.innerHTML = '';

    // Video formats
    if (videos.length === 0) {
        videoGrid.innerHTML = '<div class="format-card">No video formats found</div>';
    } else {
        videos.sort((a, b) => (b.filesize || 0) - (a.filesize || 0));
        videos.slice(0, 8).forEach((f, i) => {
            videoGrid.appendChild(buildFormatCard(f, 'video', i === 0));
        });
    }

    // Audio formats (always offer generic MP3 from best video)
    const bestForAudio = audioFromVideo[0] || formats[0];
    if (bestForAudio) {
        audioGrid.appendChild(buildFormatCard(bestForAudio, 'audio', true));
    }
    audios.forEach((f) => {
        audioGrid.appendChild(buildFormatCard(f, 'audio', false));
    });

    // Tabs default: video
    if (tabVideo && tabAudio) {
        tabVideo.classList.add('active');
        tabAudio.classList.remove('active');
        videoGrid.style.display = 'grid';
        audioGrid.style.display = 'none';
    }
}

function buildFormatCard(fmt, type, recommended) {
    const card = document.createElement('div');
    card.className = 'format-card' + (recommended ? ' recommended' : '');

    const quality = fmt.quality || fmt.ext || 'Standard';
    const size = formatBytes(fmt.filesize);

    card.innerHTML = `
        ${recommended ? '<div class="format-badge">Recommended</div>' : ''}
        <div class="format-title-group">
            <div class="format-quality">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    ${type === 'audio'
                        ? '<path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>'
                        : '<polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>'}
                </svg>
                <span>${quality}</span>
            </div>
            <div class="format-sub">${type === 'audio' ? 'MP3 192kbps' : fmt.ext?.toUpperCase() || 'MP4'}</div>
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

// ---- Download trigger ---------------------------------------------------
async function triggerDownload(fmt, type) {
    if (!currentInfo) return;

    showLoading(
        type === 'audio'
            ? 'Preparing MP3... (may take 30-90s if queue busy)'
            : 'Starting download... (may wait up to 1 min if queue busy)'
    );

    try {
        const res = await fetchWithTimeout(API_DOWNLOAD, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: currentInfo.url,
                format_id: fmt.format_id || 'best',
                type: type,
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

        const safeTitle = (currentInfo.title || 'video').replace(/[^\w\s-]/g, '').slice(0, 60).trim();
        a.download = type === 'audio'
            ? `sai-digital-${safeTitle}.mp3`
            : `sai-digital-${safeTitle}.mp4`;

        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        showToast('Download Started', 'Check your browser downloads.', 'success');

    } catch (err) {
        if (err.name === 'AbortError') {
            showToast('Timeout', 'Server busy — please try again in a minute.', 'error');
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
