// ===== CHANGE THE DEFAULT LOGIN HERE =====
const DEFAULT_USER = 'admin';
const DEFAULT_PASS = 'saideals2026';
// (A password changed in Settings is saved in this browser and overrides DEFAULT_PASS.)
// NOTE: this login only hides the page. It runs in the browser, so it is not real security.
// ==========================================
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const rd = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const wr = (k, v) => localStorage.setItem(k, JSON.stringify(v));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const SESSION = 'sd_admin_session', P = () => rd('sd_products', []), pass = () => rd('sd_admin_pw', DEFAULT_PASS);
const authed = () => localStorage.getItem(SESSION) === '1' || sessionStorage.getItem(SESSION) === '1';
const inr = n => '₹' + Number(n || 0).toLocaleString('en-IN');
let editId = null;

function toast(m, e) { const t = document.createElement('div'); t.className = 'toast' + (e ? ' e' : ''); t.textContent = m; $('#toasts').append(t); setTimeout(() => t.remove(), 3200); }
function confirmBox(msg) { return new Promise(res => { $('#ct').textContent = msg; $('#cm').hidden = false; const d = v => { $('#cm').hidden = true; res(v); }; $('#cy').onclick = () => d(true); $('#cn').onclick = () => d(false); }); }

// ---- Login wall ----
function gate() { const ok = authed(); $('#login').hidden = ok; $('#app').hidden = !ok; if (ok) init(); }
$('#lf').onsubmit = e => {
  e.preventDefault(); const f = e.target;
  if (f.u.value.trim() === DEFAULT_USER && f.p.value === pass()) { (f.r.checked ? localStorage : sessionStorage).setItem(SESSION, '1'); f.reset(); $('#le').textContent = ''; gate(); }
  else $('#le').textContent = 'Wrong username or password.';
};
function logout() { localStorage.removeItem(SESSION); sessionStorage.removeItem(SESSION); gate(); }

