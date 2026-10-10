/* ============================================================
   SAI ORBIT — Main Script
   ============================================================ */

/* ------------------------------------------------------------
   🔧 TOOLS CONFIG
   ------------------------------------------------------------
   নতুন tool যোগ করতে চাইলে নিচের array-তে একটা object push করো।
   Example:
   {
     icon: '🖼️',
     title: 'Orbit Image Compressor',
     desc: 'Compress images without losing quality.',
     url: '/image-compressor',
     color: '#10b981'  // optional
   }
------------------------------------------------------------ */
const TOOLS = [
  {
    icon: '🎬',
    title: 'Orbit Video Downloader',
    desc: 'Download videos from your favorite platforms — fast, free, and watermark-free.',
    url: '/video-downloader',
  },
  {
    icon: '📄',
    title: 'Orbit PDF Editor',
    desc: 'Edit, merge, split, and convert PDFs right in your browser. No installs needed.',
    url: '/pdf-editor',
  },
  {
    icon: '🛒',
    title: 'Orbit Deals',
    desc: 'Handpicked Flipkart deals and offers, updated daily. Save more on every purchase.',
    url: '/deals',
  },
  // 👇 Future tools — just uncomment or add more
  // {
  //   icon: '🖼️',
  //   title: 'Orbit Image Tools',
  //   desc: 'Compress, resize, and convert images in one click.',
  //   url: '/image-tools',
  // },
  // {
  //   icon: '📝',
  //   title: 'Orbit Text Utils',
  //   desc: 'Word count, case convert, and text cleaning tools.',
  //   url: '/text-tools',
  // },
];

/* ------------------------------------------------------------
   RENDER TOOLS GRID
------------------------------------------------------------ */
function renderTools() {
  const grid = document.getElementById('toolsGrid');
  if (!grid) return;

  grid.innerHTML = TOOLS.map(tool => `
    <a href="${tool.url}" class="tool-card">
      <div class="tool-icon">${tool.icon}</div>
      <h3 class="tool-title">${tool.title}</h3>
      <p class="tool-desc">${tool.desc}</p>
      <span class="tool-link">Launch <span>→</span></span>
    </a>
  `).join('');
}

/* ------------------------------------------------------------
   MOBILE MENU
------------------------------------------------------------ */
function initMenu() {
  const menuToggle = document.getElementById('menuToggle');
  const nav = document.getElementById('nav');
  if (!menuToggle || !nav) return;

  menuToggle.addEventListener('click', () => {
    nav.classList.toggle('open');
    menuToggle.classList.toggle('open');
  });

  // Close menu when a link is clicked
  nav.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
      nav.classList.remove('open');
      menuToggle.classList.remove('open');
    });
  });
}

/* ------------------------------------------------------------
   THEME TOGGLE (persisted in localStorage)
------------------------------------------------------------ */
function initTheme() {
  const toggle = document.getElementById('themeToggle');
  const saved = localStorage.getItem('saiorbit-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  const initialTheme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', initialTheme);

  if (!toggle) return;
  toggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('saiorbit-theme', next);
  });
}

/* ------------------------------------------------------------
   BACK TO TOP
------------------------------------------------------------ */
function initBackToTop() {
  const btn = document.getElementById('backToTop');
  if (!btn) return;

  window.addEventListener('scroll', () => {
    if (window.scrollY > 400) btn.classList.add('visible');
    else btn.classList.remove('visible');
  });

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* ------------------------------------------------------------
   DYNAMIC YEAR IN FOOTER
------------------------------------------------------------ */
function initYear() {
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();
}

/* ------------------------------------------------------------
   SCROLL REVEAL (simple fade-in)
------------------------------------------------------------ */
function initScrollReveal() {
  const elements = document.querySelectorAll('.tool-card, .feature-card, .stat');
  if (!('IntersectionObserver' in window)) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  elements.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
  });
}

/* ------------------------------------------------------------
   INIT ALL
------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
  renderTools();
  initMenu();
  initTheme();
  initBackToTop();
  initYear();
  initScrollReveal();
});
