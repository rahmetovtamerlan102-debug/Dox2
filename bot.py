# bot.py — Definitelysearch (Phone, Name, TG)
import os, asyncio, logging, time, datetime, html as htmllib, re, hashlib, secrets
import urllib.parse
import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher, html
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.environ["TG_TOKEN"]
API = os.environ["API_URL"].rstrip("/")
PORT = int(os.environ.get("PORT", 8080))
BASE = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8080").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE}{WEBHOOK_PATH}"

dp = Dispatcher()
HTML_CACHE: dict[str, str] = {}

# ═══════════════════════════════════════════════════════════════════
# HTML-ШАБЛОН
# ═══════════════════════════════════════════════════════════════════

REPORT_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Definitelysearch — __QUERY__</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#000000; --card:#0a0a0a; --card-hover:#111111;
  --border:#1a1a1a; --border-hi:#333333;
  --text:#ffffff; --muted:#888888; --accent:#22d3ee;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body {
  font-family:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
  background:#000; color:var(--text); min-height:100vh;
  padding:56px 24px 48px; position:relative;
  -webkit-font-smoothing:antialiased;
  user-select: none; -webkit-user-select: none; -webkit-touch-callout: none;
}
.wrap{max-width:1080px;margin:0 auto;position:relative;z-index:1}

.field-val, .stat-value {
  user-select: none; -webkit-user-select: none; -webkit-touch-callout: none;
  cursor:pointer; display:inline-flex; align-items:center; gap:8px; transition:all 0.2s;
}
.copy-icon { opacity:0; transform:translateX(-4px); transition:all 0.2s ease; color:var(--muted); flex-shrink:0; }
.field:hover .copy-icon, .stat:hover .copy-icon { opacity:0.6; transform:translateX(0); }
.field:hover .field-val.accent .copy-icon { color:var(--accent); }
.field-val:active, .stat-value:active { opacity:0.6; }

.map-link {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 8px;
  background: rgba(34,211,238,0.12); border: 1px solid rgba(34,211,238,0.35);
  margin-left: 8px; color: var(--accent); text-decoration: none; transition: all 0.25s ease;
  vertical-align: middle; flex-shrink: 0;
}
.map-link:hover { background: rgba(34,211,238,0.3); border-color: var(--accent); transform: scale(1.15); box-shadow: 0 0 12px rgba(34,211,238,0.4); }
.map-link svg { width: 14px; height: 14px; display: block; }

