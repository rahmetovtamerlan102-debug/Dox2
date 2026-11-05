# bot.py — aiogram 3 webhook для Render
import os, asyncio, logging
import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher, html
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from report import report_handler

TOKEN = os.environ["TG_TOKEN"]
API = os.environ["API_URL"].rstrip("/")
PORT = int(os.environ.get("PORT", 8080))
BASE = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8080").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE}{WEBHOOK_PATH}"

dp = Dispatcher()

def fmt_card(h):
    lines = [f"📂 <b>{html.quote(str(h.get('source','?')))}</b>"]
    for k, v in h.items():
        if k == "source" or v in (None, "", "-", "NULL"): continue
        val = str(v)
        if len(val) > 200: val = val[:197] + "..."
        lines.append(f"  <b>{html.quote(str(k))}:</b> {html.quote(val)}")
    return "\n".join(lines)

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer(
        f"Привет, {html.bold(m.from_user.full_name or 'друг')}!\n\n"
        "Кидай:\n"
        "• номер — <code>79887415988</code>\n"
        "• TG ID — <code>6607391529</code>\n"
        "• ФИО — <code>Иванов</code>\n\n"
        "/help — помощь",
        parse_mode="HTML"
    )

@dp.message()
async def handle(m: Message):
    q = (m.text or "").strip()
    if len(q) < 3:
        return await m.answer("слишком короткий запрос (минимум 3 символа)")
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.get(f"{API}/lookup", params={"q": q})
            data = r.json()
    except Exception as e:
        return await m.answer(f"API недоступен: <code>{html.quote(str(e))}</code>", parse_mode="HTML")
    hits = data.get("hits", [])
    if not hits:
        return await m.answer(f"🔎 <code>{html.quote(q)}</code>\n\n✗ не найдено", parse_mode="HTML")

    out = [f"🔎 <code>{html.quote(q)}</code> — <b>{len(hits)}</b> записей"]
    for i, h in enumerate(hits[:8], 1):
        out.append(f"\n<b>#{i}</b>\n{fmt_card(h)}")
    if len(hits) > 8:
        out.append(f"\n... ещё {len(hits) - 8}")

    text = "\n".join(out)
    if len(text) > 4000:
        text = text[:3990] + "\n\n<i>...обрезано</i>"
    await m.answer(text, parse_mode="HTML")

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"webhook set: {WEBHOOK_URL}")

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bot = Bot(token=TOKEN)
    dp.startup.register(on_startup)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.router.add_get("/", lambda r: web.Response(text="doks bot ok"))
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    app.router.add_get("/report", report_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"listening on {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
