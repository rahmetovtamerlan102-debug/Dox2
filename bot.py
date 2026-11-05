# bot.py — Definitelysearch: строгий чёрный фон
import os, asyncio, logging, time, datetime, html as htmllib
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
}

def icon_for(key):
    k = str(key).lower()
    for kk, svg in ICONS.items():
        if kk in k: return svg
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

REPORT_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Definitelysearch — __QUERY__</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#000000;
  --card:#0a0a0a;
  --card-hover:#111111;
  --border:#1a1a1a;
  --border-hi:#333333;
  --text:#ffffff;
  --muted:#888888;
  --accent:#22d3ee;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
  background:#000; color:var(--text); min-height:100vh;
  padding:56px 24px 96px; position:relative;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px;margin:0 auto;position:relative;z-index:1}

/* HERO */
.hero{margin-bottom:64px;text-align:center;animation:fadein 0.6s ease-out}
@keyframes fadein{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
.logo{
  display:inline-flex;align-items:center;gap:12px;
  font-size:11px;font-weight:700;color:var(--muted);
  letter-spacing:0.2em;text-transform:uppercase;margin-bottom:32px;
  padding:10px 20px;border:1px solid var(--border);border-radius:100px;
  background:#050505;
}
.logo-dot{
  width:8px;height:8px;border-radius:50%;
  background:#fff;
  box-shadow:0 0 10px rgba(255,255,255,0.5);
  animation:pulse 2s ease-in-out infinite;
}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.5;transform:scale(1.2)}}
h1{
  font-size:clamp(36px,7vw,64px);font-weight:900;
  color:#fff;letter-spacing:-0.04em;line-height:1;
  margin-bottom:20px;
}
.subtitle{color:var(--muted);font-size:14px;margin-bottom:28px;font-weight:500}
.query-pill{
  display:inline-flex;align-items:center;gap:12px;
  background:#050505;border:1px solid var(--border-hi);
  padding:14px 28px;border-radius:100px;
  font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:700;
  color:#fff;
}
.query-pill::after{
  content:'';width:8px;height:8px;border-radius:50%;
  background:var(--accent);
}

/* STATS */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:20px;margin-bottom:56px}
.stat{
  background:#0a0a0a;border:1px solid var(--border);
  border-radius:16px;padding:26px 24px;
  transition:all 0.3s ease;
  animation:slideup 0.5s ease-out backwards;
}
.stat:nth-child(1){animation-delay:0.1s}
.stat:nth-child(2){animation-delay:0.2s}
.stat:nth-child(3){animation-delay:0.3s}
@keyframes slideup{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}
.stat:hover{border-color:var(--border-hi);background:var(--card-hover)}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px;font-weight:700}
.stat-value{
  font-size:clamp(32px,5vw,44px);font-weight:900;
  color:#fff;line-height:1;
  font-family:'JetBrains Mono',monospace;letter-spacing:-0.02em;
}
.stat-value small{font-size:15px;color:var(--muted);font-weight:600;letter-spacing:0}

/* SECTION */
.section-title{
  font-size:11px;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.15em;font-weight:800;margin-bottom:28px;
  display:flex;align-items:center;gap:16px;
}
.section-title::before{content:'';width:6px;height:6px;border-radius:50%;background:#fff}
.section-title::after{content:'';flex:1;height:1px;background:var(--border)}

/* CARDS */
.card{
  background:#0a0a0a;border:1px solid var(--border);
  border-radius:16px;margin-bottom:20px;overflow:hidden;
  transition:all 0.3s ease;
  animation:slideup 0.5s ease-out backwards;
}
.card:nth-child(1){animation-delay:0.4s}
.card:nth-child(2){animation-delay:0.45s}
.card:nth-child(3){animation-delay:0.5s}
.card:nth-child(4){animation-delay:0.55s}
.card:nth-child(5){animation-delay:0.6s}
.card:hover{border-color:var(--border-hi);background:var(--card-hover)}
.card-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:18px 24px;border-bottom:1px solid var(--border);
  background:#050505;
}
.card-source{
  font-family:'JetBrains Mono',monospace;font-size:13px;
  color:var(--accent);font-weight:700;
  display:flex;align-items:center;gap:10px;
}
.card-source::before{
  content:'';width:6px;height:6px;border-radius:50%;
  background:var(--accent);
}
.card-num{
  font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace;
  background:#111;padding:6px 12px;border-radius:6px;
  font-weight:800;border:1px solid var(--border);
}
.card-body{padding:10px 24px}

