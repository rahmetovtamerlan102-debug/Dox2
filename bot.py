# bot.py — Definitelysearch (PostgreSQL + Все SVG иконки + Admin + Promo + CryptoBot)
import os, asyncio, logging, time, datetime, html as htmllib, re, urllib.parse, random, string
import httpx
import asyncpg
from aiohttp import web
from aiogram import Bot, Dispatcher, html, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import Message, BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiocryptopay import AioCryptoPay, Networks

# ── НАСТРОЙКИ ИЗ ENV ──
TOKEN = os.environ.get("TG_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
BASE = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8080").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE}{WEBHOOK_PATH}"

TERMUX_API = os.environ.get("API_URL", "").rstrip("/")
API_KEY = os.environ.get("API_KEY", "test_key_123")
CRYPTO_TOKEN = os.environ.get("CRYPTO_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "5021557806"))

if not TOKEN:
    raise ValueError("❌ Переменная TG_TOKEN не задана!")
if not DATABASE_URL:
    raise ValueError("❌ Переменная DATABASE_URL не задана!")

dp = Dispatcher()
USER_STATES = {}
bot: Bot = None
DB_POOL: asyncpg.Pool = None
DAILY_LIMIT = 3

# ═══════════════════════════════════════════════════════════════════
# БАЗА (PostgreSQL)
# ═══════════════════════════════════════════════════════════════════

def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    if ".render.com" in dsn and "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
    return dsn

async def db_init():
    global DB_POOL
    DB_POOL = await asyncpg.create_pool(
        dsn=_normalize_dsn(DATABASE_URL),
        min_size=1,
        max_size=10,
        command_timeout=60,
    )
    async with DB_POOL.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                balance DOUBLE PRECISION DEFAULT 0,
                api_key TEXT,
                key_expires TEXT,
                reg_date TEXT,
                daily_requests INTEGER DEFAULT 0,
                last_request_date TEXT,
                bonus_requests INTEGER DEFAULT 0,
                referrer_id BIGINT DEFAULT NULL
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                bonus_requests INTEGER,
                created_at TEXT
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_promocodes (
                user_id BIGINT,
                code TEXT,
                used_at TEXT,
                PRIMARY KEY (user_id, code)
            )
        ''')
    logging.info("✅ DB pool + схема готовы")

async def get_user(user_id: int):
    async with DB_POOL.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT balance, api_key, key_expires, reg_date, daily_requests, "
            "last_request_date, bonus_requests, referrer_id FROM users WHERE user_id=$1",
            user_id,
        )
        if row is None:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await conn.execute(
                "INSERT INTO users (user_id, balance, reg_date, daily_requests, bonus_requests) "
                "VALUES ($1, 0, $2, 0, 0) ON CONFLICT (user_id) DO NOTHING",
                user_id, now_str,
            )
            row = await conn.fetchrow(
                "SELECT balance, api_key, key_expires, reg_date, daily_requests, "
                "last_request_date, bonus_requests, referrer_id FROM users WHERE user_id=$1",
                user_id,
            )
        return row

async def update_user(user_id: int, balance=None, api_key=None, key_expires=None,
                      daily_requests=None, last_request_date=None,
                      bonus_requests=None, referrer_id=None):
    sets, values, idx = [], [], 1
    if balance is not None:           sets.append(f"balance=${idx}");           values.append(balance);           idx += 1
    if api_key is not None:           sets.append(f"api_key=${idx}");           values.append(api_key);           idx += 1
    if key_expires is not None:       sets.append(f"key_expires=${idx}");       values.append(key_expires);       idx += 1
    if daily_requests is not None:    sets.append(f"daily_requests=${idx}");    values.append(daily_requests);    idx += 1
    if last_request_date is not None: sets.append(f"last_request_date=${idx}"); values.append(last_request_date); idx += 1
    if bonus_requests is not None:    sets.append(f"bonus_requests=${idx}");    values.append(bonus_requests);    idx += 1
    if referrer_id is not None:       sets.append(f"referrer_id=${idx}");       values.append(referrer_id);       idx += 1
    if not sets:
        return
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(sets)} WHERE user_id=${idx}"
    async with DB_POOL.acquire() as conn:
        await conn.execute(query, *values)

def generate_key():
    return "Definitelysearch_" + ''.join(random.choices(string.ascii_letters + string.digits, k=24))


# ═══════════════════════════════════════════════════════════════════
# HTML ШАБЛОН
# ═══════════════════════════════════════════════════════════════════
REPORT_HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Definitelysearch — __QUERY__</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#000000;--card:#0a0a0a;--card-hover:#111111;--border:#1a1a1a;--border-hi:#333333;--text:#ffffff;--muted:#888888;--accent:#22d3ee;}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body {font-family:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;background:#000;color:var(--text);min-height:100vh;padding:56px 24px 48px;position:relative;-webkit-font-smoothing:antialiased;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none;}
.wrap{max-width:1080px;margin:0 auto;position:relative;z-index:1}
.field-val,.stat-value{user-select:none;-webkit-user-select:none;-webkit-touch-callout:none;cursor:pointer;display:inline-flex;align-items:center;gap:8px;transition:all 0.2s;}
.copy-icon{opacity:0;transform:translateX(-4px);transition:all 0.2s ease;color:var(--muted);flex-shrink:0;}
.field:hover .copy-icon,.stat:hover .copy-icon{opacity:0.6;transform:translateX(0);}
.field:hover .field-val.accent .copy-icon{color:var(--accent);}
.field-val:active,.stat-value:active{opacity:0.6;}
.map-link{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:8px;background:rgba(34,211,238,0.12);border:1px solid rgba(34,211,238,0.35);margin-left:8px;color:var(--accent);text-decoration:none;transition:all 0.25s ease;vertical-align:middle;flex-shrink:0;}
.map-link:hover{background:rgba(34,211,238,0.3);border-color:var(--accent);transform:scale(1.15);box-shadow:0 0 12px rgba(34,211,238,0.4);}
.map-link svg{width:14px;height:14px;display:block;}
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
@media(max-width:640px){body{padding:32px 16px 48px}.field{grid-template-columns:1fr;gap:6px;padding:12px 0}.field-key{font-size:12px}.stats{grid-template-columns:1fr 1fr;gap:12px}.stat{padding:20px 16px}.card-head{padding:16px 18px}.card-body{padding:8px 18px}}
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
document.querySelectorAll('.field-val, .stat-value').forEach(el => {
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

# Словарь переводов
FIELD_MAP = {
    'fio':'ФИО','name':'ФИО','surname':'Фамилия','firstname':'Имя','middlename':'Отчество','patronymic':'Отчество',
    'bdate':'Дата рождения','birthday':'ДР','dob':'Дата рождения','birthdate':'Дата рождения',
    'phone':'Телефон','email':'Email','address':'Адрес','city':'Город','street':'Улица',
    'inn':'ИНН','snils':'СНИЛС','passport_series':'Паспорт','passport':'Паспорт', 'pass':'Паспорт',
    'issued_by':'Кем выдан','issue_date':'Дата выдачи','passport_date':'Дата выдачи',
    'passport_issuer':'Кем выдан','gender':'Пол','citizenship':'Гражданство', 'polis':'Полис', 'policy':'Полис',
    'tg_id':'TG ID','id':'ID','tags':'Метки','card_type':'Карта','amount':'Сумма','sum':'Сумма заказа',
    'country':'Страна','bank':'Банк','source':'Источник','card_mask':'Маска карты','card_bank':'Банк карты',
    'fullname':'ФИО', 'region':'Регион', 'type':'Тип', 'rank':'Звание', 'age':'Возраст',
    'death':'Дата смерти', 'locationName':'Населенный пункт', 'password':'Пароль',
    'salary':'Зарплата', 'profession':'Профессия', 'comment':'Комментарий', 'created_at':'Дата регистрации', 'price':'Сумма',
    'school':'Школа', 'class_num':'Класс', 'class_letter':'Литера', 'gosnomer':'Госномер', 'work':'Работа',
    'organization':'Организация', 'diagnosis':'Диагноз', 'actual_address':'Фактический адрес',
    'skype':'Skype', 'pin':'PIN-код', 'login':'Логин', 'payment_sum':'Сумма оплат', 'last_visit':'Последний визит',
    'status':'Статус', 'user_id':'ID клиента', 'ip':'IP-адрес', 'order_date':'Дата заказа',
    'order_text':'Текст заказа', 'date':'Дата', 'bonus_card':'Бонусная карта', 'user_agent':'Устройство',
    'vk_url': 'VK Ссылка', 'department': 'Отдел', 'score': 'Баллы', 'position': 'Должность',
    'company': 'Компания', 'operator': 'Оператор', 'provider': 'Провайдер'
}

# Огромный словарь иконок
ICONS = {
    "телефон": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    "фио": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "фамилия": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    "отчество": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg>',
    "инн": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "снилс": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><rect x="6" y="13" width="4" height="3" rx="1"/><line x1="14" y1="15" x2="18" y2="15"/></svg>',
    "паспорт": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="9" r="3"/><path d="M8 17h8"/></svg>',
    "адрес": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "город": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "дата": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
    "др": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
    "email": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/></svg>',
    "tg id": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>',
    "пол": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>',
    "оператор": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg>',
    "регион": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "страна": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "маска карты": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>',
    "банк": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M3 10h18M3 7l9-4 9 4M3 10v11M21 10v11"/></svg>',
    "сумма": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>',
    "координаты": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/></svg>',
    "профессия": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "должность": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "работа": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "зарплата": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
    "пароль": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>',
    "логин": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg>',
    "пин-код": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>',
    "устройство": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>',
    "ip-адрес": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
    "ссылка": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>',
    "госномер": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"></path><circle cx="7" cy="17" r="2"></circle><path d="M9 17h6"></path><circle cx="17" cy="17" r="2"></circle></svg>',
    "школа": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>',
    "диагноз": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>',
    "компания": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "организация": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
}

COPY_SVG = '<svg class="copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'

def icon_for(key):
    k = str(key).lower()
    for kk, svg in ICONS.items():
        if kk in k: return svg
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'

def build_html(q, hits, elapsed_ms):
    def clean_surrogates(text):
        if not isinstance(text, str): return text
        return text.encode('utf-8', errors='replace').decode('utf-8')

    hits.sort(key=lambda x: 0 if "dadata" in str(x.get("source", "")).lower() else 1)
    sources = len(set(h.get("source", "") for h in hits))
    cards = []
    
    for i, h in enumerate(hits, 1):
        raw_src = str(h.get("source", "?"))
        clean_src = raw_src.split('.')[-1] if '.' in raw_src else raw_src
        src = htmllib.escape(clean_surrogates(clean_src))
        
        fields = []
        for k, v in h.items():
            if str(k).lower() == "source" or v in (None, "", "-"): continue
            
            k_ru = FIELD_MAP.get(str(k).lower(), str(k))
            
            if str(k).lower() in ('телефон', 'phone') and "dadata" in raw_src.lower(): continue
            
            if str(k_ru).lower() == 'оператор':
                v_str = str(v)
                v_str = re.sub(r'^(ПАО|ООО|АО|ЗАО|ОАО|АНО)\s+', '', v_str, flags=re.IGNORECASE)
                for ch in ['"', '«', '»', "'", '`']: v_str = v_str.replace(ch, '')
                v = v_str.strip()

            k_esc = htmllib.escape(clean_surrogates(str(k_ru)))
            svg = icon_for(k_ru)
            v_esc = htmllib.escape(clean_surrogates(str(v)))
            
            accent = ' accent' if str(k_ru).lower() in ('телефон', 'инн', 'снилс', 'паспорт', 'tg id') else ''
            
            map_link = ''
            if str(k_ru).lower() in ('адрес', 'город') and len(v_esc) > 5:
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


# ═══════════════════════════════════════════════════════════════════
# ПРОКСИ ДЛЯ API
# ═══════════════════════════════════════════════════════════════════
async def proxy_api(request):
    if not TERMUX_API:
        return web.json_response({"success": False, "error": "Termux API not connected"}, status=503)
    path = request.match_info['path']
    query = request.query_string
    target = f"{TERMUX_API}/api/v1/{path}"
    if query: target += f"?{query}"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.get(target)
            return web.Response(body=r.content, status=r.status_code, content_type=r.headers.get("content-type", "application/json"))
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=502)

async def set_api_url(request):
    global TERMUX_API
    secret = request.query.get("secret", "")
    new_url = request.query.get("url", "").rstrip("/")
    if secret != "Definitelysearch_secret_2026":
        return web.json_response({"error": "Invalid secret"}, status=403)
    if not new_url:
        return web.json_response({"error": "url required"}, status=400)
    TERMUX_API = new_url
    logging.info(f"TERMUX_API updated to: {TERMUX_API}")
    return web.json_response({"success": True, "termux_api": TERMUX_API})


# ═══════════════════════════════════════════════════════════════════
# КЛАВИАТУРЫ И ОБРАБОТЧИКИ
# ═══════════════════════════════════════════════════════════════════
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Искать", callback_data="search_menu"), InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Реферальная система", callback_data="ref_system"), InlineKeyboardButton(text="🤖 ЧАО", callback_data="chaos")],
        [InlineKeyboardButton(text="⚙️ API - ключ", callback_data="api_menu")]
    ])

def get_search_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Номер телефона", callback_data="set_search_phone"), InlineKeyboardButton(text="✈️ Telegram", callback_data="set_search_tg")],
        [InlineKeyboardButton(text="🔙 Вернуться назад", callback_data="back")]
    ])

# ── АДМИН ПАНЕЛЬ ──
@dp.message(Command("admin"))
async def cmd_admin(m: Message):
    if m.from_user.id != ADMIN_ID: return
    async with DB_POOL.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_keys = await conn.fetchval("SELECT COUNT(*) FROM users WHERE api_key IS NOT NULL")
    text = (
        "👑 <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"🔑 Выдано ключей: <b>{total_keys}</b>\n\n"
        "Выберите действие:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Выдать ключ вручную", callback_data="admin_gen_key")],
        [InlineKeyboardButton(text="🎟 Создать промокод", callback_data="admin_promo")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Закрыть", callback_data="back")]
    ])
    await m.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "admin_gen_key")
async def admin_gen_key(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    USER_STATES[cb.from_user.id] = "admin_waiting_key"
    await cb.message.edit_text("🔑 <b>Выдача ключа</b>\n\nОтправь мне ID пользователя и количество дней через пробел (например: <code>123456789 30</code>).", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="back")]]))
    await cb.answer()

@dp.callback_query(F.data == "admin_promo")
async def admin_promo(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    USER_STATES[cb.from_user.id] = "admin_waiting_promo"
    await cb.message.edit_text("🎟 <b>Создание промокода</b>\n\nОтправь мне данные в формате:\n<code>КОД КОЛИЧЕСТВО_АКТИВАЦИЙ БОНУСНЫЕ_ЗАПРОСЫ</code>\n\n<b>Пример:</b> <code>SALE 100 5</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="back")]]))
    await cb.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    USER_STATES[cb.from_user.id] = "admin_waiting_broadcast"
    await cb.message.edit_text("📢 <b>Рассылка</b>\n\nОтправь мне текст, который нужно разослать всем пользователям.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="back")]]))
    await cb.answer()

# ── ПРОФИЛЬ И ПРОМОКОДЫ ──
@dp.callback_query(F.data == "profile")
async def show_profile(cb: CallbackQuery):
    user_id = cb.from_user.id
    username = f"@{cb.from_user.username}" if cb.from_user.username else "Нет"
    row = await get_user(user_id)
    balance, api_key, key_expires, reg_date, daily_requests, last_req, bonus, _ = row
    try:
        reg_dt = datetime.datetime.strptime(reg_date, "%Y-%m-%d %H:%M:%S")
        days_in_system = (datetime.datetime.now() - reg_dt).days + 1
        reg_date_str = reg_dt.strftime("%d.%m.%Y")
    except Exception:
        days_in_system = 1; reg_date_str = "Неизвестно"
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if last_req != today:
        daily_requests = 0
        await update_user(user_id, daily_requests=0, last_request_date=today)
    left_requests = max(0, DAILY_LIMIT - daily_requests)
    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"<blockquote>"
        f"• ID: <code>{user_id}</code>\n"
        f"• Юзернейм: {username}\n"
        f"• В системе с: {reg_date_str} ({days_in_system} дн.)\n"
        f"• Запросов сегодня: {left_requests}/{DAILY_LIMIT}\n"
        f"• Бонусных запросов: {bonus}"
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="activate_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await cb.message.edit_text(profile_text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "activate_promo")
async def activate_promo_menu(cb: CallbackQuery):
    USER_STATES[cb.from_user.id] = "user_waiting_promo"
    await cb.message.edit_text("🎟 <b>Активация промокода</b>\n\nОтправь мне промокод в ответном сообщении.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="back")]]))
    await cb.answer()

# ── СТАРТ ──
@dp.message(CommandStart(deep_link=True))
async def start_ref(m: Message, command: CommandObject):
    args = command.args
    if args and args.startswith("ref_"):
        try: referrer_id = int(args.replace("ref_", ""))
        except ValueError: return await cmd_start(m)
        if referrer_id != m.from_user.id:
            row = await get_user(m.from_user.id)
            existing_ref = row["referrer_id"]
            if not existing_ref:
                await update_user(m.from_user.id, referrer_id=referrer_id)
                ref_row = await get_user(referrer_id)
                ref_bonus = ref_row["bonus_requests"]
                await update_user(referrer_id, bonus_requests=(ref_bonus or 0) + 1)
                try:
                    if bot: await bot.send_message(referrer_id, "🎉 <b>По вашей ссылке зарегистрировался новый пользователь!</b>\n\nВам начислен <b>+1 бонусный запрос</b>.", parse_mode="HTML")
                except Exception: pass
    await cmd_start(m)

@dp.message(CommandStart())
async def cmd_start(m: Message):
    await get_user(m.from_user.id)
    await m.answer("👋 <b>Добро пожаловать в поисковик — бесплатный поиск по данным</b>\n\n👇 <b>Вы находитесь в меню, выберите нужную кнопку</b>", parse_mode="HTML", reply_markup=get_main_menu())

@dp.callback_query(F.data == "back")
async def back_to_menu(cb: CallbackQuery):
    USER_STATES.pop(cb.from_user.id, None)
    await cb.message.edit_text("👋 <b>Добро пожаловать в поисковик — бесплатный поиск по данным</b>\n\n👇 <b>Вы находитесь в меню, выберите нужную кнопку</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await cb.answer()

@dp.callback_query(F.data == "search_menu")
async def show_search_menu(cb: CallbackQuery):
    await cb.message.edit_text("👇 <b>Выберите нужный сервис</b>", parse_mode="HTML", reply_markup=get_search_menu())
    await cb.answer()

@dp.callback_query(F.data.startswith("set_search_"))
async def set_search_type(cb: CallbackQuery):
    search_type = cb.data.replace("set_search_", "")
    USER_STATES[cb.from_user.id] = search_type
    if search_type == "phone":
        text = "📞 <b>Введите номер телефона</b>\n\n<b>Пример:</b>\n– <code>79033295223</code>\n– <code>+79033295223</code>"
    elif search_type == "tg":
        text = "✈️ <b>Введите Telegram ID или Username</b>\n\n<b>Пример:</b>\n– <code>123456789</code>\n– <code>@username</code>"
    else:
        text = "Введите запрос для поиска:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="back")]])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "ref_system")
async def show_ref_system(cb: CallbackQuery):
    user_id = cb.from_user.id
    row = await get_user(user_id)
    bonus_requests = row["bonus_requests"]
    async with DB_POOL.acquire() as conn:
        invited = await conn.fetchval("SELECT COUNT(*) FROM users WHERE referrer_id=$1", user_id)
    link = f"https://t.me/Kdkdkdldkdkbot?start=ref_{user_id}"
    text = (
        "🎁 <b>Реферальная система</b>\n\n"
        "Приглашайте друзей и получайте <b>+1 запрос</b> за каждого.\nБонус начисляется мгновенно.\n\n"
        f"<b>Ваша ссылка:</b>\n<code>{link}</code>\n\n"
        f"👥 Вы пригласили: <b>{invited}</b>\n"
        f"✨ Бонусных запросов: <b>{bonus_requests}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "chaos")
async def show_chaos(cb: CallbackQuery):
    await cb.answer("🤖 Раздел в разработке...", show_alert=True)

@dp.callback_query(F.data == "api_menu")
async def show_api_menu(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="7 дн. — $7.50", callback_data="buy_7")],
        [InlineKeyboardButton(text="30 дн. — $10.60", callback_data="buy_30")],
        [InlineKeyboardButton(text="365 дн. — $15.50", callback_data="buy_365")],
        [InlineKeyboardButton(text="⚙️ Мой API - ключ", callback_data="my_api_key")],
        [InlineKeyboardButton(text="📄 Документация", url="https://definitelysearch-api.onrender.com")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await cb.message.edit_text("⚙️ <b>API - ключ Definitelysearch</b>\n\nПолучите доступ к нашему API для автоматизации поиска.\n\n<b>Тарифы:</b>\n• 7 дн. — $7.50\n• 30 дн. — $10.60\n• 365 дн. — $15.50\n\n<i>После оплаты ключ будет сгенерирован автоматически.</i>", parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "my_api_key")
async def show_my_api_key(cb: CallbackQuery):
    user_id = cb.from_user.id
    row = await get_user(user_id)
    api_key = row["api_key"]; key_expires = row["key_expires"]
    if not api_key:
        text = "⚙️ <b>Мой API - ключ</b>\n\nУ вас пока нет API-ключа. Приобретите его в разделе тарифов."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Купить ключ", callback_data="api_menu")]])
    else:
        text = f"⚙️ <b>Мой API - ключ</b>\n\n🔑 <b>Ваш ключ:</b>\n<code>{api_key}</code>\n\n📅 <b>Действует до:</b> {key_expires}\n\n<i>Используйте его в заголовке <code>X-API-Key</code> или в параметре <code>?key=</code>.</i>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

# ── ОПЛАТА ──
@dp.callback_query(F.data.startswith("buy_"))
async def buy_key(cb: CallbackQuery):
    if not CRYPTO_TOKEN: return await cb.answer("❌ Оплата временно недоступна.", show_alert=True)
    days = int(cb.data.split("_")[1])
    user_id = cb.from_user.id
    prices = {7: 1, 30: 3, 365: 10}
    amount = prices[days]
    crypto_client = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)
    try:
        invoice = await crypto_client.create_invoice(asset="USDT", amount=amount, description=f"API Key {days} days", payload=f"{user_id}:{days}")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить {amount} USDT", url=invoice.bot_invoice_url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_pay_{invoice.invoice_id}")]
        ])
        await cb.message.edit_text(f"💳 <b>Счет на оплату</b>\n\nТариф: <b>{days} дней</b>\nСумма: <b>{amount} USDT</b>\n\nНажмите «Оплатить», чтобы перейти в @send.\nПосле оплаты нажмите «Я оплатил».", parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        await cb.answer(f"Ошибка создания счета: {e}", show_alert=True)
    finally:
        await crypto_client.close()
    await cb.answer()

@dp.callback_query(F.data.startswith("check_pay_"))
async def check_payment(cb: CallbackQuery):
    if not CRYPTO_TOKEN: return await cb.answer("❌ Оплата недоступна.", show_alert=True)
    invoice_id = int(cb.data.replace("check_pay_", ""))
    crypto_client = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)
    try:
        result = await crypto_client.get_invoices(invoice_ids=invoice_id)
        invoice = result[0] if isinstance(result, list) and result else (None if isinstance(result, list) else result)
        if invoice and invoice.status == "paid":
            payload = invoice.payload
            if payload and ":" in payload:
                user_id, days = payload.split(":")
                days = int(days)
            else:
                user_id = cb.from_user.id; days = 30
            key = generate_key()
            expires = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            await update_user(int(user_id), api_key=key, key_expires=expires)
            await cb.message.edit_text(f"✅ <b>Оплата получена!</b>\n\nВаш API-ключ:\n<code>{key}</code>\n\nДействует до: {expires}", parse_mode="HTML")
        else:
            await cb.answer("Счет еще не оплачен или не найден.", show_alert=True)
    except Exception as e:
        await cb.answer(f"Ошибка проверки: {e}", show_alert=True)
    finally:
        await crypto_client.close()

# ═══════════════════════════════════════════════════════════════════
# ГЛАВНЫЙ ОБРАБОТЧИК
# ═══════════════════════════════════════════════════════════════════
@dp.message()
async def handle(m: Message):
    q = (m.text or "").strip()
    user_id = m.from_user.id
    state = USER_STATES.get(user_id)

    if user_id == ADMIN_ID and state:
        if state == "admin_waiting_key":
            try:
                target_id, days_str = q.split()
                days = int(days_str)
                key = generate_key()
                expires = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
                await update_user(int(target_id), api_key=key, key_expires=expires)
                await m.answer(f"✅ Ключ выдан юзеру <code>{target_id}</code> на {days} дней:\n<code>{key}</code>", parse_mode="HTML")
                try:
                    if bot: await bot.send_message(int(target_id), f"🎁 <b>Вам выдан API-ключ!</b>\n\n<code>{key}</code>\n\nДействует до: {expires}", parse_mode="HTML")
                except Exception: pass
            except Exception:
                await m.answer("❌ Ошибка формата. Напиши: <code>123456789 30</code>", parse_mode="HTML")
            USER_STATES.pop(user_id, None)
            return

        elif state == "admin_waiting_promo":
            try:
                code, uses_str, bonus_str = q.split()
                uses = int(uses_str)
                bonus = int(bonus_str)
                async with DB_POOL.acquire() as conn:
                    await conn.execute("INSERT INTO promocodes (code, max_uses, used_count, bonus_requests, created_at) VALUES ($1, $2, 0, $3, $4)", code, uses, bonus, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                await m.answer(f"✅ Промокод <code>{code}</code> создан!\n\nАктиваций: {uses}\nБонусных запросов: {bonus}", parse_mode="HTML")
            except Exception as e:
                await m.answer(f"❌ Ошибка формата. Напиши: <code>SALE 100 5</code>\n\nОшибка: {e}", parse_mode="HTML")
            USER_STATES.pop(user_id, None)
            return

        elif state == "admin_waiting_broadcast":
            await m.answer("🚀 Начинаю рассылку...", parse_mode="HTML")
            async with DB_POOL.acquire() as conn:
                rows = await conn.fetch("SELECT user_id FROM users")
            users = [r["user_id"] for r in rows]
            success = 0
            for u in users:
                try:
                    if bot:
                        await bot.send_message(u, q, parse_mode="HTML")
                        success += 1
                        await asyncio.sleep(0.05)
                except Exception: pass
            await m.answer(f"✅ Рассылка завершена. Доставлено {success} из {len(users)}.")
            USER_STATES.pop(user_id, None)
            return

    if state == "user_waiting_promo":
        code = q.upper()
        message_text = None
        bonus_granted = 0
        try:
            async with DB_POOL.acquire() as conn:
                async with conn.transaction():
                    promo = await conn.fetchrow("SELECT max_uses, used_count, bonus_requests FROM promocodes WHERE code=$1", code)
                    if not promo:
                        message_text = "❌ Такого промокода не существует."
                    elif promo["used_count"] >= promo["max_uses"]:
                        message_text = "❌ У этого промокода закончились активации."
                    else:
                        existing = await conn.fetchrow("SELECT 1 FROM user_promocodes WHERE user_id=$1 AND code=$2", user_id, code)
                        if existing:
                            message_text = "❌ Вы уже активировали этот промокод."
                        else:
                            await conn.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=$1", code)
                            await conn.execute("INSERT INTO user_promocodes (user_id, code, used_at) VALUES ($1, $2, $3)", user_id, code, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            bonus_granted = promo["bonus_requests"]
        except Exception as e:
            message_text = f"❌ Ошибка активации: {e}"

        if bonus_granted > 0:
            row = await get_user(user_id)
            current_bonus = row["bonus_requests"] or 0
            await update_user(user_id, bonus_requests=current_bonus + bonus_granted)
            await m.answer(f"✅ Промокод активирован!\n\nВам начислено <b>+{bonus_granted}</b> бонусных запросов.", parse_mode="HTML")
        else:
            await m.answer(message_text or "❌ Не удалось активировать промокод.")
        USER_STATES.pop(user_id, None)
        return

    # ═══════════════════════════════════════════════════════════════
    # ЗАЩИТА: Если не выбрана кнопка "Искать" -> игнорируем ввод
    # ═══════════════════════════════════════════════════════════════
    if state not in ("phone", "tg"):
        return

    # ── ОБЫЧНЫЙ ПОИСК ──
    if len(q) < 3:
        return await m.answer("слишком короткий запрос (минимум 3 символа)")
    if not TERMUX_API:
        return await m.answer("❌ API временно недоступен (Termux не подключен).")

    row = await get_user(user_id)
    balance, api_key, key_expires, reg_date, daily_requests, last_req, bonus, _ = row
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if last_req != today: daily_requests = 0

    use_bonus = False
    if bonus and bonus > 0: use_bonus = True
    elif daily_requests >= DAILY_LIMIT:
        return await m.answer(f"🚫 <b>Лимит запросов исчерпан</b>\n\nВы сделали {DAILY_LIMIT} запроса сегодня. Лимит обновится завтра.\n\n<i>Пригласите друга в разделе «Реферальная система» или активируйте промокод.</i>", parse_mode="HTML")

    msg = await m.answer("🔍 Поиск...")
    t0 = time.time()

    try:
        async with httpx.AsyncClient(timeout=120) as c:
            search_type = "tg" if state == "tg" else "phone"
            r = await c.get(f"{TERMUX_API}/api/v1/search", params={"q": q, "type": search_type, "key": API_KEY})
            data = r.json()
    except Exception as e:
        return await msg.edit_text(f"API недоступен: <code>{html.quote(str(e))}</code>", parse_mode="HTML")

    if not data.get("success"):
        return await msg.edit_text(f"Ошибка API: {data.get('error')}", parse_mode="HTML")

    hits = data.get("data", [])
    elapsed = int((time.time() - t0) * 1000)

    if not hits:
        return await msg.edit_text(f"<code>{html.quote(q)}</code>\n\n✗ не найдено", parse_mode="HTML")

    if use_bonus:
        await update_user(user_id, bonus_requests=bonus - 1, last_request_date=today)
    else:
        await update_user(user_id, daily_requests=daily_requests + 1, last_request_date=today)

    USER_STATES.pop(user_id, None)

    try: await msg.delete()
    except: pass

    html_content = build_html(q, hits, elapsed)
    safe_q = q.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"Definitelysearch_{safe_q}.html"
    html_bytes = html_content.encode("utf-8", errors="replace")

    if use_bonus:
        left_info = f"🎁 Потрачен бонусный запрос (осталось: {bonus - 1})"
    else:
        left_info = f"Осталось попыток: {max(0, DAILY_LIMIT - (daily_requests + 1))}/{DAILY_LIMIT}"

    await m.answer_document(BufferedInputFile(html_bytes, filename=filename), caption=f"📄 Отчет: {q} ({len(hits)} записей)\n<i>{left_info}</i>", parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════════════════
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"webhook set: {WEBHOOK_URL}")

async def on_shutdown():
    if DB_POOL:
        await DB_POOL.close()
        logging.info("DB pool closed")

async def main():
    global bot
    logging.basicConfig(level=logging.INFO)
    await db_init()
    bot = Bot(token=TOKEN)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    app.router.add_get("/api/v1/{path:.*}", proxy_api)
    app.router.add_get("/set-api-url", set_api_url)
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
