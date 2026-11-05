# bot.py — Definitelysearch: только HTML-файл, SaaS-отчёт
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

REPORT_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Definitelysearch — __QUERY__</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#06060a; --bg2:#0d0d14; --card:rgba(255,255,255,0.04);
  --card-hover:rgba(255,255,255,0.06);
  --border:rgba(255,255,255,0.09); --border-hi:rgba(139,92,246,0.4);
  --text:#f0f0f8; --muted:#8888a0;
  --accent1:#8b5cf6; --accent2:#06b6d4; --accent3:#f472b6;
  --ok:#10b981; --glow:rgba(139,92,246,0.35);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
  background:var(--bg); color:var(--text); min-height:100vh;
  padding:64px 24px; position:relative; overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
}
body::before{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(ellipse 60% 40% at 50% -10%, rgba(139,92,246,0.22), transparent 60%),
    radial-gradient(ellipse 50% 35% at 85% 90%, rgba(6,182,212,0.15), transparent 60%),
    radial-gradient(ellipse 40% 30% at 10% 80%, rgba(244,114,182,0.10), transparent 60%);
  animation:bgshift 12s ease-in-out infinite alternate;
}
@keyframes bgshift{0%{opacity:1}100%{opacity:0.85;transform:scale(1.05)}}
body::after{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:0.4;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Ccircle cx='1' cy='1' r='0.8' fill='rgba(255,255,255,0.06)'/%3E%3C/svg%3E");
}
.wrap{max-width:1040px;margin:0 auto;position:relative;z-index:1}

.hero{margin-bottom:56px;text-align:center;animation:fadein 0.6s ease-out}
@keyframes fadein{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.logo{
  display:inline-flex;align-items:center;gap:12px;
  font-size:12px;font-weight:700;color:var(--muted);
  letter-spacing:0.16em;text-transform:uppercase;margin-bottom:28px;
  padding:8px 16px;border:1px solid var(--border);border-radius:100px;
  background:rgba(255,255,255,0.02);backdrop-filter:blur(10px);
}
.logo-dot{
  width:8px;height:8px;border-radius:50%;
  background:linear-gradient(135deg,var(--accent1),var(--accent2));
  box-shadow:0 0 14px var(--accent1);
  animation:pulse 2s ease-in-out infinite;
}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.6;transform:scale(1.15)}}
h1{
  font-size:clamp(32px,6vw,56px);font-weight:800;
  background:linear-gradient(135deg,#fff 0%,#c4b5fd 30%,#a78bfa 50%,#06b6d4 80%,#22d3ee 100%);
  background-size:200% 200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;letter-spacing:-0.04em;line-height:1.05;
  margin-bottom:20px;
  animation:gradientmove 6s ease infinite;
}
@keyframes gradientmove{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.subtitle{color:var(--muted);font-size:15px;margin-bottom:24px;font-weight:500}
.query-pill{
  display:inline-flex;align-items:center;gap:10px;
  background:rgba(255,255,255,0.03);
  border:1px solid var(--border-hi);
  padding:12px 24px;border-radius:100px;
  font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;
  color:var(--text);backdrop-filter:blur(20px);
  box-shadow:0 0 30px rgba(139,92,246,0.15), inset 0 1px 0 rgba(255,255,255,0.08);
}
.query-pill::before{
  content:'';width:8px;height:8px;border-radius:50%;
  background:var(--ok);box-shadow:0 0 12px var(--ok);
  animation:pulse 2s ease-in-out infinite;
}

.stats{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:20px;margin-bottom:48px;
}
.stat{
  background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01));
  border:1px solid var(--border);
  border-radius:20px;padding:24px;
  position:relative;overflow:hidden;
  backdrop-filter:blur(20px);
  transition:all 0.4s cubic-bezier(0.4,0,0.2,1);
  animation:slideup 0.5s ease-out backwards;
}
.stat:nth-child(1){animation-delay:0.1s}
.stat:nth-child(2){animation-delay:0.2s}
.stat:nth-child(3){animation-delay:0.3s}
@keyframes slideup{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.stat::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,var(--accent1),var(--accent2),transparent);
  opacity:0.7;
}
.stat::after{
  content:'';position:absolute;bottom:-40%;right:-40%;width:120px;height:120px;
  background:radial-gradient(circle,var(--glow),transparent 70%);
  opacity:0.5;transition:all 0.4s;
}
.stat:hover{
  border-color:var(--border-hi);
  transform:translateY(-4px);
  box-shadow:0 20px 40px rgba(139,92,246,0.25);
}
.stat:hover::after{opacity:1;bottom:-30%;right:-30%}
.stat-label{
  font-size:11px;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.12em;margin-bottom:10px;font-weight:600;
}
.stat-value{
  font-size:clamp(28px,4vw,40px);font-weight:800;
  background:linear-gradient(135deg,#fff,#c4b5fd);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;line-height:1;
  font-family:'JetBrains Mono',monospace;
}
.stat-value small{font-size:14px;color:var(--muted);font-weight:500;-webkit-text-fill-color:var(--muted)}

.section-title{
  font-size:12px;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.16em;font-weight:700;margin-bottom:24px;
  display:flex;align-items:center;gap:16px;
}
.section-title::after{
  content:'';flex:1;height:1px;
  background:linear-gradient(90deg,var(--border),transparent);
}

.card{
  background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01));
  border:1px solid var(--border);
  border-radius:20px;margin-bottom:20px;overflow:hidden;
  transition:all 0.4s cubic-bezier(0.4,0,0.2,1);
  backdrop-filter:blur(20px);
  animation:slideup 0.5s ease-out backwards;
  position:relative;
}
.card:nth-child(1){animation-delay:0.4s}
.card:nth-child(2){animation-delay:0.45s}
.card:nth-child(3){animation-delay:0.5s}
.card:nth-child(4){animation-delay:0.55s}
.card:nth-child(5){animation-delay:0.6s}
.card:nth-child(6){animation-delay:0.65s}
.card:nth-child(7){animation-delay:0.7s}
.card:nth-child(8){animation-delay:0.75s}
.card:hover{
  border-color:var(--border-hi);
  transform:translateY(-3px);
  box-shadow:0 24px 48px rgba(139,92,246,0.2), 0 0 0 1px rgba(139,92,246,0.1);
}
.card::before{
  content:'';position:absolute;top:0;left:0;width:3px;height:100%;
  background:linear-gradient(180deg,var(--accent1),var(--accent2));
  opacity:0.7;transition:opacity 0.3s;
}
.card:hover::before{opacity:1}
.card-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:18px 24px;border-bottom:1px solid var(--border);
  background:rgba(255,255,255,0.02);
}
.card-source{
  font-family:'JetBrains Mono',monospace;font-size:13px;
  color:var(--accent2);font-weight:600;letter-spacing:0.02em;
  display:flex;align-items:center;gap:8px;
}
.card-source::before{
  content:'';width:6px;height:6px;border-radius:50%;
  background:var(--accent2);box-shadow:0 0 10px var(--accent2);
}
.card-num{
  font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace;
  background:rgba(255,255,255,0.06);padding:5px 12px;border-radius:8px;
  font-weight:700;letter-spacing:0.05em;
}
.card-body{padding:8px 24px}

