"""Arabic Telegram Casino Bot — Cloudflare Bypass with Thordata Web Unlocker + curl_cffi + SOCKS5 proxy fallback."""
import os, json, logging, requests, urllib.parse, re
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from telegram import Bot
import asyncio
from telegram.constants import ParseMode
from urllib.parse import urlencode

# curl_cffi for advanced browser emulation (Cloudflare bypass via proxy)
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except Exception as _import_err:
    CURL_CFFI_AVAILABLE = False
    curl_requests = None

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Bot Configuration ───────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_TOKEN_HERE')
API_SECRET        = os.environ.get('API_SECRET', 'YOUR_API_SECRET_HERE')

# ─── Thordata Web Unlocker (Primary bypass) ────────────────────
THORDATA_TOKEN = os.environ.get('THORDATA_TOKEN', 'a88e6ccf584d663b4e55d6fc746e805e')

# ─── SOCKS5 / HTTP Proxy (Fallback) ────────────────────────────
RESIDENTIAL_PROXY = os.environ.get('RESIDENTIAL_PROXY', '')
# MUST be https://... or socks5://...  NOT http:// (will cause SSL WRONG_VERSION_NUMBER)

THORDATA_ENDPOINT = 'https://webunlocker.thordata.com/request'

# ─── Target Domain ───────────────────────────────────────────
API_DOMAIN = 'https://agents.texas4win.com'

# ─── Graceful JSON extraction ─────────────────────────────────
CLEAN_RE = re.compile(r'<[^>]+>')

def safe_json_load(text, log_prefix=''):
    """Strip HTML tags, control chars, and try to decode JSON from any blob."""
    if not text or not isinstance(text, str):
        return None
    text = CLEAN_RE.sub('', text)
    text = text.replace('\x00','').replace('\x0b','').replace('\x0c','').strip()
    if text.startswith('"') and text.endswith('"'):
        try:
            text = json.loads(text)
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        arr_start = text.find('[')
        obj_start = text.find('{')
        if obj_start != -1 and (arr_start == -1 or obj_start < arr_start):
            text = text[obj_start:]
            try:
                return json.loads(text)
            except Exception:
                pass
        if arr_start != -1:
            text = text[arr_start:]
            try:
                return json.loads(text)
            except Exception:
                pass
    return None


def _proxy_for():
    """Return a proxy dict if RESIDENTIAL_PROXY is set."""
    if not RESIDENTIAL_PROXY:
        return None
    if '://' not in RESIDENTIAL_PROXY:
        return {'http': f'http://{RESIDENTIAL_PROXY}', 'https': f'http://{RESIDENTIAL_PROXY}'}
    parsed = urllib.parse.urlparse(RESIDENTIAL_PROXY)
    if parsed.scheme in ('socks5', 'socks5h', 'socks4', 'socks4a'):
        return {'http': RESIDENTIAL_PROXY, 'https': RESIDENTIAL_PROXY}
    return {'http': RESIDENTIAL_PROXY, 'https': RESIDENTIAL_PROXY}


def _thordata_unlocker(method, url, **kwargs):
    """Use Thordata Web Unlocker to fetch a URL. Returns requests.Response."""
    form_data = {'url': url, 'type': 'html'}
    headers = {
        'Authorization': f'Bearer {THORDATA_TOKEN}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    try:
        logger.info('🔥 Thordata Web Unlocker: %s %s via POST %s', method, url, THORDATA_ENDPOINT)
        resp = requests.post(
            THORDATA_ENDPOINT,
            data=urlencode(form_data),
            headers=headers,
            timeout=kwargs.get('timeout', 30),
        )
        resp.raise_for_status()
        return resp
    except Exception as e:
        logger.error('Thordata Web Unlocker failed: %s', e)
        raise


class ApiResponse:
    """Wrapper that normalizes Thordata HTML responses and direct JSON responses."""
    def __init__(self, raw_resp):
        self._raw = raw_resp
        self.status_code = raw_resp.status_code
        self.text = getattr(raw_resp, 'text', '')
        self.content = getattr(raw_resp, 'content', b'')
        self.headers = getattr(raw_resp, 'headers', {})

    @property
    def json(self):
        # Try to parse as JSON first
        data = safe_json_load(self.text)
        if data is not None:
            return data
        # If Thordata returns HTML, try to extract JSON from it
        if '<' in self.text:
            return safe_json_load(self.text)
        raise ValueError('Response is not JSON')

    def __repr__(self):
        return f'<ApiResponse [{self.status_code}]>'


def api_request(method, endpoint, **kwargs):
    """
    1) Try Thordata Web Unlocker (primary Cloudflare bypass) for GET/DELETE/OPTIONS.
    2) If Thordata fails or body is present, try standard requests + curl_cffi + proxy.
    """
    url = f'{API_DOMAIN}{endpoint}'
    timeout = kwargs.get('timeout', 30)
    json_body = kwargs.get('json')
    extra_headers = kwargs.get('headers', {})

    # 1) Thordata Web Unlocker for GET/DELETE/OPTIONS (no body)
    if THORDATA_TOKEN and method.upper() in ('GET', 'DELETE', 'OPTIONS'):
        try:
            raw = _thordata_unlocker(method, url, **kwargs)
            return ApiResponse(raw)
        except Exception as e:
            logger.info('Thordata bypass failed, trying proxy fallback: %s', e)

    # 2) For POST/PUT with body or Thordata failure, use proxy + curl_cffi
    try:
        proxy = _proxy_for()
        if proxy:
            logger.info('Direct proxy request: %s', proxy.get('https') or proxy.get('http'))
        else:
            logger.info('Direct request without proxy')

        # Try curl_cffi first for advanced stealth
        if CURL_CFFI_AVAILABLE:
            try:
                proxy_url = None
                if proxy:
                    proxy_url = proxy.get('https') or proxy.get('http')
                raw = curl_requests.request(
                    method, url,
                    json=json_body,
                    headers=extra_headers,
                    proxy=proxy_url,
                    timeout=timeout,
                )
                raw.raise_for_status()
                return ApiResponse(raw)
            except Exception as curl_err:
                logger.warning('curl_cffi failed: %s, falling back to requests', curl_err)

        # Fallback to requests library
        raw = requests.request(
            method, url,
            json=json_body,
            headers=extra_headers,
            proxies=proxy,
            timeout=timeout,
        )
        raw.raise_for_status()
        return ApiResponse(raw)
    except Exception as e:
        logger.error('All bypass methods failed for %s: %s', url, e)
        raise


# ─── Flask App (webhook) ─────────────────────────────────────
app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Texas4Win Agent is online!'

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()})

