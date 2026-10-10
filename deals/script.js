// SaiDeals - Affiliate Deal Aggregator
// Sheet ID: 17MRsUL3xh4zbuLv3HOQwm3CNCLXC-3hS-7jqaSW6_44
const SHEET_URL = 'https://opensheet.elk.sh/17MRsUL3xh4zbuLv3HOQwm3CNCLXC-3hS-7jqaSW6_44/1';
const $ = (s, r = document) => r.querySelector(s);
const ls = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
const S = { all: [], view: [], page: 1, per: 20, cat: 'all', q: '', wish: ls('sd_wish', []), seen: ls('sd_seen', {}), recent: ls('sd_recent', []), list: false };
const inr = n => '₹' + Number(n).toLocaleString('en-IN');
const img = p => (p.image || '').startsWith('http') ? p.image : `https://images.unsplash.com/${p.image}?w=500&q=70&auto=format&fit=crop`;
const off = p => { const orig = +(p.original || p.originalPrice || 0); if (!orig || !p.price || orig <= p.price) return 0; return Math.round((1 - p.price / orig) * 100); };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

async function load() {
  $('#grid').innerHTML = '<div class="sk"></div>'.repeat(8);
  let data;
  try {
    if (SHEET_URL.includes('YOUR_SHEET_ID')) throw 0;
    const r = await fetch(SHEET_URL); if (!r.ok) throw 0;
    data = (await r.json()).map((p, i) => ({ 
      ...p, 
      id: +p.id || i + 1, 
      price: +p.price || 0, 
      original: +(p.originalPrice || p.original || 0), 
      rating: +p.rating || 0, 
      reviews: +p.reviews || 0 
    }));
  } catch { data = await (await fetch('data.json')).json(); }
  const extra = ls('sd_products', []);
  S.all = [...extra, ...data];
  render(); trending(); recs(); notifs();
}

function card(p) {
  const on = S.wish.includes(p.id);
  const discount = off(p);
  const orig = +(p.original || p.originalPrice || 0);
  return `<article class="card"><div class="im"><img src="${img(p)}" alt="${esc(p.name)}" loading="lazy" onerror="this.style.display='none'"><span class="disc">${discount}% OFF</span><button class="heart ${on ? 'on' : ''}" data-h="${p.id}" aria-label="Save to wishlist">♥</button><span class="store ${p.store}">${p.store}</span><div class="qv">👁 Quick View</div></div>
<div class="bd"><h3>${esc(p.name)}</h3><div class="rt"><b>⭐ ${p.rating}</b>(${p.reviews.toLocaleString('en-IN')})</div>
<div class="pr"><strong>${inr(p.price)}</strong>${orig ? `<s>${inr(orig)}</s>` : ''}${discount ? `<em>${discount}% off</em>` : ''}</div><div class="dl">🚚 Free Delivery</div>
<a class="buy" data-b="${p.id}" href="${p.link}" target="_blank" rel="sponsored noopener">Buy Now</a></div></article>`;
}

function filter() {
  const f = id => $(id).value; let r = S.all.filter(p => {
    if (S.cat !== 'all' && p.category !== S.cat) return false;
    if (f('#fs') !== 'all' && p.store !== f('#fs')) return false;
    if (f('#fp') !== 'all' && p.price > +f('#fp')) return false;
    if (f('#fr') !== 'all' && p.rating < +f('#fr')) return false;
    return !S.q || p.name.toLowerCase().includes(S.q.toLowerCase());
  });
  const s = f('#so');
  r.sort({ pop: (a, b) => b.reviews - a.reviews, lo: (a, b) => a.price - b.price, hi: (a, b) => b.price - a.price, rate: (a, b) => b.rating - a.rating, new: (a, b) => b.id - a.id }[s]);
  return r;
}
function render(reset = true) {
  if (reset) S.page = 1; S.view = filter();
  const g = $('#grid'); g.className = 'grid' + (S.list ? ' list' : '');
  g.innerHTML = S.view.length ? S.view.slice(0, S.page * S.per).map(card).join('') : '<div class="none">😕 No deals found. Try another search or filter.</div>';
  $('#count').textContent = `${S.view.length} deals found`;
  $('#more').style.display = S.view.length > S.page * S.per ? 'block' : 'none';
  $('#wc').textContent = S.wish.length;
}
function trending() { $('#trend').innerHTML = [...S.all].sort((a, b) => b.reviews - a.reviews).slice(0, 6).map(card).join(''); }
function recs() {
  const top = Object.entries(S.seen).sort((a, b) => b[1] - a[1])[0]?.[0];
  const list = (top ? S.all.filter(p => p.category === top) : [...S.all].sort((a, b) => b.rating - a.rating)).slice(0, 5);
  $('#recs').innerHTML = list.map(card).join('');
}
function notifs() { $('#np').innerHTML = S.all.slice(0, 4).map(p => `<p>🆕 ${esc(p.name.slice(0, 34))}… now ${inr(p.price)}</p>`).join(''); $('#nc').textContent = Math.min(4, S.all.length); }