// ---- Navigation ----
function go(v) {
  if (v === 'logout') return logout();
  $$('.view').forEach(x => x.classList.toggle('on', x.id === 'v-' + v));
  $$('#side nav button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  side(false); if (v === 'dash') stats(); if (v === 'products') table(); scrollTo(0, 0);
}
const side = o => { $('#side').classList.toggle('open', o); $('#scrim').classList.toggle('on', o); };
$$('#side nav button').forEach(b => b.onclick = () => go(b.dataset.v));
$('#menu').onclick = () => side(true); $('#scrim').onclick = () => side(false);

// ---- Dashboard ----
function stats() {
  const wish = rd('sd_wish', rd('sd_wishlist', []));
  $('#stats').innerHTML = [[P().length, 'Total Products'], [6, 'Total Categories'], [rd('sd_clicks', 0), 'Total Clicks'], [wish.length, 'Wishlist Saves']].map(s => `<div class="stat"><b>${s[0]}</b><span>${s[1]}</span></div>`).join('');
}

// ---- Add / edit product ----
const pf = $('#pf');
function fill(p) { for (const k of ['name', 'price', 'original', 'rating', 'reviews', 'store', 'category', 'badge', 'image', 'link', 'desc']) if (p[k] != null && pf[k]) pf[k].value = p[k]; }
function clearForm() { pf.reset(); editId = null; $('#ft').textContent = 'Add Product'; }
$('#pc').onclick = clearForm;
pf.onsubmit = e => {
  e.preventDefault(); const f = pf, list = P();
  const p = { name: f.name.value.trim(), price: +f.price.value, original: +f.original.value || +f.price.value, rating: +f.rating.value || 4, reviews: +f.reviews.value || 0, store: f.store.value, category: f.category.value, badge: f.badge.value, image: f.image.value.trim(), link: f.link.value.trim(), desc: f.desc.value.trim() };
  if (!p.name || !p.price || !p.link) return toast('Name, price and affiliate link are required.', 1);
  if (editId) { const i = list.findIndex(x => x.id === editId); list[i] = { ...list[i], ...p }; toast('Product updated'); }
  else { list.unshift({ id: Date.now(), added: Date.now(), ...p }); toast('Product saved. It is live on the storefront.'); }
  wr('sd_products', list); clearForm(); go('products');
};

// ---- Products table ----
function table() {
  $('#tb').innerHTML = '<tr><td colspan="7"><div class="sk" style="height:60px"></div></td></tr>';
  setTimeout(() => {
    const q = $('#tq').value.toLowerCase(), s = $('#ts').value, c = $('#tc').value, o = $('#to').value;
    const r = P().filter(p => (!q || p.name.toLowerCase().includes(q)) && (!s || p.store === s) && (!c || p.category === c));
    r.sort(o === 'price' ? (a, b) => a.price - b.price : o === 'name' ? (a, b) => a.name.localeCompare(b.name) : (a, b) => (b.added || b.id) - (a.added || a.id));
    $('#tb').innerHTML = r.map(p => `<tr><td>${String(p.id).slice(-5)}</td><td><img src="${esc(p.image)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'"></td><td>${esc(p.name)}</td><td>${inr(p.price)}</td><td>${esc(p.store)}</td><td>${esc(p.category)}</td><td><button class="a" data-a="edit" data-id="${p.id}">Edit</button><button class="a td-del" data-a="del" data-id="${p.id}">Delete</button><button class="a" data-a="view" data-id="${p.id}">View</button></td></tr>`).join('') || '<tr><td colspan="7" class="empty">📦 No products yet. Add one to see it here.</td></tr>';
  }, 250);
}
['#tq', '#ts', '#tc', '#to'].forEach(s => $(s).addEventListener('input', table));
$('#tb').onclick = async e => {
  const b = e.target.closest('[data-a]'); if (!b) return; const id = +b.dataset.id, p = P().find(x => x.id === id);
  if (b.dataset.a === 'view') window.open(p.link, '_blank', 'noopener');
  if (b.dataset.a === 'edit') { editId = id; fill(p); $('#ft').textContent = 'Edit Product'; go('add'); $('#ft').textContent = 'Edit Product'; }
  if (b.dataset.a === 'del' && await confirmBox(`Delete "${p.name.slice(0, 50)}"?`)) { wr('sd_products', P().filter(x => x.id !== id)); table(); toast('Product deleted'); }
};
$('#ex').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(P(), null, 2)], { type: 'application/json' })); a.download = 'data.json'; a.click(); URL.revokeObjectURL(a.href); };
$('#im').onchange = async e => { const f = e.target.files[0]; if (!f) return; try { toast(`Imported ${add(JSON.parse(await f.text()))} products`); table(); } catch (x) { toast(x.message || 'Invalid JSON file', 1); } e.target.value = ''; };

// ---- Bulk import ----
function parse(t) {
  const a = JSON.parse(t); if (!Array.isArray(a)) throw new Error('JSON must be an array [ ... ]');
  a.forEach((p, i) => { if (!p.name || !p.price || !p.link) throw new Error(`Item ${i + 1} needs name, price and link`); }); return a;
}
function add(a) {
  parse(JSON.stringify(a)); const list = P(), ids = new Set(list.map(p => p.id)); let n = Date.now();
  const add = a.map(p => { let id = +p.id; if (!id || ids.has(id)) { id = ++n; } ids.add(id); return { rating: 4, reviews: 0, store: 'Amazon', category: 'mobiles', badge: '', image: '', ...p, id, price: +p.price, original: +p.original || +p.price, added: Date.now() }; });
  wr('sd_products', [...add, ...list]); return add.length;
}
const bmsg = (m, ok) => { $('#bm2').textContent = m; $('#bm2').style.color = ok ? '#388e3c' : '#ff3f6c'; };
$('#bv').onclick = () => { try { bmsg(`✅ Valid JSON: ${parse($('#bt').value).length} products`, 1); } catch (e) { bmsg('❌ ' + e.message); } };
$('#bi').onclick = () => { try { const n = add(parse($('#bt').value)); bmsg(`✅ Imported ${n} products`, 1); toast(`Imported ${n} products`); $('#bt').value = ''; } catch (e) { bmsg('❌ ' + e.message); toast(e.message, 1); } };

