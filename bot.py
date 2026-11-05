# bot.py — HTML-файл в чат
import os, asyncio, logging, io, time, html as htmllib
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

# ═══════════ ГЕНЕРАТОР HTML ═══════════
REPORT_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>doks — report: __QUERY__</title>
<style>
:root{--bg:#0a0a0f;--card:rgba(255,255,255,0.03);--border:rgba(255,255,255,0.08);
  --text:#e8e8f0;--muted:#7a7a8c;--accent1:#8b5cf6;--accent2:#06b6d4;--ok:#10b981}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  background-image:radial-gradient(ellipse 80% 50% at 50% -20%,rgba(139,92,246,0.15),transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%,rgba(6,182,212,0.08),transparent);
  padding:48px 24px}
.wrap{max-width:960px;margin:0 auto}
.hero{margin-bottom:48px;text-align:center}
.logo{display:inline-flex;align-items:center;gap:12px;font-size:14px;
  font-weight:600;color:var(--muted);letter-spacing:0.1em;
  text-transform:uppercase;margin-bottom:24px}
.logo-dot{width:8px;height:8px;border-radius:50%;
  background:linear-gradient(135deg,var(--accent1),var(--accent2));
  box-shadow:0 0 12px var(--accent1);animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
h1{font-size:clamp(28px,5vw,44px);font-weight:800;
  background:linear-gradient(135deg,#fff 0%,#a78bfa 50%,#06b6d4 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;letter-spacing:-0.03em;line-height:1.1;margin-bottom:16px}
.query-pill{display:inline-flex;align-items:center;gap:10px;
  background:var(--card);border:1px solid var(--border);
  padding:10px 20px;border-radius:100px;
  font-family:'SF Mono',Monaco,monospace;font-size:15px;color:var(--text)}
.query-pill::before{content:'';width:6px;height:6px;border-radius:50%;
  background:var(--ok);box-shadow:0 0 8px var(--ok)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:16px;margin-bottom:40px}
.stat{background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:20px;position:relative;overflow:hidden}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,var(--accent1),transparent);opacity:0.5}
.stat-label{font-size:11px;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.08em;margin-bottom:6px}
.stat-value{font-size:32px;font-weight:700;
  background:linear-gradient(135deg,#fff,#a78bfa);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;line-height:1}
.section-title{font-size:13px;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.1em;margin-bottom:20px;display:flex;align-items:center;gap:12px}
.section-title::after{content:'';flex:1;height:1px;
  background:linear-gradient(90deg,var(--border),transparent)}
.card{background:var(--card);border:1px solid var(--border);
  border-radius:16px;margin-bottom:16px;overflow:hidden;transition:all 0.3s}
.card:hover{border-color:rgba(139,92,246,0.3);box-shadow:0 8px 32px rgba(139,92,246,0.15)}
.card-head{display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;border-bottom:1px solid var(--border)}
.card-source{font-family:'SF Mono',monospace;font-size:13px;color:var(--accent2)}
.card-num{font-size:11px;color:var(--muted);font-family:'SF Mono',monospace;
  background:rgba(255,255,255,0.05);padding:4px 10px;border-radius:6px}
.card-body{padding:20px}
.field{display:grid;grid-template-columns:180px 1fr;padding:12px 0;
  border-bottom:1px solid rgba(255,255,255,0.04);font-size:14px}
.field:last-child{border-bottom:none}
.field-key{color:var(--muted);font-size:13px;font-weight:500}
.field-val{color:var(--text);word-break:break-word;font-weight:500;line-height:1.5}
.field-val.accent{font-family:'SF Mono',monospace;
  background:linear-gradient(135deg,#a78bfa,#06b6d4);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;font-weight:600}
.footer{margin-top:64px;padding-top:32px;border-top:1px solid var(--border);
  text-align:center;color:var(--muted);font-size:13px}
@media(max-width:640px){body{padding:24px 16px}
  .field{grid-template-columns:1fr;gap:4px}.stats{grid-template-columns:1fr 1fr}}
</style></head><body>
<div class="wrap">
<div class="hero">
  <div class="logo"><span class="logo-dot"></span>doks · intelligence</div>
  <h1>Search Report</h1>
  <div class="query-pill">__QUERY__</div>
</div>
<div class="stats">
  <div class="stat"><div class="stat-label">Найдено</div>
    <div class="stat-value">__TOTAL__</div></div>
  <div class="stat"><div class="stat-label">Источников</div>
    <div class="stat-value">__SOURCES__</div></div>
  <div class="stat"><div class="stat-label">Время</div>
    <div class="stat-value">__TIME__<span style="font-size:14px;color:var(--muted)">ms</span></div></div>
</div>
<div class="section-title">Результаты поиска</div>
__CARDS__
<div class="footer">doks · private search</div>
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
    return REPORT_HTML \
        .replace("__QUERY__", htmllib.escape(q)) \
        .replace("__TOTAL__", str(len(hits))) \
        .replace("__SOURCES__", str(sources)) \
        .replace("__TIME__", str(elapsed_ms)) \
        .replace("__CARDS__", "".join(cards))

# ═══════════ БОТ ═══════════
def fmt_card(h):
    lines = [f"<b>{html.quote(str(h.get('source','?')))}</b>"]
    for k, v in h.items():
        if k == "source" or v in (None, "", "-", "NULL"): continue
        val = str(v)
        if len(val) > 200: val = val[:197] + "..."
        lines.append(f"  <b>{html.quote(str(k))}:</b> {html.quote(val)}")
    return "\n".join(lines)

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer(
        f"Привет, {html.bold(m.from_user.full_name or 'друг')}.\n\n"
        "Отправь номер, ФИО или TG ID — пришлю текстом + HTML-файл.",
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

    # 1. текстовый ответ
    out = [f"<code>{html.quote(q)}</code> — <b>{len(hits)}</b> записей"]
    for i, h in enumerate(hits[:8], 1):
        out.append(f"\n<b>#{i}</b>\n{fmt_card(h)}")
    if len(hits) > 8:
        out.append(f"\n... ещё {len(hits) - 8}")
    text = "\n".join(out)
    if len(text) > 4000:
        text = text[:3990] + "\n\n<i>...обрезано</i>"
    await msg.edit_text(text, parse_mode="HTML")

    # 2. HTML-файл
    html_content = build_html(q, hits, elapsed)
    filename = f"doks_{q}.html".replace(" ", "_").replace("/", "_")
    try:
        await m.answer_document(
            BufferedInputFile(html_content.encode("utf-8"), filename=filename),
            caption=f"HTML-отчёт: {q} ({len(hits)} записей)"
        )
    except Exception as e:
        await m.answer(f"ошибка файла: {html.quote(str(e))}", parse_mode="HTML")

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
