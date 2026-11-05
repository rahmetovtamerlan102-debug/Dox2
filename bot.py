# bot.py — Definitelysearch: чёрный фон, aurora + звёзды
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
  --bg:#000000; --card:rgba(255,255,255,0.04);
  --border:rgba(255,255,255,0.09); --border-hi:rgba(139,92,246,0.55);
  --text:#f0f0ff; --muted:#8888a8;
  --violet:#8b5cf6; --cyan:#06b6d4; --pink:#ec4899; --emerald:#10b981;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}

/* ═══════════ ФОН: чёрный + aurora ═══════════ */
body{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
  background:#000000; color:var(--text); min-height:100vh;
  padding:56px 24px 96px; position:relative; overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
  background-image:
    radial-gradient(ellipse 90% 55% at 25% -15%, rgba(139,92,246,0.22), transparent 60%),
    radial-gradient(ellipse 60% 45% at 85% 35%, rgba(6,182,212,0.14), transparent 65%),
    radial-gradient(ellipse 55% 40% at 10% 90%, rgba(236,72,153,0.10), transparent 65%);
  background-attachment:fixed;
  animation:aurorashift 24s ease-in-out infinite alternate;
}
@keyframes aurorashift{
  0%{background-position:0% 0%, 0% 0%, 0% 0%}
  100%{background-position:5% 3%, -3% 5%, 3% -2%}
}

/* ═══════════ ЗВЁЗДЫ ═══════════ */
body::before{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:0.7;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Ccircle cx='30' cy='50' r='1' fill='%23fff' opacity='0.6'/%3E%3Ccircle cx='150' cy='80' r='0.8' fill='%23fff' opacity='0.5'/%3E%3Ccircle cx='270' cy='30' r='0.6' fill='%23fff' opacity='0.7'/%3E%3Ccircle cx='340' cy='120' r='0.9' fill='%23fff' opacity='0.4'/%3E%3Ccircle cx='80' cy='180' r='0.7' fill='%23fff' opacity='0.5'/%3E%3Ccircle cx='220' cy='200' r='1.1' fill='%23fff' opacity='0.6'/%3E%3Ccircle cx='360' cy='260' r='0.8' fill='%23fff' opacity='0.5'/%3E%3Ccircle cx='60' cy='320' r='0.6' fill='%23fff' opacity='0.7'/%3E%3Ccircle cx='190' cy='340' r='0.9' fill='%23fff' opacity='0.4'/%3E%3Ccircle cx='310' cy='380' r='0.7' fill='%23fff' opacity='0.6'/%3E%3Ccircle cx='120' cy='390' r='0.5' fill='%23fff' opacity='0.5'/%3E%3Ccircle cx='250' cy='290' r='0.8' fill='%23fff' opacity='0.6'/%3E%3C/svg%3E");
  animation:stardrift 180s linear infinite;
}
@keyframes stardrift{from{background-position:0 0}to{background-position:400px 400px}}

body::after{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:0.4;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='600'%3E%3Ccircle cx='40' cy='70' r='0.7' fill='%23a78bfa' opacity='0.5'/%3E%3Ccircle cx='200' cy='150' r='1.2' fill='%2306b6d4' opacity='0.4'/%3E%3Ccircle cx='400' cy='90' r='0.9' fill='%23ec4899' opacity='0.4'/%3E%3Ccircle cx='520' cy='200' r='1' fill='%23fff' opacity='0.5'/%3E%3Ccircle cx='100' cy='300' r='0.8' fill='%23a78bfa' opacity='0.4'/%3E%3Ccircle cx='300' cy='420' r='1.1' fill='%2306b6d4' opacity='0.4'/%3E%3Ccircle cx='550' cy='500' r='0.7' fill='%23fff' opacity='0.5'/%3E%3Ccircle cx='180' cy='550' r='0.9' fill='%23ec4899' opacity='0.4'/%3E%3C/svg%3E");
  animation:stardrift2 240s linear infinite;
}
@keyframes stardrift2{from{background-position:0 0}to{background-position:-600px 600px}}