/* FIELDS */
.field{
  display:grid;grid-template-columns:200px 1fr;
  padding:14px 0;border-bottom:1px solid #111;
  font-size:14.5px;align-items:center;
}
.field:last-child{border-bottom:none}
.field-key{
  color:var(--muted);font-size:13px;font-weight:600;
  display:flex;align-items:center;gap:12px;
}
.field-key svg{opacity:0.6;flex-shrink:0;color:#fff}
.field-val{color:#fff;word-break:break-word;font-weight:500;line-height:1.5}
.field-val.accent{
  font-family:'JetBrains Mono',monospace;
  color:var(--accent);font-weight:700;
}

/* FOOTER */
.footer{
  margin-top:80px;padding-top:40px;
  border-top:1px solid var(--border);
  text-align:center;color:var(--muted);font-size:13px;font-weight:500;
}
.footer-brand{font-size:15px;font-weight:900;color:#fff;margin-bottom:8px}
.footer-meta{font-size:11px;opacity:0.5;margin-top:8px;font-family:'JetBrains Mono',monospace}

@media(max-width:640px){
  body{padding:32px 16px 64px}
  .field{grid-template-columns:1fr;gap:6px;padding:12px 0}
  .field-key{font-size:12px}
  .stats{grid-template-columns:1fr 1fr;gap:12px}
  .stat{padding:20px 16px}
  .card-head{padding:16px 18px}
  .card-body{padding:8px 18px}
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
<div class="footer">
  <div class="footer-brand">Definitelysearch</div>
  <div>private search engine</div>
  <div class="footer-meta">GENERATED __DATE__ · QUERY __QUERY__</div>
</div>
</div></body></html>"""

def build_html(q, hits, elapsed_ms):
    sources = len(set(h.get("source", "") for h in hits))
    cards = []
    for i, h in enumerate(hits, 1):
        src = htmllib.escape(str(h.get("source", "?")))
        fields = []
        for k, v in h.items():
            if k == "source" or v in (None, "", "-"): continue
            k_esc = htmllib.escape(str(k))
            v_esc = htmllib.escape(str(v))
            accent = ' accent' if str(k).lower() in (
                'телефон','инн','снилс','паспорт','tg id'
            ) else ''
            svg = icon_for(k)
            fields.append(
                f'<div class="field"><div class="field-key">{svg}{k_esc}</div>'
                f'<div class="field-val{accent}">{v_esc}</div></div>'
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
        .replace("__QUERY__", htmllib.escape(q)) \
        .replace("__TOTAL__", str(len(hits))) \
        .replace("__SOURCES__", str(sources)) \
        .replace("__TIME__", str(elapsed_ms)) \
        .replace("__DATE__", now) \
        .replace("__CARDS__", "".join(cards))

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer(
        f"Привет, {html.bold(m.from_user.full_name or 'друг')}.\n\n"
        "Отправь номер, ФИО или TG ID — пришлю HTML-отчёт Definitelysearch.",
        parse_mode="HTML"
    )

@dp.message()
async def handle(m: Message):
    q = (m.text or "").strip()
    if len(q) < 3:
        return await m.answer("слишком короткий запрос (минимум 3 символа)")

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.get(f"{API}/lookup", params={"q": q})
            data = r.json()
    except Exception as e:
        return await m.answer(f"API недоступен: <code>{html.quote(str(e))}</code>", parse_mode="HTML")

    hits = data.get("hits", [])
    elapsed = int((time.time() - t0) * 1000)

    if not hits:
        return await m.answer(
            f"<code>{html.quote(q)}</code>\n\nне найдено",
            parse_mode="HTML"
        )

    html_content = build_html(q, hits, elapsed)
    safe_q = q.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"Definitelysearch_{safe_q}.html"
    await m.answer_document(
        BufferedInputFile(html_content.encode("utf-8"), filename=filename),
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
