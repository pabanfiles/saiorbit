/**
 * Sai Digital — Daily Auto-Update Widgets (v4.1)
 * Client-side rotation keeps the homepage feeling fresh without server cost.
 */

(function () {
  'use strict';

  const TRENDING_MESSAGES = [
    'Instagram Reels download in 1080p without watermark — try it now',
    'Best Quality MP4 downloads now start in under 1 second',
    'MP3 audio extraction at 320kbps is now live for all platforms',
    'TikTok videos without watermark — 100% clean downloads',
    'Facebook Reels supported with full original audio',
    'Twitter/X videos — full HD quality now available',
    'Zero storage on server — direct CDN streaming active',
    'Pinterest, Reddit, Vimeo, Threads — all supported',
    'Works on mobile without installing any app',
    'Fast • Free • No Watermark — that is the Sai Digital promise',
    'New: 300MB file size support for large videos',
    'Auto-cleanup every 60 seconds keeps downloads instant',
    'No ads, no popups, no redirects — pure downloader',
    'Blog updated with new guides every week',
    'All 8 platforms supported with single paste',
  ];

  const DAILY_TIPS = [
    'Tip: Paste the link, tap Fetch, then pick Best Quality for the fastest download.',
    'Tip: For Instagram Reels, always copy the permanent Reel URL — not the temporary story link.',
    'Tip: MP3 320 kbps gives studio-quality audio — perfect for offline music.',
    'Tip: If a video is over 300MB, choose 720p instead of Best for a smaller file.',
    'Tip: Facebook videos must be Public (globe icon) — private ones cannot be fetched.',
    'Tip: TikTok downloads are watermark-free — ready for cross-platform re-editing.',
    'Tip: On iPhone, tap Share → Save Video to move downloads into your Photos app.',
    'Tip: All downloads are processed directly from CDN — no server storage, maximum speed.',
    'Tip: Twitter/X videos retain full original audio quality in our MP4 output.',
    'Tip: Use our Blog guides to master each platform — updated weekly.',
    'Tip: Mobile users — the site is fully responsive and works in any browser.',
    'Tip: Rate limits protect the service — 5 downloads per minute per visitor.',
    'Tip: No login, no signup, no cookies required — just paste and download.',
    'Tip: Every link is validated for safety before processing — zero malware risk.',
    'Tip: Best Quality option uses direct CDN streaming — download starts instantly.',
    'Tip: Audio extraction uses professional FFmpeg pipelines for pristine output.',
    'Tip: Clean, ad-free interface — no deceptive "Download" ads.',
    'Tip: Works in Chrome, Safari, Firefox, Edge — any modern browser.',
    'Tip: Bookmark Sai Digital for one-tap access on mobile.',
    'Tip: All formats are MP4 (video) or MP3 (audio) — universally compatible.',
  ];

  function pickByDay(array, offset = 0) {
    const day = Math.floor(Date.now() / 86400000);
    return array[(day + offset) % array.length];
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function initTrendingBanner() {
    const banner = document.getElementById('trending-banner');
    if (!banner) return;
    const textEl = banner.querySelector('.trending-text');
    if (!textEl) return;

    textEl.textContent = pickByDay(TRENDING_MESSAGES, 0);

    let idx = Math.floor(Date.now() / 86400000) % TRENDING_MESSAGES.length;
    setInterval(() => {
      textEl.classList.add('switching');
      setTimeout(() => {
        idx = (idx + 1) % TRENDING_MESSAGES.length;
        textEl.textContent = TRENDING_MESSAGES[idx];
        textEl.classList.remove('switching');
      }, 500);
    }, 6000);
  }

  function initDailyTip() {
    const tip = document.getElementById('daily-tip');
    if (!tip) return;
    const textEl = tip.querySelector('.daily-tip-text');
    if (!textEl) return;

    textEl.textContent = pickByDay(DAILY_TIPS, 7);

    let idx = Math.floor(Date.now() / 86400000) % DAILY_TIPS.length;
    setInterval(() => {
      textEl.classList.add('switching');
      setTimeout(() => {
        idx = (idx + 1) % DAILY_TIPS.length;
        textEl.textContent = DAILY_TIPS[idx];
        textEl.classList.remove('switching');
      }, 500);
    }, 12000);
  }

  function initFreshBadges() {
    const cards = document.querySelectorAll('[data-post-date]');
    const now = Date.now();
    const weekMs = 7 * 24 * 60 * 60 * 1000;

    cards.forEach((card) => {
      const raw = card.getAttribute('data-post-date');
      if (!raw) return;
      const ts = Date.parse(raw);
      if (!isNaN(ts) && (now - ts) < weekMs) {
        if (!card.querySelector('.fresh-badge')) {
          const badge = document.createElement('span');
          badge.className = 'fresh-badge';
          badge.textContent = '✨ New';
          const meta = card.querySelector('.blog-card-meta');
          if (meta) meta.prepend(badge);
          else card.prepend(badge);
        }
      }
    });
  }

  function initLiveIndicator() {
    const el = document.getElementById('live-indicator');
    if (!el) return;
    const timeEl = el.querySelector('.live-time');
    if (!timeEl) return;

    function tick() {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, '0');
      const mm = String(now.getMinutes()).padStart(2, '0');
      timeEl.textContent = `${hh}:${mm}`;
    }
    tick();
    setInterval(tick, 30000);
  }

  function initReveal() {
    const els = document.querySelectorAll('.reveal');
    if (!('IntersectionObserver' in window)) {
      els.forEach((el) => el.classList.add('visible'));
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => obs.observe(el));
  }

  function boot() {
    initTrendingBanner();
    initDailyTip();
    initFreshBadges();
    initLiveIndicator();
    initReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
