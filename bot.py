# bot.py — Definitelysearch (с профилем и API ключами)
import os, asyncio, logging, time, datetime, html as htmllib, re, urllib.parse, secrets, sqlite3, random, string
import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher, html, F
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

# ═══════════════════════════════════════════════════════════════════
# БАЗА ДЛЯ ПОЛЬЗОВАТЕЛЕЙ (SQLite)
# ═══════════════════════════════════════════════════════════════════
DB_PATH = "users.db"
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance REAL DEFAULT 0,
        api_key TEXT,
        key_expires TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance, api_key, key_expires FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        conn.commit()
        row = (0, None, None)
    conn.close()
    return row

def update_user(user_id, balance=None, api_key=None, key_expires=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if balance is not None:
        c.execute("UPDATE users SET balance=? WHERE user_id=?", (balance, user_id))
    if api_key is not None:
        c.execute("UPDATE users SET api_key=?, key_expires=? WHERE user_id=?", (api_key, key_expires, user_id))
    conn.commit()
    conn.close()

def generate_key():
    # Генерирует ключ вида Definitelysearch_XXXXX
    return "Definitelysearch_" + ''.join(random.choices(string.ascii_letters + string.digits, k=24))

# ═══════════════════════════════════════════════════════════════════
# HTML-ШАБЛОН (без изменений, оставляем как было)
# ═══════════════════════════════════════════════════════════════════

# ... (ВСТАВЬ СЮДА ВЕСЬ REPORT_HTML, ICONS И COPY_SVG ИЗ ПРЕДЫДУЩЕГО КОДА) ...

# ═══════════════════════════════════════════════════════════════════
# ОБРАБОТЧИКИ КОМАНД И КНОПОК
# ═══════════════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def start(m: Message):
    name = html.quote(m.from_user.full_name or 'друг')
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await m.answer(
        f"<b>Привет, {name}!</b>\n\n"
        "<blockquote><b>Отправь данные для поиска:</b>\n"
        "<code>Телефон</code>\n"
        "<code>ФИО</code>\n"
        "<code>TG ID</code></blockquote>\n\n"
        "<i>Данные будут собраны из открытых и закрытых источников.</i>",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(F.data == "main_menu")
async def show_main_menu(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ API - ключ Spectrum", callback_data="api_menu")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    
    await cb.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=kb
    )
    await cb.answer()

@dp.callback_query(F.data == "api_menu")
async def show_api_menu(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="7 дн. — $7.50", callback_data="buy_7")],
        [InlineKeyboardButton(text="30 дн. — $10.60", callback_data="buy_30")],
        [InlineKeyboardButton(text="365 дн. — $15.50", callback_data="buy_365")],
        [InlineKeyboardButton(text="⚙️ Мой API - ключ", callback_data="my_api_key")],
        [InlineKeyboardButton(text="📄 Документация", url="https://api.usespectrum.cfd")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    
    await cb.message.edit_text(
        "⚙️ <b>API - ключ Definitelysearch</b>\n\n"
        "Получите доступ к нашему API для автоматизации поиска.\n\n"
        "<b>Тарифы:</b>\n"
        "• 7 дн. — $7.50\n"
        "• 30 дн. — $10.60\n"
        "• 365 дн. — $15.50\n\n"
        "<i>После оплаты ключ будет сгенерирован автоматически.</i>",
        parse_mode="HTML",
        reply_markup=kb
    )
    await cb.answer()

@dp.callback_query(F.data == "my_api_key")
async def show_my_api_key(cb: CallbackQuery):
    user_id = cb.from_user.id
    balance, api_key, key_expires = get_user(user_id)
    
    if not api_key:
        text = (
            "⚙️ <b>Мой API - ключ</b>\n\n"
            "У вас пока нет API-ключа. Приобретите его в разделе тарифов."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Купить ключ", callback_data="api_menu")]
        ])
    else:
        text = (
            f"⚙️ <b>Мой API - ключ</b>\n\n"
            f"🔑 <b>Ваш ключ:</b>\n"
            f"<code>{api_key}</code>\n\n"
            f"📅 <b>Действует до:</b> {key_expires}\n\n"
            f"<i>Используйте его в заголовке <code>X-API-Key</code> или в параметре <code>?key=</code>.</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="api_menu")]
        ])
    
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_key(cb: CallbackQuery):
    days = int(cb.data.split("_")[1])
    user_id = cb.from_user.id
    
    # Проверка баланса
    balance, _, _ = get_user(user_id)
    price = {7: 7.50, 30: 10.60, 365: 15.50}[days]
    
    if balance < price:
        await cb.answer(f"❌ Недостаточно средств. Пополните баланс на ${price - balance:.2f}", show_alert=True)
        return
        
    # Списываем баланс и генерируем ключ
    new_balance = balance - price
    key = generate_key()
    expires = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    update_user(user_id, balance=new_balance, api_key=key, key_expires=expires)
    
    await cb.message.edit_text(
        f"✅ <b>Успешно!</b>\n\n"
        f"Ваш новый API-ключ:\n<code>{key}</code>\n\n"
        f"Действует до: {expires}\n"
        f"Остаток на балансе: ${new_balance:.2f}",
        parse_mode="HTML"
    )
    await cb.answer("Ключ сгенерирован")

@dp.callback_query(F.data == "back")
async def back_to_menu(cb: CallbackQuery):
    await show_main_menu(cb)

# ═══════════════════════════════════════════════════════════════════
# ПОИСК (Главный обработчик)
# ═══════════════════════════════════════════════════════════════════

@dp.message()
async def handle(m: Message):
    q = (m.text or "").strip()
    if len(q) < 3:
        return await m.answer("слишком короткий запрос (минимум 3 символа)")

    msg = await m.answer("🔍 Поиск...")

    t0 = time.time()
    API_KEY = "test_key_123"  # Ключ из твоего api.py
    
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            is_phone = q.startswith('+') or (q.replace(' ', '').replace('-','').isdigit() and len(q) > 9)
            search_type = "phone" if is_phone else "fio"
            
            r = await c.get(
                f"{API}/api/v1/search", 
                params={"q": q, "type": search_type, "key": API_KEY, "serveo-skip-browser-warning": "true"}
            )
            data = r.json()
    except Exception as e:
        return await msg.edit_text(f"API недоступен: <code>{html.quote(str(e))}</code>", parse_mode="HTML")

    if not data.get("success"):
        return await msg.edit_text(f"Ошибка API: {data.get('error')}", parse_mode="HTML")

    hits = data.get("data", [])
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

    # Если у тебя HTML-генератор вынесен в функцию build_html, вызывай её тут
    # html_content = build_html(q, hits, elapsed)
    
    # Заглушка для отправки
    await m.answer(f"Найдено {len(hits)} записей. (HTML генератор нужно вставить)")

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