// ---- Bookmarklet (works on Amazon, Flipkart, Meesho, Ajio) ----
const BM = `(function(){var h=location.hostname,Q=function(a){for(var i=0;i<a.length;i++){var e=document.querySelector(a[i]);if(e&&e.textContent.trim())return e.textContent.trim()}return''},N=function(s){return+((s.match(/[\\d,]*\\.?\\d+/)||[0])[0]+'').replace(/,/g,'')||0},M=function(p){var e=document.querySelector(p);return e?e.content:''};var d={name:Q(['#productTitle','span.B_NuCI','h1.pdp-title','h1'])||M('meta[property="og:title"]'),price:N(Q(['.a-price .a-offscreen','div.Nx9bqj','.prod-sp','[class*=ProductPrice]'])),original:N(Q(['.a-text-price .a-offscreen','div.yRaY8j','.prod-cp'])),rating:N(Q(['#acrPopover .a-icon-alt','div.XQDdHH','[class*=rating]'])),reviews:N(Q(['#acrCustomerReviewText','span.Wphh3N','[class*=review]'])),image:M('meta[property="og:image"]'),link:location.href.split('?')[0],desc:M('meta[name=description]'),store:/amazon/.test(h)?'Amazon':/flipkart/.test(h)?'Flipkart':/meesho/.test(h)?'Meesho':'Ajio'};var j=JSON.stringify(d,null,1);try{navigator.clipboard.writeText(j)}catch(x){}var o=document.createElement('div');o.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:2147483647;display:grid;place-items:center;font:14px sans-serif';var b=document.createElement('div');b.style.cssText='background:#fff;color:#212121;border-radius:14px;padding:18px;width:min(460px,92vw)';var t=document.createElement('textarea');t.value=j;t.style.cssText='width:100%;height:200px;font:12px monospace;box-sizing:border-box';var a=document.createElement('button');a.textContent='Copy to Admin Panel';a.style.cssText='background:#fb641b;color:#fff;border:0;border-radius:8px;padding:10px 14px;margin:10px 8px 0 0;font-weight:700;cursor:pointer';a.onclick=function(){var u=new URLSearchParams(d).toString();window.open('__ADMIN__?'+u,'_blank')};var c=document.createElement('button');c.textContent='Close';c.style.cssText='border:1px solid #ccc;background:#fff;border-radius:8px;padding:10px 14px;cursor:pointer';c.onclick=function(){o.remove()};b.append('Copied to clipboard. Review the data:',t,a,c);o.append(b);document.body.append(o)})();`;
$('#bk').value = 'javascript:' + BM.replace('__ADMIN__', location.origin + location.pathname);
$('#bc').onclick = async () => { try { await navigator.clipboard.writeText($('#bk').value); } catch { $('#bk').select(); document.execCommand('copy'); } toast('Bookmarklet copied'); };

// ---- Settings ----
const sf = $('#sf'), DEF = { name: 'SaiDeals', tagline: 'Smart Savings Plus', bar: true, flash: true, recs: true };
function loadSettings() { const s = { ...DEF, ...rd('sd_settings', {}) }; sf.name.value = s.name; sf.tagline.value = s.tagline; sf.bar.checked = s.bar; sf.flash.checked = s.flash; sf.recs.checked = s.recs; }
sf.onsubmit = e => { e.preventDefault(); wr('sd_settings', { name: sf.name.value.trim() || DEF.name, tagline: sf.tagline.value.trim() || DEF.tagline, bar: sf.bar.checked, flash: sf.flash.checked, recs: sf.recs.checked }); toast('Settings saved'); };
$('#pw').onsubmit = e => {
  e.preventDefault(); const f = e.target;
  if (f.o.value !== pass()) return toast('Old password is wrong', 1);
  if (f.n.value !== f.c.value) return toast('New passwords do not match', 1);
  wr('sd_admin_pw', f.n.value); f.reset(); toast('Password updated');
};

function init() {
  loadSettings(); stats();
  const q = new URLSearchParams(location.search); // pre-fill from the bookmarklet
  if (q.get('name')) { fill(Object.fromEntries(q)); history.replaceState(null, '', location.pathname); go('add'); toast('Product details loaded from bookmarklet'); }
}
gate();
