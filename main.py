"""Arabic Telegram Casino Bot — Texas4Win Agent Panel Full Automation
Cloudflare Bypass via Thordata Web Unlocker + curl_cffi fallback.
"""
import os
import json
import logging
import re
import threading
import asyncio
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlencode

from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# curl_cffi for advanced browser emulation
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except Exception:
    CURL_CFFI_AVAILABLE = False
    curl_requests = None

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
API_SECRET = os.environ.get('API_SECRET', 'default_secret')
THORDATA_TOKEN = os.environ.get('THORDATA_TOKEN', '')
RESIDENTIAL_PROXY = os.environ.get('RESIDENTIAL_PROXY', '')

# Texas4Win Panel Settings
T4W_DOMAIN = os.environ.get('T4W_DOMAIN', 'https://agents.texas4win.com')
T4W_LOGIN_ENDPOINT = os.environ.get('T4W_LOGIN_ENDPOINT', '/api/auth/login')
T4W_CREATE_ENDPOINT = os.environ.get('T4W_CREATE_ENDPOINT', '/api/player/create')
T4W_DEPOSIT_ENDPOINT = os.environ.get('T4W_DEPOSIT_ENDPOINT', '/api/finance/deposit')
T4W_WITHDRAW_ENDPOINT = os.environ.get('T4W_WITHDRAW_ENDPOINT', '/api/finance/withdraw')
T4W_BALANCE_ENDPOINT = os.environ.get('T4W_BALANCE_ENDPOINT', '/api/player/balance')

# Agent credentials (to login to Texas4win panel)
T4W_AGENT_USERNAME = os.environ.get('T4W_AGENT_USERNAME', '')
T4W_AGENT_PASSWORD = os.environ.get('T4W_AGENT_PASSWORD', '')

THORDATA_ENDPOINT = 'https://webunlocker.thordata.com/request'
USER_DB_PATH = os.environ.get('USER_DB_PATH', '/tmp/texas4win_bot.db')

if not TELEGRAM_BOT_TOKEN:
    logger.warning('⚠️ TELEGRAM_BOT_TOKEN not set!')

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
CLEAN_RE = re.compile(r'<[^>]+>')


def safe_json_load(text):
    if not text or not isinstance(text, str):
        return None
    text = CLEAN_RE.sub('', text)
    text = text.replace('\x00', '').replace('\x0b', '').replace('\x0c', '').strip()
    if text.startswith('"') and text.endswith('"'):
        try:
            text = json.loads(text)
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        for start_char in ('{', '['):
            idx = text.find(start_char)
            if idx != -1:
                try:
                    return json.loads(text[idx:])
                except Exception:
                    pass
    return None


def _proxy_for():
    if not RESIDENTIAL_PROXY:
        return None
    if '://' not in RESIDENTIAL_PROXY:
        return {'http': f'http://{RESIDENTIAL_PROXY}', 'https': f'http://{RESIDENTIAL_PROXY}'}
    parsed = __import__('urllib.parse').parse.urlparse(RESIDENTIAL_PROXY)
    if parsed.scheme in ('socks5', 'socks5h', 'socks4', 'socks4a'):
        return {'http': RESIDENTIAL_PROXY, 'https': RESIDENTIAL_PROXY}
    return {'http': RESIDENTIAL_PROXY, 'https': RESIDENTIAL_PROXY}