.wrap{max-width:1080px;margin:0 auto;position:relative;z-index:1}

.hero{margin-bottom:64px;text-align:center;animation:fadein 0.7s ease-out}
@keyframes fadein{from{opacity:0;transform:translateY(-12px)}to{opacity:1;transform:translateY(0)}}
.logo{display:inline-flex;align-items:center;gap:12px;font-size:11px;font-weight:800;color:var(--muted);letter-spacing:0.2em;text-transform:uppercase;margin-bottom:32px;padding:10px 20px;border:1px solid var(--border);border-radius:100px;background:rgba(255,255,255,0.03);backdrop-filter:blur(14px);box-shadow:inset 0 1px 0 rgba(255,255,255,0.06), 0 0 24px rgba(139,92,246,0.08)}
.logo-dot{width:8px;height:8px;border-radius:50%;background:linear-gradient(135deg,var(--violet),var(--cyan));box-shadow:0 0 16px var(--violet);animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.55;transform:scale(1.25)}}
h1{font-size:clamp(36px,7vw,68px);font-weight:900;background:linear-gradient(135deg,#fff 0%,#e9d5ff 25%,#c4b5fd 45%,#a78bfa 60%,#06b6d4 85%,#22d3ee 100%);background-size:300% 300%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.045em;line-height:1;margin-bottom:20px;animation:gradientmove 8s ease infinite;filter:drop-shadow(0 4px 24px rgba(139,92,246,0.35))}
@keyframes gradientmove{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.subtitle{color:var(--muted);font-size:14px;margin-bottom:28px;font-weight:500;letter-spacing:0.02em}
.query-pill{display:inline-flex;align-items:center;gap:12px;background:linear-gradient(135deg,rgba(139,92,246,0.12),rgba(6,182,212,0.06));border:1px solid var(--border-hi);padding:14px 28px;border-radius:100px;font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:700;color:var(--text);backdrop-filter:blur(20px);box-shadow:0 0 40px rgba(139,92,246,0.25),inset 0 1px 0 rgba(255,255,255,0.1),0 4px 20px rgba(0,0,0,0.3);position:relative;overflow:hidden}
.query-pill::before{content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.15),transparent);animation:shimmer 3s ease-in-out infinite}
@keyframes shimmer{0%{left:-100%}100%{left:100%}}
.query-pill::after{content:'';width:8px;height:8px;border-radius:50%;background:var(--emerald);box-shadow:0 0 12px var(--emerald);animation:pulse 2s ease-in-out infinite}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:20px;margin-bottom:56px}
.stat{background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.01));border:1px solid var(--border);border-radius:22px;padding:26px 24px;position:relative;overflow:hidden;backdrop-filter:blur(24px);transition:all 0.45s cubic-bezier(0.4,0,0.2,1);animation:slideup 0.6s ease-out backwards}
.stat:nth-child(1){animation-delay:0.15s}
.stat:nth-child(2){animation-delay:0.25s}
.stat:nth-child(3){animation-delay:0.35s}
@keyframes slideup{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--violet),var(--cyan),transparent);opacity:0.8}
.stat:hover{border-color:var(--border-hi);transform:translateY(-6px) scale(1.02);box-shadow:0 24px 48px rgba(139,92,246,0.28),0 0 0 1px rgba(139,92,246,0.15),inset 0 1px 0 rgba(255,255,255,0.08)}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.16em;margin-bottom:14px;font-weight:700}
.stat-value{font-size:clamp(32px,5vw,48px);font-weight:900;background:linear-gradient(135deg,#fff 0%,#c4b5fd 60%,#06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1;font-family:'JetBrains Mono',monospace;letter-spacing:-0.02em}
.stat-value small{font-size:15px;color:var(--muted);font-weight:600;-webkit-text-fill-color:var(--muted);letter-spacing:0}

.section-title{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.2em;font-weight:800;margin-bottom:28px;display:flex;align-items:center;gap:18px}
.section-title::before{content:'';width:4px;height:4px;border-radius:50%;background:var(--violet);box-shadow:0 0 12px var(--violet)}
.section-title::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border),transparent)}