.hero{margin-bottom:64px;text-align:center;animation:fadein 0.6s ease-out}
@keyframes fadein{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
.logo{display:inline-flex;align-items:center;gap:12px;font-size:11px;font-weight:700;color:var(--muted);letter-spacing:0.2em;text-transform:uppercase;margin-bottom:32px;padding:10px 20px;border:1px solid var(--border);border-radius:100px;background:#050505;}
.logo-dot{width:8px;height:8px;border-radius:50%;background:#fff;box-shadow:0 0 10px rgba(255,255,255,0.5);animation:pulse 2s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.5;transform:scale(1.2)}}
h1{font-size:clamp(36px,7vw,64px);font-weight:900;color:#fff;letter-spacing:-0.04em;line-height:1;margin-bottom:20px;}
.subtitle{color:var(--muted);font-size:14px;margin-bottom:28px;font-weight:500}
.query-pill{display:inline-flex;align-items:center;gap:12px;background:#050505;border:1px solid var(--border-hi);padding:14px 28px;border-radius:100px;font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:700;color:#fff;}
.query-pill::after{content:'';width:8px;height:8px;border-radius:50%;background:var(--accent);}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:20px;margin-bottom:56px}
.stat{background:#0a0a0a;border:1px solid var(--border);border-radius:16px;padding:26px 24px;transition:all 0.3s ease;animation:slideup 0.5s ease-out backwards;}
.stat:nth-child(1){animation-delay:0.1s}.stat:nth-child(2){animation-delay:0.2s}.stat:nth-child(3){animation-delay:0.3s}
@keyframes slideup{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}
.stat:hover{border-color:var(--border-hi);background:var(--card-hover)}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px;font-weight:700}
.stat-value{font-size:clamp(32px,5vw,44px);font-weight:900;color:#fff;line-height:1;font-family:'JetBrains Mono',monospace;letter-spacing:-0.02em;}
.stat-value small{font-size:15px;color:var(--muted);font-weight:600;letter-spacing:0}

.section-title{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.15em;font-weight:800;margin-bottom:28px;display:flex;align-items:center;gap:16px;}
.section-title::before{content:'';width:6px;height:6px;border-radius:50%;background:#fff}
.section-title::after{content:'';flex:1;height:1px;background:var(--border)}

.card{background:#0a0a0a;border:1px solid var(--border);border-radius:16px;margin-bottom:20px;overflow:hidden;transition:all 0.3s ease;animation:slideup 0.5s ease-out backwards;}
.card:hover{border-color:var(--border-hi);background:var(--card-hover)}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:18px 24px;border-bottom:1px solid var(--border);background:#050505;}
.card-source{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--accent);font-weight:700;display:flex;align-items:center;gap:10px;}
.card-source::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--accent);}
.card-num{font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace;background:#111;padding:6px 12px;border-radius:6px;font-weight:800;border:1px solid var(--border);}
.card-body{padding:10px 24px}

.field{display:grid;grid-template-columns:200px 1fr;padding:14px 0;border-bottom:1px solid #111;font-size:14.5px;align-items:center;}
.field:last-child{border-bottom:none}
.field-key{color:var(--muted);font-size:13px;font-weight:600;display:flex;align-items:center;gap:12px;}
.field-key svg{opacity:0.6;flex-shrink:0;color:#fff}
.field-val{color:#fff;word-break:break-word;font-weight:500;line-height:1.5}
.field-val.accent{font-family:'JetBrains Mono',monospace;color:var(--accent);font-weight:700;}

.sub-list { display: flex; flex-direction: column; gap: 10px; width: 100%; }
.sub-item { background: #050505; border: 1px solid #151515; border-radius: 10px; padding: 12px 16px; font-size: 13px; }
.sub-item .row { display: flex; justify-content: space-between; margin-bottom: 6px; }
.sub-item .row:last-child { margin-bottom: 0; }
.sub-key { color: var(--muted); font-weight: 500; }
.sub-val { color: #fff; font-weight: 600; font-family: 'JetBrains Mono', monospace; word-break: break-all; text-align: right;}

@media(max-width:640px){
  body{padding:32px 16px 48px}
  .field{grid-template-columns:1fr;gap:6px;padding:12px 0}
  .field-key{font-size:12px}
  .stats{grid-template-columns:1fr 1fr;gap:12px}
  .stat{padding:20px 16px}
  .card-head{padding:16px 18px}
  .card-body{padding:8px 18px}
  .sub-item { padding: 10px; }
}
</style></head><body>
<div class="wrap">
<div class="hero">
  <div class="logo"><span class="logo-dot"></span>Definitelysearch</div>
  <h1>Search Report</h1>
  <div class="subtitle">Результаты поиска по запросу</div>
  <div class="query-pill">__QUERY__</div>
</div>
<div class="stats">
  <div class="stat"><div class="stat-label">Найдено записей</div><div class="stat-value">__TOTAL__</div></div>
  <div class="stat"><div class="stat-label">Источников</div><div class="stat-value">__SOURCES__</div></div>
  <div class="stat"><div class="stat-label">Время поиска</div><div class="stat-value">__TIME__<small>ms</small></div></div>
</div>
<div class="section-title">Результаты поиска</div>
__CARDS__
</div>

<script>
document.querySelectorAll('.field-val, .stat-value, .sub-val').forEach(el => {
  el.addEventListener('click', function(e) {
    if (e.target.closest('a')) return; 
    let clone = this.cloneNode(true);
    clone.querySelectorAll('svg, a').forEach(n => n.remove());
    let text = clone.innerText.trim();
    if (!text) return;
    
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed'; textarea.style.opacity = '0'; textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.focus(); textarea.select(); textarea.setSelectionRange(0, textarea.value.length);
    try { document.execCommand('copy'); } catch (err) {}
    document.body.removeChild(textarea);
  });
});
</script>
</body></html>"""

ICONS = {
    "телефон":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    "фио":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "фамилия":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    "отчество": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg>',
    "инн":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "снилс":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><rect x="6" y="13" width="4" height="3" rx="1"/><line x1="14" y1="15" x2="18" y2="15"/></svg>',
    "паспорт":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="9" r="3"/><path d="M8 17h8"/></svg>',
    "адрес":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "дата":     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
    "email":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/></svg>',
    "tg id":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>',
    "пол":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>',
    "оператор": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg>',
    "регион":   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "страна":   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "маска карты": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>',
    "банк карты":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M3 10h18M3 7l9-4 9 4M3 10v11M21 10v11"/></svg>',
    "сумма":       '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>',
    "координаты":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/></svg>',
}

COPY_SVG = '<svg class="copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'

def icon_for(key):
    k = str(key).lower()
    for kk, svg in ICONS.items():
        if kk in k: return svg
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

# ═══════════════════════════════════════════════════════════════════
# HTML BUILDER
# ═══════════════════════════════════════════════════════════════════

def build_html(q, hits, elapsed_ms):
    def clean_surrogates(text):
        if not isinstance(text, str): return text
        return text.encode('utf-8', errors='replace').decode('utf-8')

    hits.sort(key=lambda x: 0 if "DaData" in str(x.get("source", "")) else 1)
    sources = len(set(h.get("source", "") for h in hits))
    cards = []
    for i, h in enumerate(hits, 1):
        raw_src = str(h.get("source", "?"))
        clean_src = raw_src.split('.')[-1] if '.' in raw_src else raw_src
        src = htmllib.escape(clean_surrogates(clean_src))
        
        fields = []
        for k, v in h.items():
            if k == "source" or v in (None, "", "-"): continue
            if str(k).lower() in ('телефон', 'phone') and raw_src == "DaData": continue
            if str(k).lower() == 'оператор':
                v_str = str(v)
                v_str = re.sub(r'^(ПАО|ООО|АО|ЗАО|ОАО|АНО)\s+', '', v_str, flags=re.IGNORECASE)
                for ch in ['"', '«', '»', "'", '`']: v_str = v_str.replace(ch, '')
                v = v_str.strip()
            k_esc = htmllib.escape(clean_surrogates(str(k)))
            svg = icon_for(k)

            if isinstance(v, list):
                items_html = []
                for sub in v:
                    if not isinstance(sub, dict): continue
                    rows = []
                    for sk, sv in sub.items():
                        if sv in (None, "", "-"): continue
                        sk_esc = htmllib.escape(str(sk))
                        sv_esc = htmllib.escape(clean_surrogates(str(sv)))
                        rows.append(f'<div class="row"><span class="sub-key">{sk_esc}</span><span class="sub-val">{sv_esc} {COPY_SVG}</span></div>')
                    if rows:
                        items_html.append(f'<div class="sub-item">{"".join(rows)}</div>')
                if items_html:
                    fields.append(f'<div class="field"><div class="field-key">{svg}{k_esc}</div><div class="sub-list">{"".join(items_html)}</div></div>')
                continue

            v_esc = htmllib.escape(clean_surrogates(str(v)))
            accent = ' accent' if str(k).lower() in ('телефон', 'инн', 'снилс', 'паспорт', 'tg id') else ''
            map_link = ''
            if str(k).lower() in ('адрес', 'address') and len(v_esc) > 5:
                yandex_url = f"https://yandex.ru/maps/?text={urllib.parse.quote(v_esc)}"
                map_link = f' <a href="{yandex_url}" target="_blank" class="map-link" title="Открыть на карте" onclick="event.stopPropagation()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg></a>'
            
            fields.append(f'<div class="field"><div class="field-key">{svg}{k_esc}</div><div class="field-val{accent}" title="Нажмите для копирования">{v_esc}{map_link} {COPY_SVG}</div></div>')
            
        if not fields: continue
        cards.append(f'<div class="card"><div class="card-head"><div class="card-source">{src}</div><div class="card-num">#{i:02d}</div></div><div class="card-body">{"".join(fields)}</div></div>')
    now = datetime.datetime.now().strftime("%d.%m.%Y · %H:%M")
    return REPORT_HTML \
        .replace("__QUERY__", htmllib.escape(clean_surrogates(q))) \
        .replace("__TOTAL__", str(len(hits))) \
        .replace("__SOURCES__", str(sources)) \
        .replace("__TIME__", str(elapsed_ms)) \
        .replace("__DATE__", now) \
        .replace("__CARDS__", "".join(cards))

# ═══════════════════════════════════════════════════════════════════
# TELEGRAM TEXT BUILDER
# ═══════════════════════════════════════════════════════════════════

def _clean_operator(s):
    s = str(s or "")
    for p in ("ПАО ", "ООО ", "АО ", "ЗАО ", "ОАО ", "АНО "): s = s.replace(p, "")
    for ch in ('"', '«', '»', "'", '`'): s = s.replace(ch, "")
    return s.strip()

def _tree(fields):
    return "\n".join(f"{'└' if i == len(fields)-1 else '├'} {k}: {v}" for i, (k, v) in enumerate(fields))

def _section(title, emoji, fields):
    if not fields: return ""
    return f"{emoji} <b>{title}</b>\n{_tree(fields)}"

def build_telegram_text(q, hits, max_hits=3):
    dadata = [h for h in hits if h.get("source") == "DaData"]
    main = [h for h in hits if h.get("source") != "DaData"]

    out = []
    dadata_phone = None

    # ── DaData ──
    if dadata:
        d = dadata[0]
        fields = []
        if d.get("Телефон"):
            dadata_phone = re.sub(r'\D', '', str(d['Телефон']))
            fields.append(("Телефон", f"<code>{html.quote(d['Телефон'])}</code>"))
        if d.get("Оператор"):
            fields.append(("Оператор", html.quote(_clean_operator(d["Оператор"]))))
        if d.get("Регион"):
            fields.append(("Регион", html.quote(d["Регион"])))
        if d.get("Страна"):
            fields.append(("Страна", html.quote(d["Страна"])))
        if fields:
            out.append(_section("Телефон", "📱", fields))
            out.append("")

    for h in main[:max_hits]:
        h_lower = {str(k).lower(): str(v).strip() for k, v in h.items() if v not in (None, "", "-")}
        
        # ── Собираем ФИО ──
        fio_parts = []
        for k in ('фамилия', 'lastname'):
            if k in h_lower: fio_parts.append(h_lower[k])
        for k in ('имя', 'firstname'):
            if k in h_lower: fio_parts.append(h_lower[k])
        for k in ('отчество', 'middlename', 'patronymic'):
            if k in h_lower: fio_parts.append(h_lower[k])
            
        full_fio = h_lower.get('фио') or h_lower.get('name') or h_lower.get('fio')
        if not full_fio and fio_parts:
            full_fio = " ".join(fio_parts)

        # ── Дата рождения и Возраст ──
        bday_str = h_lower.get('дата рождения') or h_lower.get('birthdate') or h_lower.get('birthday') or h_lower.get('др') or h_lower.get('bdate') or h_lower.get('dob')
        age_str = h_lower.get('возраст') or h_lower.get('age')
        
        if not age_str and bday_str:
            try:
                bday_clean = re.sub(r'[^\d\.\-\/]', '', bday_str)
                parts = re.split(r'[\.\-\/]', bday_clean)
                if len(parts) == 3:
                    if len(parts[0]) == 4: # YYYY-MM-DD
                        b_year, b_month, b_day = int(parts[0]), int(parts[1]), int(parts[2])
                    else: # DD.MM.YYYY
                        b_day, b_month, b_year = int(parts[0]), int(parts[1]), int(parts[2])
                    today = datetime.date.today()
                    age = today.year - b_year - ((today.month, today.day) < (b_month, b_day))
                    age_str = str(age)
            except Exception:
                pass

        # ── Телефон ──
        phone_val = h_lower.get('телефон') or h_lower.get('phone')
        if phone_val:
            if dadata_phone and re.sub(r'\D', '', phone_val) == dadata_phone:
                phone_val = None

        # ── Адрес ──
        addr_parts = []
        for k in ('город', 'city', 'регион', 'region', 'страна', 'country', 'адрес', 'address'):
            if k in h_lower and h_lower[k] != phone_val:
                addr_parts.append(h_lower[k])
        addr_str = ", ".join(addr_parts) if addr_parts else None

        # ── Документы ──
        docs_f = []
        for k, label in [('паспорт', 'Паспорт'), ('passport', 'Паспорт'), ('инн', 'ИНН'), ('inn', 'ИНН'), ('снилс', 'СНИЛС'), ('snils', 'СНИЛС'), ('пароль', 'Пароль'), ('password', 'Пароль')]:
            if k in h_lower: docs_f.append((label, f"<code>{html.quote(h_lower[k])}</code>"))

        # ── Прочее ──
        other_f = []
        for k, label in [('email', 'Email'), ('почта', 'Email')]:
            if k in h_lower:
                other_f.append((label, f"<code>{html.quote(h_lower[k])}</code>"))
                break
        for k, label in [('вконтакте', 'ВКонтакте'), ('vk_url', 'ВКонтакте')]:
            if k in h_lower:
                other_f.append((label, f'<a href="{html.quote(h_lower[k])}">открыть</a>'))
                break

        blocks = []
        main_f = []
        if full_fio: main_f.append(("ФИО", f"<b>{html.quote(full_fio)}</b>"))
        if bday_str: main_f.append(("Дата рождения", f"<b>{html.quote(bday_str)}</b>"))
        if age_str: main_f.append(("Возраст", f"<b>{html.quote(age_str)}</b>"))
        if main_f: blocks.append(_section("Основные данные", "👤", main_f))

        if phone_val:
            blocks.append(_section("Телефон", "📱", [("Телефон", f"<code>{html.quote(phone_val)}</code>")]))
        if addr_str:
            blocks.append(_section("Адрес", "📍", [("Адрес", html.quote(addr_str))]))
        if docs_f:
            blocks.append(_section("Документы", "🔒", docs_f))
        if other_f:
            blocks.append(_section("Прочее", "📋", other_f))

        if blocks:
            out.append("\n\n".join(blocks))
            out.append("")

    if len(main) > max_hits:
        out.append(f"<i>и ещё {len(main) - max_hits} записей — в полном отчёте</i>")

    text = "\n".join(out).strip()
    if len(text) > 4000: text = text[:3950] + "\n\n<i>… обрезано</i>"
    return text

# ═══════════════════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def start(m: Message):
    name = html.quote(m.from_user.full_name or 'друг')
    await m.answer(
        f"<b>Привет, {name}!</b>\n\n"
        "<blockquote><b>Отправь данные для поиска:</b>\n"
        "<code>Телефон</code>\n<code>ФИО</code>\n<code>TG ID</code></blockquote>\n\n"
        "<i>Данные будут собраны из открытых и закрытых источников.</i>",
        parse_mode="HTML"
    )

@dp.message()
async def handle(m: Message):
    q = (m.text or "").strip()
    if len(q) < 3:
        return await m.answer("слишком короткий запрос (минимум 3 символа)")

    msg = await m.answer("🔍 Поиск...")
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.get(f"{API}/lookup", params={"q": q})
            data = r.json()
    except Exception as e:
        return await msg.edit_text(f"API недоступен: <code>{html.quote(str(e))}</code>", parse_mode="HTML")

    hits = data.get("hits", [])
    elapsed = int((time.time() - t0) * 1000)

    if not hits:
        return await msg.edit_text(f"<code>{html.quote(q)}</code>\n\n✗ не найдено", parse_mode="HTML")

    try: await msg.delete()
    except: pass

    text = build_telegram_text(q, hits, max_hits=3)

    html_content = build_html(q, hits, elapsed)
    rid = secrets.token_urlsafe(8)
    HTML_CACHE[rid] = html_content
    if len(HTML_CACHE) > 200:
        HTML_CACHE.pop(next(iter(HTML_CACHE)))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"📄 Все {len(hits)} записей (HTML)", callback_data=f"file:{rid}")
    ]])

    await m.answer(text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)

@dp.callback_query(lambda c: c.data.startswith("file:"))
async def on_file(cb: CallbackQuery):
    rid = cb.data.split(":", 1)[1]
    content = HTML_CACHE.get(rid)
    if not content:
        return await cb.answer("Отчёт устарел, отправь запрос заново", show_alert=True)
    await cb.message.answer_document(
        BufferedInputFile(content.encode("utf-8"), filename=f"Definitelysearch_{rid}.html"),
        caption="📄 Полный HTML-отчёт"
    )
    await cb.answer("Отправлено")

# ═══════════════════════════════════════════════════════════════════
# WEBHOOK / WEB
# ═══════════════════════════════════════════════════════════════════

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"webhook set: {WEBHOOK_URL}")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    dp.startup.register(on_startup)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.router.add_get("/", lambda r: web.Response(text="ok"))
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"listening on {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