.field{
  display:grid;grid-template-columns:180px 1fr;
  padding:14px 0;border-bottom:1px solid rgba(255,255,255,0.04);
  font-size:14px;align-items:center;transition:background 0.2s;
}
.field:last-child{border-bottom:none}
.field:hover{background:rgba(255,255,255,0.02);border-radius:8px;padding-left:8px;margin-left:-8px}
.field-key{
  color:var(--muted);font-size:13px;font-weight:600;
  letter-spacing:0.02em;display:flex;align-items:center;gap:10px;
}
.field-key::before{
  content:'';width:4px;height:4px;border-radius:50%;
  background:var(--accent1);opacity:0.6;
}
.field-val{
  color:var(--text);word-break:break-word;font-weight:500;line-height:1.5;
}
.field-val.accent{
  font-family:'JetBrains Mono',monospace;
  background:linear-gradient(135deg,#c4b5fd,#06b6d4);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;font-weight:700;
}

.footer{
  margin-top:80px;padding-top:40px;
  border-top:1px solid var(--border);
  text-align:center;color:var(--muted);font-size:13px;
  font-weight:500;letter-spacing:0.02em;
}
.footer-brand{
  font-size:14px;font-weight:700;color:var(--text);
  background:linear-gradient(135deg,#c4b5fd,#06b6d4);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin-bottom:8px;
}
.footer-meta{font-size:12px;opacity:0.6;margin-top:6px}

@media(max-width:640px){
  body{padding:32px 16px}
  .field{grid-template-columns:1fr;gap:6px;padding:12px 0}
  .field-key{font-size:12px}
  .field:hover{padding-left:0;margin-left:0}
  .stats{grid-template-columns:1fr 1fr;gap:12px}
  .stat{padding:18px}
  .card-head{padding:14px 18px}
  .card-body{padding:6px 18px}
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
  <div class="stat">
    <div class="stat-label">Найдено записей</div>
    <div class="stat-value">__TOTAL__</div>
  </div>
  <div class="stat">
    <div class="stat-label">Источников</div>
    <div class="stat-value">__SOURCES__</div>
  </div>
  <div class="stat">
    <div class="stat-label">Время поиска</div>
    <div class="stat-value">__TIME__<small>ms</small></div>
  </div>
</div>

<div class="section-title">Результаты поиска</div>
__CARDS__

<div class="footer">
  <div class="footer-brand">Definitelysearch</div>
  <div>private search engine</div>
  <div class="footer-meta">generated __DATE__ · __QUERY__</div>
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
            fields.append(
                f'<div class="field"><div class="field-key">{k_esc}</div>'
                f'<div class="field-val{accent}">{v_esc}</div></div>'
            )
        if not fields: continue
        cards.append(
            f'<div class="card"><div class="card-head">'
            f'<div class="card-source">{src}</div>'
            f'<div class="card-num">#{i:02d}</div></div>'
            f'<div class="card-body">{"".join(fields)}</div></div>'
        )
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
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
    msg = await m.answer(f"ищу <code>{html.quote(q)}</code>...", parse_mode="HTML")
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
            f"<code>{html.quote(q)}</code>\n\nне найдено",
            parse_mode="HTML"
        )

    # удалить "ищу..."
    try:
        await msg.delete()
    except Exception:
        pass

    # только HTML-файл
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