.card{background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.008));border:1px solid var(--border);border-radius:22px;margin-bottom:22px;overflow:hidden;transition:all 0.45s cubic-bezier(0.4,0,0.2,1);backdrop-filter:blur(24px);animation:slideup 0.6s ease-out backwards;position:relative}
.card:nth-child(1){animation-delay:0.45s}
.card:nth-child(2){animation-delay:0.5s}
.card:nth-child(3){animation-delay:0.55s}
.card:nth-child(4){animation-delay:0.6s}
.card:nth-child(5){animation-delay:0.65s}
.card:nth-child(6){animation-delay:0.7s}
.card:nth-child(7){animation-delay:0.75s}
.card:nth-child(8){animation-delay:0.8s}
.card:hover{border-color:var(--border-hi);transform:translateY(-4px);box-shadow:0 32px 56px rgba(139,92,246,0.22),0 0 0 1px rgba(139,92,246,0.12),inset 0 1px 0 rgba(255,255,255,0.06)}
.card::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:linear-gradient(180deg,var(--violet),var(--cyan),var(--pink));opacity:0.75;transition:all 0.4s}
.card:hover::before{opacity:1;width:4px;box-shadow:0 0 16px var(--violet)}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:20px 28px;border-bottom:1px solid var(--border);background:linear-gradient(90deg,rgba(255,255,255,0.03),rgba(255,255,255,0.005))}
.card-source{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--cyan);font-weight:700;letter-spacing:0.02em;display:flex;align-items:center;gap:10px}
.card-source::before{content:'';width:7px;height:7px;border-radius:50%;background:var(--cyan);box-shadow:0 0 12px var(--cyan);animation:pulse 2s ease-in-out infinite}
.card-num{font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace;background:rgba(255,255,255,0.07);padding:6px 14px;border-radius:10px;font-weight:800;letter-spacing:0.08em;border:1px solid rgba(255,255,255,0.05)}
.card-body{padding:10px 28px}

.field{display:grid;grid-template-columns:200px 1fr;padding:16px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:14.5px;align-items:center;transition:all 0.25s ease}
.field:last-child{border-bottom:none}
.field:hover{background:linear-gradient(90deg,rgba(139,92,246,0.06),rgba(139,92,246,0.01),transparent);border-radius:10px;padding-left:14px;margin-left:-14px;padding-right:14px;margin-right:-14px}
.field-key{color:var(--muted);font-size:13px;font-weight:600;letter-spacing:0.02em;display:flex;align-items:center;gap:12px}
.field-key svg{opacity:0.7;flex-shrink:0}
.field:hover .field-key svg{opacity:1;color:var(--violet)}
.field-val{color:var(--text);word-break:break-word;font-weight:500;line-height:1.55}
.field-val.accent{font-family:'JetBrains Mono',monospace;background:linear-gradient(135deg,#c4b5fd 0%,#a78bfa 40%,#06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-weight:700;letter-spacing:0.01em}

.footer{margin-top:96px;padding-top:48px;border-top:1px solid var(--border);text-align:center;color:var(--muted);font-size:13px;font-weight:500;letter-spacing:0.02em}
.footer-brand{font-size:16px;font-weight:900;color:var(--text);background:linear-gradient(135deg,#c4b5fd,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:10px;letter-spacing:-0.01em}
.footer-meta{font-size:11px;opacity:0.5;margin-top:10px;font-family:'JetBrains Mono',monospace;letter-spacing:0.05em}

@media(max-width:640px){body{padding:32px 16px 64px}.field{grid-template-columns:1fr;gap:8px;padding:14px 0}.field-key{font-size:12px}.field:hover{padding-left:0;margin-left:0;padding-right:0;margin-right:0}.stats{grid-template-columns:1fr 1fr;gap:14px}.stat{padding:20px 18px}.card-head{padding:16px 20px}.card-body{padding:8px 20px}h1{letter-spacing:-0.03em}}
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
