# bot.py — Definitelysearch: IP, INN, Phone (с иконками и копированием в 1 клик)
import os, asyncio, logging, time, datetime, html as htmllib, re
import urllib.parse
import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher, html
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.environ["TG_TOKEN"]
API = os.environ["API_URL"].rstrip("/")
PORT = int(os.environ.get("PORT", 8080))
BASE = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8080").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE}{WEBHOOK_PATH}"

dp = Dispatcher()

ICONS = {
    "телефон":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    "фио":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "инн":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/></svg>',
    "снилс":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/></svg>',
    "паспорт":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="10" r="3"/><path d="M8 17h8"/></svg>',
    "адрес":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "дата":     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
    "email":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/></svg>',
    "tg id":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>',
    "пол":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>',
    "оператор": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg>',
    "регион":   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "страна":   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "ip":       '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>',
    "провайдер":'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0 1 14.08 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01"/></svg>',
    "организация":'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "часовой":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    "город":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M3 10h18M3 7l9-4 9 4M3 10v11M21 10v11"/></svg>',
    "время":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    "dns":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg>',
    "isp":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0 1 14.08 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01"/></svg>',
    "asn":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "тип":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
    "прокси":   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "хостинг":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>',
    "координаты":'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/></svg>',
    "индекс":   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    "название": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "кпп":      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/></svg>',
    "огрн":     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
    "статус":   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>',
    "оквэд":    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "руководитель":'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
}

def icon_for(key):
    k = str(key).lower()
    for kk, svg in ICONS.items():
        if kk in k: return svg
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

COPY_SVG = '<svg class="copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'

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

/* Вложенные списки (на всякий случай, если будут массивы) */
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

def build_html(q, hits, elapsed_ms):
    def clean_surrogates(text):
        if not isinstance(text, str): return text
        return text.encode('utf-8', errors='replace').decode('utf-8')

    # Приоритетные источники (DaData и IP) ставим на первые места
    hits.sort(key=lambda x: 0 if "DaData" in str(x.get("source", "")) or "IP" in str(x.get("source", "")) else 1)

    sources = len(set(h.get("source", "") for h in hits))
    cards = []
    for i, h in enumerate(hits, 1):
        src = htmllib.escape(clean_surrogates(str(h.get("source", "?"))))
        fields = []
        for k, v in h.items():
            if k == "source" or v in (None, "", "-"): continue
            
            # Скрываем телефон из DaData (он просто дублирует запрос)
            if str(k).lower() in ('телефон', 'phone') and src == "DaData": continue

            # Очистка оператора от "ПАО", "ООО" и кавычек
            if str(k).lower() == 'оператор':
                v_str = str(v)
                v_str = re.sub(r'^(ПАО|ООО|АО|ЗАО|ОАО|АНО)\s+', '', v_str, flags=re.IGNORECASE)
                for ch in ['"', '«', '»', "'", '`']: v_str = v_str.replace(ch, '')
                v = v_str.strip()

            k_esc = htmllib.escape(clean_surrogates(str(k)))
            svg = icon_for(k)

            # Обработка вложенных списков
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
                    fields.append(
                        f'<div class="field"><div class="field-key">{svg}{k_esc}</div>'
                        f'<div class="sub-list">{"".join(items_html)}</div></div>'
                    )
                continue

            # Обычные строковые поля
            v_esc = htmllib.escape(clean_surrogates(str(v)))
            accent = ' accent' if str(k).lower() in ('телефон', 'инн', 'кпп', 'огрн', 'снилс', 'паспорт', 'tg id', 'ip', 'координаты', 'местное время') else ''
            
            map_link = ''
            if str(k).lower() == 'координаты' and len(v_esc) > 2:
                yandex_url = f"https://yandex.ru/maps/?text={urllib.parse.quote(v_esc)}"
                map_link = f' <a href="{yandex_url}" target="_blank" class="map-link" title="Открыть на карте" onclick="event.stopPropagation()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg></a>'
            elif str(k).lower() in ('адрес', 'address') and len(v_esc) > 5:
                yandex_url = f"https://yandex.ru/maps/?text={urllib.parse.quote(v_esc)}"
                map_link = f' <a href="{yandex_url}" target="_blank" class="map-link" title="Открыть на карте" onclick="event.stopPropagation()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg></a>'
            
            fields.append(
                f'<div class="field"><div class="field-key">{svg}{k_esc}</div>'
                f'<div class="field-val{accent}" title="Нажмите для копирования">'
                f'{v_esc}{map_link} {COPY_SVG}</div></div>'
            )
            
        if not fields: continue
        cards.append(
            f'<div class="card"><div class="card-head">'
            f'<div class="card-source">{src}</div>'
            f'<div class="card-num">#{i:02d}</div></div>'
            f'<div class="card-body">{"".join(fields)}</div></div>'
        )
    now = datetime.datetime.now().strftime("%d.%m.%Y · %H:%M")
    return REPORT_HTML \
        .replace("__QUERY__", htmllib.escape(clean_surrogates(q))) \
        .replace("__TOTAL__", str(len(hits))) \
        .replace("__SOURCES__", str(sources)) \
        .replace("__TIME__", str(elapsed_ms)) \
        .replace("__DATE__", now) \
        .replace("__CARDS__", "".join(cards))

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer(
        f"Привет, {html.bold(m.from_user.full_name or 'друг')}.\n\n"
        "Отправь номер, ИНН, ФИО, IP или TG ID — пришлю HTML-отчёт Definitelysearch.",
        parse_mode="HTML"
    )

@dp.message()
async def handle(m: Message):
    q = (m.text or "").strip()
    if len(q) < 3:
        return await m.answer("слишком короткий запрос (минимум 3 символа)")

    msg = await m.answer("Поиск...")

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
        return await msg.edit_text(
            f"<code>{html.quote(q)}</code>\n\n✗ не найдено",
            parse_mode="HTML"
        )

    try:
        await msg.delete()
    except Exception:
        pass

    html_content = build_html(q, hits, elapsed)
    safe_q = q.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"Definitelysearch_{safe_q}.html"
    html_bytes = html_content.encode("utf-8", errors="replace")
    
    await m.answer_document(
        BufferedInputFile(html_bytes, filename=filename),
        caption=f"HTML-отчёт: {q} ({len(hits)} записей)"
    )

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
PYEOF