document.addEventListener('click', e => {
  const h = e.target.closest('[data-h]');
  if (h) { const id = +h.dataset.h; S.wish = S.wish.includes(id) ? S.wish.filter(x => x !== id) : [...S.wish, id]; save('sd_wish', S.wish); render(false); trending(); recs(); }
  const b = e.target.closest('[data-b]');
  if (b) {
    const p = S.all.find(x => x.id == b.dataset.b); S.seen[p.category] = (S.seen[p.category] || 0) + 1; save('sd_seen', S.seen);
    const c = ls('sd_clicks', 0) + 1; save('sd_clicks', c);
  }
  const r = e.target.closest('.btn,.buy');
  if (r) { const d = document.createElement('span'), k = r.getBoundingClientRect(), z = Math.max(k.width, k.height); d.className = 'rip'; d.style.cssText = `width:${z}px;height:${z}px;left:${e.clientX - k.left - z / 2}px;top:${e.clientY - k.top - z / 2}px`; r.append(d); setTimeout(() => d.remove(), 600); }
});

let t; const si = $('#q'), ac = $('#ac');
si.addEventListener('input', () => {
  $('#qx').style.display = si.value ? 'block' : 'none'; clearTimeout(t);
  t = setTimeout(() => {
    const v = si.value.trim(); if (!v) { ac.style.display = 'none'; return; }
    const m = S.all.filter(p => p.name.toLowerCase().includes(v.toLowerCase())).slice(0, 5);
    const hl = n => n.replace(new RegExp('(' + v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig'), '<mark>$1</mark>');
    ac.innerHTML = m.map(p => `<div>${hl(esc(p.name))}</div>`).join('') || '<div>No matches</div>'; ac.style.display = 'block';
  }, 300);
});
si.addEventListener('focus', () => { if (!si.value && S.recent.length) { ac.innerHTML = S.recent.map(x => `<div>🕘 ${esc(x)}</div>`).join(''); ac.style.display = 'block'; } });
ac.addEventListener('click', e => { if (e.target.closest('div')) { si.value = e.target.textContent.replace('🕘 ', ''); go(); } });
si.addEventListener('keydown', e => e.key === 'Enter' && go());
$('#qx').onclick = () => { si.value = ''; S.q = ''; $('#qx').style.display = 'none'; ac.style.display = 'none'; render(); };
function go() { S.q = si.value.trim(); ac.style.display = 'none'; if (S.q) { S.recent = [S.q, ...S.recent.filter(x => x !== S.q)].slice(0, 5); save('sd_recent', S.recent); } render(); $('#deals').scrollIntoView(); }
document.addEventListener('click', e => { if (!e.target.closest('.search')) ac.style.display = 'none'; });

['#fs', '#fp', '#fr', '#so'].forEach(s => $(s).onchange = () => render());
document.querySelectorAll('.cats button').forEach(b => b.onclick = () => { S.cat = b.dataset.c; document.querySelectorAll('.cats button').forEach(x => x.classList.toggle('on', x === b)); render(); });
document.querySelectorAll('.vt button').forEach(b => b.onclick = () => { S.list = b.dataset.v === 'l'; document.querySelectorAll('.vt button').forEach(x => x.classList.toggle('on', x === b)); render(false); });
$('#more').onclick = () => { S.page++; render(false); };
$('#bell').onclick = () => { const p = $('#np'); p.style.display = p.style.display === 'block' ? 'none' : 'block'; $('#nc').style.display = 'none'; };
const dr = $('#drawer'), sc = $('#scrim'), tg = o => { dr.classList.toggle('open', o); sc.style.display = o ? 'block' : 'none'; };
$('#burger').onclick = () => tg(true); sc.onclick = () => tg(false); dr.addEventListener('click', e => e.target.closest('a,.xd') && tg(false));
$('#wl').onclick = () => { S.q = ''; const w = S.all.filter(p => S.wish.includes(p.id)); $('#grid').className = 'grid'; $('#grid').innerHTML = w.length ? w.map(card).join('') : '<div class="none">💔 Your wishlist is empty. Tap ♥ on any deal.</div>'; $('#count').textContent = `${w.length} saved`; $('#more').style.display = 'none'; $('#deals').scrollIntoView(); };
$('#news').onsubmit = e => { e.preventDefault(); e.target.innerHTML = '<b>✅ Subscribed! Daily deals are on the way.</b>'; };

let end = Date.now() + (2 * 3600 + 45 * 60 + 30) * 1000;
setInterval(() => { let s = Math.max(0, Math.floor((end - Date.now()) / 1000)); if (!s) end = Date.now() + 3 * 3600e3; $('#timer').textContent = [s / 3600, s % 3600 / 60, s % 60].map(n => String(Math.floor(n)).padStart(2, '0')).join(':'); }, 1000);

addEventListener('scroll', () => $('#top').classList.toggle('show', scrollY > 400), { passive: true });
$('#top').onclick = () => scrollTo({ top: 0, behavior: 'smooth' });
if (ls('sd_cookie', false)) $('#cookie').remove(); else $('#ck').onclick = () => { save('sd_cookie', true); $('#cookie').remove(); };

(function(){const s=ls('sd_settings',null);if(!s)return;
 if(s.name){document.title=s.name+' – '+(s.tagline||'');document.querySelectorAll('.logo b,.fg b').forEach(e=>e.textContent=s.name);}
 if(s.tagline)document.querySelectorAll('.logo small').forEach(e=>e.textContent=s.tagline+' ⭐');
 [['bar','#bar'],['flash','#flash'],['recs','#recsec'],['recs','#recs']].forEach(([k,id])=>{if(s[k]===false)$(id).style.display='none';});})();
load();