@app.route('/deposit', methods=['POST'])
def handle_deposit():
    data = request.get_json(force=True)
    if not data or data.get('secret') != API_SECRET:
        return jsonify({'error': 'Invalid secret'}), 403
    user_id = data.get('user_id')
    amount  = data.get('amount')
    if not user_id or not amount:
        return jsonify({'error': 'Missing user_id or amount'}), 400
    try:
        msg = f'✅ تم إيداع ${amount} بنجاح! 🎉'
        asyncio.run(bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.HTML))
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error('Deposit error: %s', e)
        return jsonify({'error': str(e)}), 500


# ─── Telegram Bot Handlers ───────────────────────────────────
user_balances: dict[str, float] = {}

async def get_balance(user_id: str) -> float:
    return user_balances.get(user_id, 0.0)

async def update_balance(user_id: str, amount: float) -> None:
    user_balances[user_id] = user_balances.get(user_id, 0.0) + amount

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    await get_balance(user_id)
    welcome_msg = (
        f'🎰 مرحباً {user.first_name}!\n\n'
        'مرحباً بك في بوت الكازينو! 🎲\n\n'
        '💰 رصيدك الحالي: $0.00\n\n'
        '💵 إيداع: 0.00 USD\n'
        '💸 سحب: 0.00 USD\n\n'
        'اضغط على الروابط أدناه للبدء:'
    )
    keyboard = [
        [InlineKeyboardButton('🎰 العب الآن', url='https://agents.texas4win.com')],
        [InlineKeyboardButton('💳 إيداع', callback_data='deposit')],
        [InlineKeyboardButton('💸 سحب', callback_data='withdraw')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    balance = await get_balance(user_id)
    msg = (
        f'💰 رصيدك الحالي: ${balance:.2f}\n\n'
        '💵 إيداع: 0.00 USD\n'
        '💸 سحب: 0.00 USD'
    )
    await update.message.reply_text(msg)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == 'deposit':
        keyboard = [[InlineKeyboardButton('💳 إيداع الآن', url='https://agents.texas4win.com')]]
        await query.edit_message_text(
            '💳 لإيداع الأموال، اضغط على الزر أدناه:',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == 'withdraw':
        await query.edit_message_text('💸 لسحب الأموال، يرجى التواصل مع الدعم.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        '🎰 *دليل البوت*\n\n'
        '/start - بدء البوت\n'
        '/balance - رصيدك\n'
        '/help - المساعدة\n\n'
        '💰 للإيداع، اضغط على زر الإيداع في القائمة الرئيسية.'
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ─── Test Thordata on startup ───────────────────────────────
def _test_thordata_on_startup():
    try:
        test_url = f'{API_DOMAIN}/health'
        logger.info('🧪 Testing Thordata Web Unlocker against %s...', test_url)
        resp = _thordata_unlocker('GET', test_url)
        logger.info('✅ Thordata Web Unlocker OK: %s — %s', resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning('⚠️ Thordata Web Unlocker startup test failed: %s', e)
        logger.warning('⚠️ Will fallback to proxy when requests arrive...')


def _init_telegram():
    app_builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
    telegram_app = app_builder.build()
    telegram_app.add_handler(CommandHandler('start', start_command))
    telegram_app.add_handler(CommandHandler('balance', balance_command))
    telegram_app.add_handler(CommandHandler('help', help_command))
    telegram_app.add_handler(CallbackQueryHandler(button_callback))
    return telegram_app


if __name__ == '__main__':
    _test_thordata_on_startup()
    telegram_app = _init_telegram()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
    if WEBHOOK_URL:
        telegram_app.run_webhook(
            listen='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            webhook_url=WEBHOOK_URL,
        )
    else:
        telegram_app.run_polling()