def _thordata_unlocker(method, url, json_data=None, extra_headers=None, timeout=30):
    """Send any HTTP request through Thordata Web Unlocker."""
    form_data = {
        'url': url,
        'type': 'json',
        'method': method.upper(),
    }
    if json_data is not None:
        form_data['body'] = json.dumps(json_data)
    if extra_headers:
        form_data['headers'] = json.dumps(extra_headers)

    headers = {
        'Authorization': f'Bearer {THORDATA_TOKEN}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    logger.info('🔥 Thordata [%s] %s', method.upper(), url)
    resp = requests.post(
        THORDATA_ENDPOINT,
        data=urlencode(form_data),
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp


class ApiResponse:
    def __init__(self, raw_resp):
        self._raw = raw_resp
        self.status_code = raw_resp.status_code
        self.text = getattr(raw_resp, 'text', '')
        self.content = getattr(raw_resp, 'content', b'')
        self.headers = getattr(raw_resp, 'headers', {})

    @property
    def json(self):
        data = safe_json_load(self.text)
        if data is not None:
            return data
        raise ValueError(
            f'Response is not JSON. Status: {self.status_code}, Body: {self.text[:300]}'
        )

    def __repr__(self):
        return f'<ApiResponse [{self.status_code}]>'


def api_request(method, endpoint, **kwargs):
    """Make API request with Cloudflare bypass (Thordata → curl_cffi → requests)."""
    url = f'{T4W_DOMAIN}{endpoint}'
    timeout = kwargs.get('timeout', 30)
    json_data = kwargs.get('json')
    extra_headers = kwargs.get('headers', {})

    # 1) Try Thordata Web Unlocker (supports ALL methods now)
    if THORDATA_TOKEN:
        try:
            raw = _thordata_unlocker(
                method, url, json_data=json_data, extra_headers=extra_headers, timeout=timeout
            )
            return ApiResponse(raw)
        except Exception as e:
            logger.warning('Thordata bypass failed: %s', e)

    # 2) Fallback: curl_cffi with proxy
    try:
        proxy = _proxy_for()
        if CURL_CFFI_AVAILABLE:
            try:
                proxy_url = proxy.get('https') or proxy.get('http') if proxy else None
                raw = curl_requests.request(
                    method, url,
                    json=json_data,
                    headers=extra_headers,
                    proxy=proxy_url,
                    timeout=timeout,
                )
                raw.raise_for_status()
                return ApiResponse(raw)
            except Exception as curl_err:
                logger.warning('curl_cffi failed: %s, falling back to requests', curl_err)

        raw = requests.request(
            method, url,
            json=json_data,
            headers=extra_headers,
            proxies=proxy,
            timeout=timeout,
        )
        raw.raise_for_status()
        return ApiResponse(raw)
    except Exception as e:
        logger.error('All bypass methods failed for %s: %s', url, e)
        raise


# ═══════════════════════════════════════════════════════════════
# Database Layer (SQLite)
# ═══════════════════════════════════════════════════════════════
class UserDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id TEXT PRIMARY KEY,
                t4w_username TEXT,
                t4w_password TEXT,
                balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def link_account(self, telegram_id, t4w_username, t4w_password=None):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            'INSERT OR REPLACE INTO users (telegram_id, t4w_username, t4w_password) VALUES (?, ?, ?)',
            (str(telegram_id), t4w_username, t4w_password)
        )
        conn.commit()
        conn.close()

    def get_user(self, telegram_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            'SELECT t4w_username, t4w_password, balance FROM users WHERE telegram_id = ?',
            (str(telegram_id),)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'username': row[0], 'password': row[1], 'balance': row[2]}
        return None

    def get_username(self, telegram_id):
        user = self.get_user(telegram_id)
        return user['username'] if user else None

    def update_balance(self, telegram_id, amount):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            'UPDATE users SET balance = balance + ? WHERE telegram_id = ?',
            (amount, str(telegram_id))
        )
        conn.commit()
        conn.close()

    def set_config(self, key, value):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()

    def get_config(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT value FROM config WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None


user_db = UserDB(USER_DB_PATH)


# ═══════════════════════════════════════════════════════════════
# Texas4Win API Client
# ═══════════════════════════════════════════════════════════════
class Texas4WinClient:
    def __init__(self):
        self._token = None

    @property
    def token(self):
        if self._token is None:
            self._token = user_db.get_config('t4w_token')
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        if value:
            user_db.set_config('t4w_token', value)

    def _request(self, method, endpoint, **kwargs):
        headers = kwargs.pop('headers', {})
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return api_request(method, endpoint, headers=headers, **kwargs)

    def login(self):
        """Authenticate as agent on Texas4Win panel."""
        if not T4W_AGENT_USERNAME or not T4W_AGENT_PASSWORD:
            raise ValueError('T4W_AGENT_USERNAME and T4W_AGENT_PASSWORD env vars must be set')

        resp = self._request('POST', T4W_LOGIN_ENDPOINT, json={
            'username': T4W_AGENT_USERNAME,
            'password': T4W_AGENT_PASSWORD
        })
        data = resp.json

        # Try common token locations in response
        token = data.get('token') or data.get('access_token')
        if not token and isinstance(data.get('data'), dict):
            token = data['data'].get('token') or data['data'].get('access_token')

        if not token:
            raise ValueError(f'Login OK but no token found. Response: {json.dumps(data)[:500]}')

        self.token = token
        logger.info('✅ Texas4Win agent login successful')
        return data

    def ensure_logged_in(self):
        if not self.token:
            self.login()

    def create_player(self, username, password, phone=None):
        """Create a new player account under this agent."""
        self.ensure_logged_in()
        payload = {'username': username, 'password': password}
        if phone:
            payload['phone'] = phone
        resp = self._request('POST', T4W_CREATE_ENDPOINT, json=payload)
        return resp.json

    def deposit(self, username, amount):
        """Deposit money into a player's account."""
        self.ensure_logged_in()
        resp = self._request('POST', T4W_DEPOSIT_ENDPOINT, json={
            'username': username,
            'amount': float(amount)
        })
        return resp.json

    def withdraw(self, username, amount):
        """Withdraw money from a player's account."""
        self.ensure_logged_in()
        resp = self._request('POST', T4W_WITHDRAW_ENDPOINT, json={
            'username': username,
            'amount': float(amount)
        })
        return resp.json

    def get_balance(self, username):
        """Get player's current balance."""
        self.ensure_logged_in()
        # Try query param first, then path param
        try:
            resp = self._request('GET', f'{T4W_BALANCE_ENDPOINT}?username={username}')
            return resp.json
        except Exception:
            resp = self._request('GET', f'{T4W_BALANCE_ENDPOINT}/{username}')
            return resp.json


t4w_client = Texas4WinClient()


# ═══════════════════════════════════════════════════════════════
# Flask App
# ═══════════════════════════════════════════════════════════════
app = Flask(__name__)


@app.route('/')
def home():
    return '✅ Texas4Win Agent Bot is online!'


@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'telegram_ready': _telegram_ready.is_set(),
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route('/deposit', methods=['POST'])
def handle_deposit():
    """External endpoint to notify bot about deposits."""
    data = request.get_json(force=True)
    if not data or data.get('secret') != API_SECRET:
        return jsonify({'error': 'Invalid secret'}), 403

    user_id = data.get('user_id')
    amount = data.get('amount')
    if not user_id or amount is None:
        return jsonify({'error': 'Missing user_id or amount'}), 400

    if not _telegram_ready.is_set():
        return jsonify({'error': 'Bot not ready'}), 503

    try:
        msg = f'✅ تم إيداع <b>${amount}</b> بنجاح! 🎉'
        future = asyncio.run_coroutine_threadsafe(
            _telegram_app.bot.send_message(
                chat_id=user_id, text=msg, parse_mode=ParseMode.HTML
            ),
            _telegram_loop
        )
        future.result(timeout=10)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error('Deposit notification error: %s', e)
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# Telegram Handlers
# ═══════════════════════════════════════════════════════════════
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    t4w_user = user_db.get_user(user.id)

    welcome = f"🎰 مرحباً {user.first_name}!\n\n"
    if t4w_user and t4w_user['username']:
        welcome += f"✅ حسابك مرتبط: <code>{t4w_user['username']}</code>\n"
        try:
            bal_data = await asyncio.to_thread(t4w_client.get_balance, t4w_user['username'])
            bal = bal_data.get('balance')
            if bal is None and isinstance(bal_data.get('data'), dict):
                bal = bal_data['data'].get('balance', 0)
            bal = bal or 0
            welcome += f"💰 الرصيد: <b>${bal}</b>\n"
        except Exception as e:
            logger.warning('Balance fetch failed: %s', e)
            welcome += "💰 الرصيد: غير متوفر\n"
    else:
        welcome += (
            "❌ لم يربط حساب Texas4win بعد\n"
            "استخدم /create لإنشاء حساب جديد\n\n"
        )

    welcome += "\n🎲 اختر إجراءً:"

    keyboard = [
        [InlineKeyboardButton('🎰 العب الآن', url='https://agents.texas4win.com')],
        [InlineKeyboardButton('💳 إيداع', callback_data='deposit')],
        [InlineKeyboardButton('💸 سحب', callback_data='withdraw')],
    ]
    await update.message.reply_text(
        welcome,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    t4w_username = user_db.get_username(user.id)

    if not t4w_username:
        await update.message.reply_text(
            "❌ لم يربط حسابك بعد.\nاستخدم: <code>/create username password</code>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        bal_data = await asyncio.to_thread(t4w_client.get_balance, t4w_username)
        bal = bal_data.get('balance')
        if bal is None and isinstance(bal_data.get('data'), dict):
            bal = bal_data['data'].get('balance', 0)
        bal = bal or 0
        await update.message.reply_text(
            f"💰 رصيد <code>{t4w_username}</code>: <b>${bal}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error('Balance error: %s', e)
        await update.message.reply_text(f"❌ تعذر جلب الرصيد: {e}")


async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "❌ الاستخدام:\n<code>/create username password</code>\n\n"
            "مثال: <code>/create player123 mypass456</code>",
            parse_mode=ParseMode.HTML
        )
        return

    username, password = args[0], args[1]

    try:
        result = await asyncio.to_thread(t4w_client.create_player, username, password)
        user_db.link_account(user.id, username, password)

        msg = (
            f"✅ تم إنشاء الحساب بنجاح!\n\n"
            f"👤 المستخدم: <code>{username}</code>\n"
            f"🔑 كلمة المرور: <code>{password}</code>\n\n"
            f"🎮 <a href='https://agents.texas4win.com'>العب الآن</a>\n\n"
            f"استخدم /deposit لإضافة رصيد."
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error('Create account error: %s', e)
        await update.message.reply_text(f"❌ فشل إنشاء الحساب: {e}")


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    t4w_username = user_db.get_username(user.id)

    if not t4w_username:
        await update.message.reply_text(
            "❌ لم يربط حسابك بعد.\nاستخدم: <code>/create username password</code>",
            parse_mode=ParseMode.HTML
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ الاستخدام: <code>/deposit 50</code>\n\nاستبدل 50 بالمبلغ المطلوب.",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        amount = float(context.args[0])
        if amount <= 0:
            raise ValueError('المبلغ يجب أن يكون أكبر من صفر')

        result = await asyncio.to_thread(t4w_client.deposit, t4w_username, amount)
        user_db.update_balance(user.id, amount)

        await update.message.reply_text(
            f"✅ تم إيداع <b>${amount}</b> إلى حساب <code>{t4w_username}</code>! 🎉",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error('Deposit error: %s', e)
        await update.message.reply_text(f"❌ فشل الإيداع: {e}")


async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    t4w_username = user_db.get_username(user.id)

    if not t4w_username:
        await update.message.reply_text(
            "❌ لم يربط حسابك بعد.\nاستخدم: <code>/create username password</code>",
            parse_mode=ParseMode.HTML
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ الاستخدام: <code>/withdraw 25</code>\n\nاستبدل 25 بالمبلغ المطلوب.",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        amount = float(context.args[0])
        if amount <= 0:
            raise ValueError('المبلغ يجب أن يكون أكبر من صفر')

        result = await asyncio.to_thread(t4w_client.withdraw, t4w_username, amount)
        user_db.update_balance(user.id, -amount)

        await update.message.reply_text(
            f"✅ تم سحب <b>${amount}</b> من حساب <code>{t4w_username}</code>! 💸",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error('Withdraw error: %s', e)
        await update.message.reply_text(f"❌ فشل السحب: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'deposit':
        await query.edit_message_text(
            "💳 لإيداع الأموال، أرسل:\n<code>/deposit 50</code>\n\n"
            "استبدل 50 بالمبلغ المطلوب.",
            parse_mode=ParseMode.HTML
        )
    elif query.data == 'withdraw':
        await query.edit_message_text(
            "💸 لسحب الأموال، أرسل:\n<code>/withdraw 25</code>\n\n"
            "استبدل 25 بالمبلغ المطلوب.",
            parse_mode=ParseMode.HTML
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎰 <b>دليل البوت</b>\n\n"
        "/start - القائمة الرئيسية\n"
        "/create username password - إنشاء حساب لاعب\n"
        "/balance - رصيد حسابك في Texas4win\n"
        "/deposit المبلغ - إيداع رصيد\n"
        "/withdraw المبلغ - سحب رصيد\n"
        "/help - المساعدة\n\n"
        "💡 <i>يجب إنشاء حساب أولاً قبل الإيداع أو السحب.</i>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════
# Background Thread for PTB Event Loop
# ═══════════════════════════════════════════════════════════════
_telegram_loop = None
_telegram_app = None
_telegram_ready = threading.Event()


def _telegram_thread_main():
    global _telegram_loop, _telegram_app

    try:
        _telegram_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_telegram_loop)

        _telegram_app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .updater(None)
            .build()
        )
        _telegram_app.add_handler(CommandHandler('start', start_command))
        _telegram_app.add_handler(CommandHandler('balance', balance_command))
        _telegram_app.add_handler(CommandHandler('create', create_command))
        _telegram_app.add_handler(CommandHandler('deposit', deposit_command))
        _telegram_app.add_handler(CommandHandler('withdraw', withdraw_command))
        _telegram_app.add_handler(CommandHandler('help', help_command))
        _telegram_app.add_handler(CallbackQueryHandler(button_callback))

        _telegram_loop.run_until_complete(_telegram_app.initialize())
        _telegram_loop.run_until_complete(_telegram_app.start())

        render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://bahr-bot-c3ac.onrender.com')
        webhook_url = f"{render_url.rstrip('/')}/{TELEGRAM_BOT_TOKEN}"
        _telegram_loop.run_until_complete(_telegram_app.bot.set_webhook(webhook_url))

        logger.info('✅ Telegram bot ready, webhook: %s', webhook_url)
        _telegram_ready.set()
        _telegram_loop.run_forever()
    except Exception as e:
        logger.error('❌ Telegram thread crashed: %s', e)
        # ready stays unset → webhook returns 503


_telegram_thread = threading.Thread(target=_telegram_thread_main, daemon=True)
_telegram_thread.start()

# ═══════════════════════════════════════════════════════════════
# Webhook Route
# ═══════════════════════════════════════════════════════════════
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    if not TELEGRAM_BOT_TOKEN:
        return 'Bot token missing', 500

    if not _telegram_ready.is_set():
        logger.warning('Webhook received but Telegram thread not ready')
        return 'Not Ready', 503

    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, _telegram_app.bot)

        future = asyncio.run_coroutine_threadsafe(
            _telegram_app.process_update(update),
            _telegram_loop
        )
        future.result(timeout=15)
        return 'OK'
    except Exception:
        logger.exception('Webhook processing error')
        return 'Error', 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
