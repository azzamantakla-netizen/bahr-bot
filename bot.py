import os
import json
import random
import string
import threading
import logging
import sqlite3
import asyncio
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlencode

from flask import Flask, request, jsonify
import requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN', '8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE')
AGENT_USERNAME = os.environ.get('AGENT_USERNAME', 'Bero@yahoo.com')
AGENT_PASSWORD = os.environ.get('AGENT_PASSWORD', 'Aazzam@318')
PARENT_ID = int(os.environ.get('PARENT_ID', '2688288'))
CURRENCY = os.environ.get('CURRENCY', 'SYP')
OWNER_ID = int(os.environ.get('OWNER_ID', '6693251012'))
ADMIN_GROUP = int(os.environ.get('ADMIN_GROUP', '-1003983996094'))
SHAM_CASH_WALLET = os.environ.get('SHAM_CASH_WALLET', 'a18758d5324eb7595d4463ca355ad221')
SYRIATEL_CASH_CODE = os.environ.get('SYRIATEL_CASH_CODE', '48122120')
DEPOSIT_MIN = int(os.environ.get('DEPOSIT_MIN', '100000'))
WITHDRAW_MIN = int(os.environ.get('WITHDRAW_MIN', '200000'))
WITHDRAW_MAX = int(os.environ.get('WITHDRAW_MAX', '2000000'))
WITHDRAW_FEE_PERCENT = int(os.environ.get('WITHDRAW_FEE_PERCENT', '10'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
API_BASE = os.environ.get('API_BASE', 'https://agents.texas4win.com/global/api/User/')
DB_PATH = os.environ.get('DB_PATH', '/tmp/texas4win.db')
PORT = int(os.environ.get('PORT', '10000'))

# Thordata Residential Proxy (primary Cloudflare bypass for POST API calls)
THORDATA_PROXY = os.environ.get('THORDATA_PROXY', '')
# Thordata Web Unlocker (optional — for fetching pages via GET only, NOT for POST API calls)
THORDATA_TOKEN = os.environ.get('THORDATA_TOKEN', '')

# ═══════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('Texas4Win')

# ═══════════════════════════════════════════════════════════════
# Database
# ═══════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        telegram_id INTEGER PRIMARY KEY,
        player_id TEXT,
        username TEXT,
        password TEXT,
        registered_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        telegram_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'admin',
        added_by INTEGER,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        amount INTEGER,
        method TEXT,
        transaction_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        amount INTEGER,
        method TEXT,
        wallet_address TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending'
    )''')
    # Insert owner as admin
    c.execute('INSERT OR IGNORE INTO admins (telegram_id, role) VALUES (?, ?)', (OWNER_ID, 'owner'))
    # Insert default settings
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('sham_cash_wallet', SHAM_CASH_WALLET))
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('syriatel_cash_code', SYRIATEL_CASH_CODE))
    conn.commit()
    conn.close()


def db_execute(query, params=(), fetch=False, fetchone=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    result = None
    if fetchone:
        result = c.fetchone()
    elif fetch:
        result = c.fetchall()
    conn.commit()
    conn.close()
    return result


# ═══════════════════════════════════════════════════════════════
# Agent API Client (with Thordata Web Unlocker for Cloudflare bypass)
# ═══════════════════════════════════════════════════════════════
class AgentAPI:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self._lock = threading.Lock()
        self._use_proxy = bool(THORDATA_PROXY)
        if self._use_proxy:
            logger.info('🌐 Thordata residential proxy enabled — Cloudflare bypass active')
        else:
            logger.warning('⚠️ No THORDATA_PROXY set — direct API calls only (may be blocked by Cloudflare)')
        self._login()

    def _fetch_page_via_webunlocker(self, target_url, timeout=30):
        """Fetch a page via Thordata Web Unlocker (GET only — for scraping, NOT for POST API calls).

        The Web Unlocker fetches HTML pages via GET. It CANNOT forward
        custom POST bodies or JSON payloads to the target. Use this only
        for fetching static pages, login pages, or extracting cookies/tokens.
        For all POST API calls, use _proxy_request() instead.
        """
        if not THORDATA_TOKEN:
            return None

        payload = {
            'url': target_url,
            'type': 'html',
            'js_render': 'False',
            'header': 'False',
        }
        try:
            resp = requests.post(
                'https://webunlocker.thordata.com/request',
                data=payload,  # form-urlencoded, NOT json=
                headers={
                    'Authorization': f'Bearer {THORDATA_TOKEN}',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                timeout=timeout
            )
            if resp.status_code == 200:
                logger.info('✅ Web Unlocker fetched page: %s', target_url)
                return resp.text
            else:
                logger.error('❌ Web Unlocker failed [%d]: %s', resp.status_code, resp.text[:300])
                return None
        except Exception as e:
            logger.error('❌ Web Unlocker error: %s', e)
            return None

    def _proxy_request(self, endpoint, payload, headers, timeout=20):
        """Use Thordata residential proxy for POST API requests (Cloudflare bypass)."""
        if not THORDATA_PROXY:
            return None

        proxy_url = THORDATA_PROXY

        # Fix: use https:// instead of http:// for the proxy URL
        # Thordata residential proxy requires https:// to avoid SSL WRONG_VERSION_NUMBER
        if proxy_url.startswith('http://') and 'thordata' in proxy_url:
            proxy_url = proxy_url.replace('http://', 'https://', 1)
            logger.info('🔄 Switched proxy URL from http:// to https://')

        proxies = {
            'http': proxy_url,
            'https': proxy_url,
        }
        try:
            resp = requests.post(
                f'{API_BASE}{endpoint}',
                json=payload,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
                verify=False  # Suppress SSL errors with proxy
            )
            logger.info('✅ Proxy request succeeded [%s]', endpoint)
            return resp
        except requests.exceptions.SSLError as e:
            logger.error('❌ Proxy SSL error [%s]: %s', endpoint, e)
            # Try with http:// proxy as fallback (some proxy configs differ)
            if proxy_url.startswith('https://'):
                fallback_url = proxy_url.replace('https://', 'http://', 1)
                try:
                    resp = requests.post(
                        f'{API_BASE}{endpoint}',
                        json=payload,
                        headers=headers,
                        proxies={'http': fallback_url, 'https': fallback_url},
                        timeout=timeout,
                        verify=False
                    )
                    logger.info('✅ Proxy (http fallback) succeeded [%s]', endpoint)
                    return resp
                except Exception as e2:
                    logger.error('❌ Proxy http fallback also failed [%s]: %s', endpoint, e2)
            return None
        except Exception as e:
            logger.error('❌ Proxy request error [%s]: %s', endpoint, e)
            return None

    def _direct_request(self, endpoint, payload, headers, timeout=15):
        """Direct API request (no proxy/unlock)."""
        try:
            resp = requests.post(
                f'{API_BASE}{endpoint}',
                json=payload,
                headers=headers,
                timeout=timeout
            )
            return resp
        except Exception as e:
            logger.error('❌ Direct request error [%s]: %s', endpoint, e)
            return None

    def _login(self):
        try:
            # Try direct first, then fallback to proxy
            resp = self._direct_request('signIn',
                {'username': AGENT_USERNAME, 'password': AGENT_PASSWORD},
                {'Content-Type': 'application/json'},
                timeout=15
            )

            if resp and resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get('result', {}).get('accessToken')
                self.refresh_token = data.get('result', {}).get('refreshToken')
                if self.access_token:
                    logger.info('✅ Agent API login successful (direct)')
                    return True

            # If direct fails (likely Cloudflare), try residential proxy
            if self._use_proxy:
                logger.info('🔄 Direct login blocked, trying Thordata proxy...')
                resp = self._proxy_request('signIn',
                    {'username': AGENT_USERNAME, 'password': AGENT_PASSWORD},
                    {'Content-Type': 'application/json'},
                    timeout=15
                )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    self.access_token = data.get('result', {}).get('accessToken')
                    self.refresh_token = data.get('result', {}).get('refreshToken')
                    if self.access_token:
                        logger.info('✅ Agent API login successful (via proxy)')
                        return True

            logger.error('❌ Agent API login failed: %s', resp.text if resp else 'No response')
            return False
        except Exception as e:
            logger.error('❌ Agent API login error: %s', e)
            return False

    def _refresh(self):
        try:
            resp = self._direct_request('refreshToken',
                {'refreshToken': self.refresh_token},
                {'Content-Type': 'application/json'},
                timeout=15
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get('result', {}).get('accessToken')
                self.refresh_token = data.get('result', {}).get('refreshToken')
                if self.access_token:
                    logger.info('✅ Token refreshed successfully')
                    return True

            # Try proxy if direct fails
            if self._use_proxy:
                resp = self._proxy_request('refreshToken',
                    {'refreshToken': self.refresh_token},
                    {'Content-Type': 'application/json'},
                    timeout=15
                )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    self.access_token = data.get('result', {}).get('accessToken')
                    self.refresh_token = data.get('result', {}).get('refreshToken')
                    if self.access_token:
                        logger.info('✅ Token refreshed via proxy')
                        return True

            return self._login()
        except Exception as e:
            logger.error('❌ Token refresh error: %s', e)
            return self._login()

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def _request(self, endpoint, payload):
        with self._lock:
            for attempt in range(2):
                try:
                    # Try direct first
                    resp = self._direct_request(endpoint, payload, self._headers(), timeout=15)

                    if resp is None or resp.status_code == 403:
                        # Cloudflare blocked - try proxy
                        if self._use_proxy:
                            logger.info('🔄 Direct blocked for %s, trying proxy...', endpoint)
                            resp = self._proxy_request(endpoint, payload, self._headers(), timeout=15)

                    if resp and resp.status_code == 401:
                        if self._refresh():
                            continue
                        return None

                    if resp and resp.status_code == 200:
                        try:
                            return resp.json()
                        except Exception:
                            logger.error('❌ Failed to parse JSON from %s response', endpoint)
                            return None

                    if resp:
                        logger.error('❌ API %s returned %d: %s', endpoint, resp.status_code, resp.text[:300])
                    return None
                except Exception as e:
                    logger.error('❌ API request error [%s]: %s', endpoint, e)
                    if attempt == 1:
                        return None
            return None

    def register_player(self, login, password, email):
        return self._request('registerPlayer', {
            'player': {
                'email': email,
                'password': password,
                'parentId': str(PARENT_ID),
                'login': login
            }
        })

    def get_player_balance(self, player_id):
        return self._request('getPlayerBalanceById', {
            'playerId': str(player_id)
        })

    def deposit_to_player(self, player_id, amount, comment=''):
        return self._request('depositToPlayer', {
            'amount': amount,
            'comment': comment,
            'playerId': str(player_id),
            'currencyCode': CURRENCY,
            'currency': CURRENCY,
            'moneyStatus': 5
        })

    def withdraw_from_player(self, player_id, amount, comment=''):
        return self._request('withdrawFromPlayer', {
            'amount': amount,
            'comment': comment,
            'playerId': str(player_id),
            'currencyCode': CURRENCY,
            'currency': CURRENCY,
            'moneyStatus': 5
        })

    def get_agent_wallets(self):
        return self._request('getAgentAllWallets', {})

    def get_players(self, search=None, player_id=None, start=0, limit=50):
        payload = {'start': start, 'limit': limit}
        filter_obj = {}
        if player_id:
            filter_obj['playerID'] = {'action': '=', 'value': str(player_id)}
        elif search:
            filter_obj['userName'] = {'action': 'like', 'value': search}
        if filter_obj:
            payload['filter'] = filter_obj
        return self._request('getPlayersForCurrentAgent', payload)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def generate_random_email():
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f'{name}@texas4win.com'


def is_player(telegram_id):
    row = db_execute('SELECT * FROM players WHERE telegram_id=?', (telegram_id,), fetchone=True)
    return row is not None


def get_player(telegram_id):
    return db_execute('SELECT * FROM players WHERE telegram_id=?', (telegram_id,), fetchone=True)


def is_admin(telegram_id):
    row = db_execute('SELECT * FROM admins WHERE telegram_id=?', (telegram_id,), fetchone=True)
    return row is not None


def is_owner(telegram_id):
    row = db_execute('SELECT * FROM admins WHERE telegram_id=? AND role=?', (telegram_id, 'owner'), fetchone=True)
    return row is not None


def get_setting(key):
    row = db_execute('SELECT value FROM settings WHERE key=?', (key,), fetchone=True)
    return row[0] if row else None


def update_setting(key, value):
    db_execute('UPDATE settings SET value=? WHERE key=?', (value, key))


def owner_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_owner(user_id):
            await update.effective_message.reply_text('⛔ هذا الإجراء متاح فقط لمالك البوت')
            return
        return await func(update, context)
    return wrapper


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.effective_message.reply_text('⛔ هذا الإجراء متاح فقط للمشرفين')
            return
        return await func(update, context)
    return wrapper


# ═══════════════════════════════════════════════════════════════
# User States (conversation flow)
# ═══════════════════════════════════════════════════════════════
user_states = {}


def set_state(telegram_id, state, data=None):
    user_states[telegram_id] = {'state': state, 'data': data or {}}


def get_state(telegram_id):
    return user_states.get(telegram_id)


def clear_state(telegram_id):
    user_states.pop(telegram_id, None)


# ═══════════════════════════════════════════════════════════════
# Keyboards
# ═══════════════════════════════════════════════════════════════
def main_menu_keyboard(telegram_id):
    if is_player(telegram_id):
        keyboard = [
            [InlineKeyboardButton('📋 معلومات الحساب', callback_data='account_info')],
            [InlineKeyboardButton('📤 سحب', callback_data='withdraw'),
             InlineKeyboardButton('📥 ايداع', callback_data='deposit')],
            [InlineKeyboardButton('🆘 الدعم الفني', callback_data='support')],
            [InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton('🆕 إنشاء حساب', callback_data='create_account')],
            [InlineKeyboardButton('🆘 الدعم الفني', callback_data='support')],
            [InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]
        ]
    return InlineKeyboardMarkup(keyboard)


def deposit_method_keyboard():
    keyboard = [
        [InlineKeyboardButton('🟠 شام كاش', callback_data='deposit_sham'),
         InlineKeyboardButton('🔴 سيريتيل كاش', callback_data='deposit_syriatel')],
        [InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]
    ]
    return InlineKeyboardMarkup(keyboard)


def withdraw_method_keyboard():
    keyboard = [
        [InlineKeyboardButton('🟠 شام كاش', callback_data='withdraw_sham'),
         InlineKeyboardButton('🔴 سيريتيل كاش', callback_data='withdraw_syriatel')],
        [InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_action_keyboard(pending_id, action_type):
    keyboard = [
        [InlineKeyboardButton('✅ موافق', callback_data=f'approve_{action_type}_{pending_id}'),
         InlineKeyboardButton('❌ رفض', callback_data=f'reject_{action_type}_{pending_id}')],
    ]
    return InlineKeyboardMarkup(keyboard)


def owner_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton('👑 اضافة مالك', callback_data='add_owner'),
         InlineKeyboardButton('👤 اضافة مشرف', callback_data='add_admin')],
        [InlineKeyboardButton('❌ ازالة مشرف', callback_data='remove_admin')],
        [InlineKeyboardButton('💰 تفقد رصيد البوت', callback_data='bot_balance')],
        [InlineKeyboardButton('🟠 تعديل محفظة شام كاش', callback_data='edit_sham_wallet')],
        [InlineKeyboardButton('🔴 تعديل كود شام كاش', callback_data='edit_syriatel_code')],
        [InlineKeyboardButton('📢 الاذاعة', callback_data='broadcast')],
        [InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]
    ]
    return InlineKeyboardMarkup(keyboard)


# ═══════════════════════════════════════════════════════════════
# Bot Handlers
# ═══════════════════════════════════════════════════════════════
WELCOME_MSG = (
    'أهلا بك في عائلتنا 🎰\n\n'
    'جميع عمليات السحب والايداع مبرمجة بالكامل ✅\n\n'
    'تفضل باختيار طلبك من القائمة ادناه 👇'
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        telegram_id = update.effective_user.id
        await update.effective_message.reply_text(
            WELCOME_MSG,
            reply_markup=main_menu_keyboard(telegram_id)
        )
    except Exception as e:
        logger.error('❌ /start error: %s', e)


# ── Callback Query Handlers ──────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    telegram_id = query.from_user.id

    # ── Back to main ──
    if data == 'back_main':
        clear_state(telegram_id)
        await query.edit_message_text(
            WELCOME_MSG,
            reply_markup=main_menu_keyboard(telegram_id)
        )
        return

    # ── Create Account ──
    if data == 'create_account':
        set_state(telegram_id, 'awaiting_username')
        await query.edit_message_text(
            '🆕 إنشاء حساب جديد\n\n'
            'اختر اسم المستخدم الذي تريده:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]])
        )
        return

    # ── Account Info ──
    if data == 'account_info':
        player = get_player(telegram_id)
        if player:
            # Try to fetch live balance from API
            balance_text = ''
            if api and player[1]:
                try:
                    bal = api.get_player_balance(player[1])
                    if bal and 'result' in bal:
                        balance_val = bal['result']
                        if isinstance(balance_val, dict):
                            balance_val = balance_val.get('balance', balance_val.get('amount', 'N/A'))
                        balance_text = f'\n💰 الرصيد: `{balance_val}` {CURRENCY}'
                except Exception as e:
                    logger.error('❌ Balance fetch error: %s', e)

            msg = (
                f'📋 معلومات حسابك:\n\n'
                f'🆔 أيدي اللاعب: `{player[1]}`\n'
                f'👤 اسم المستخدم: `{player[2]}`\n'
                f'🔑 كلمة السر: `{player[3]}`'
                f'{balance_text}'
            )
            await query.edit_message_text(
                msg,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]])
            )
        return

    # ── Deposit ──
    if data == 'deposit':
        if not is_player(telegram_id):
            await query.edit_message_text('⚠️ يجب إنشاء حساب أولاً')
            return
        await query.edit_message_text(
            '📥 الإيداع\n\n'
            f'الحد الأدنى للإيداع: {DEPOSIT_MIN:,} {CURRENCY}\n\n'
            'اختر طريقة الإيداع:',
            reply_markup=deposit_method_keyboard()
        )
        return

    # ── Deposit: Sham Cash ──
    if data == 'deposit_sham':
        sham_wallet = get_setting('sham_cash_wallet')
        set_state(telegram_id, 'awaiting_deposit_amount', {'method': 'sham_cash', 'wallet': sham_wallet})
        await query.edit_message_text(
            '📥 إيداع عبر شام كاش\n\n'
            f'اكتب المبلغ المراد إيداعه:\n'
            f'(الحد الأدنى: {DEPOSIT_MIN:,} {CURRENCY})',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='deposit')]])
        )
        return

    # ── Deposit: Syriatel Cash ──
    if data == 'deposit_syriatel':
        syriatel_code = get_setting('syriatel_cash_code')
        set_state(telegram_id, 'awaiting_deposit_amount', {'method': 'syriatel_cash', 'code': syriatel_code})
        await query.edit_message_text(
            '📥 إيداع عبر سيريتيل كاش\n\n'
            f'اكتب المبلغ المراد إيداعه:\n'
            f'(الحد الأدنى: {DEPOSIT_MIN:,} {CURRENCY})',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='deposit')]])
        )
        return

    # ── Deposit: Amount Entered → Show wallet info ──
    if data == 'deposit':
        pass

    # ── Withdraw ──
    if data == 'withdraw':
        if not is_player(telegram_id):
            await query.edit_message_text('⚠️ يجب إنشاء حساب أولاً')
            return
        await query.edit_message_text(
            '📤 السحب\n\n'
            f'الحد الأدنى للسحب: {WITHDRAW_MIN:,} {CURRENCY}\n'
            f'الحد الأقصى للسحب: {WITHDRAW_MAX:,} {CURRENCY}\n'
            f'عمولة السحب: {WITHDRAW_FEE_PERCENT}%\n\n'
            'اختر طريقة السحب:',
            reply_markup=withdraw_method_keyboard()
        )
        return

    # ── Withdraw: Sham Cash ──
    if data == 'withdraw_sham':
        set_state(telegram_id, 'awaiting_withdraw_amount', {'method': 'sham_cash'})
        await query.edit_message_text(
            '📤 سحب عبر شام كاش\n\n'
            f'⚠️ يتم خصم عمولة {WITHDRAW_FEE_PERCENT}% من المبلغ\n\n'
            f'اكتب المبلغ المراد سحبه:\n'
            f'(من {WITHDRAW_MIN:,} إلى {WITHDRAW_MAX:,} {CURRENCY})',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='withdraw')]])
        )
        return

    # ── Withdraw: Syriatel Cash ──
    if data == 'withdraw_syriatel':
        set_state(telegram_id, 'awaiting_withdraw_amount', {'method': 'syriatel_cash'})
        await query.edit_message_text(
            '📤 سحب عبر سيريتيل كاش\n\n'
            f'⚠️ يتم خصم عمولة {WITHDRAW_FEE_PERCENT}% من المبلغ\n\n'
            f'اكتب المبلغ المراد سحبه:\n'
            f'(من {WITHDRAW_MIN:,} إلى {WITHDRAW_MAX:,} {CURRENCY})',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='withdraw')]])
        )
        return

    # ── Support ──
    if data == 'support':
        set_state(telegram_id, 'support_chat')
        await query.edit_message_text(
            '🆘 الدعم الفني\n\n'
            'اكتب رسالتك وسيتم تحويلها لفريق الدعم:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]])
        )
        return

    # ── Owner Panel ──
    if data == 'owner_panel':
        if is_owner(telegram_id):
            await query.edit_message_text(
                '⚙️ قائمة تحكم البوت',
                reply_markup=owner_panel_keyboard()
            )
        else:
            await query.answer('⛔ غير مصرح', show_alert=True)
        return

    # ── Owner: Add Owner ──
    if data == 'add_owner':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        set_state(telegram_id, 'awaiting_add_owner')
        await query.edit_message_text(
            '👑 اضافة مالك جديد\n\n'
            'أرسل أيدي التليغرام الخاص بالمالك الجديد:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Owner: Add Admin ──
    if data == 'add_admin':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        set_state(telegram_id, 'awaiting_add_admin')
        await query.edit_message_text(
            '👤 اضافة مشرف جديد\n\n'
            'أرسل أيدي التليغرام الخاص بالمشرف الجديد:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Owner: Remove Admin ──
    if data == 'remove_admin':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        admins = db_execute('SELECT telegram_id, role FROM admins', fetch=True)
        if not admins:
            await query.edit_message_text('⚠️ لا يوجد مشرفين حالياً')
            return
        keyboard = []
        for admin_id, role in admins:
            if role != 'owner' or admin_id != OWNER_ID:
                label = f'👑 {admin_id}' if role == 'owner' else f'👤 {admin_id}'
                keyboard.append([InlineKeyboardButton(label, callback_data=f'remove_admin_{admin_id}')])
        keyboard.append([InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')])
        await query.edit_message_text(
            '❌ اختر المشرف الذي تريد إزالته:',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ── Owner: Remove specific admin ──
    if data.startswith('remove_admin_') and data != 'remove_admin':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        target_id = int(data.split('_')[-1])
        db_execute('DELETE FROM admins WHERE telegram_id=? AND role!=?', (target_id, 'owner'))
        await query.edit_message_text(
            f'✅ تم إزالة المشرف {target_id}',
            reply_markup=owner_panel_keyboard()
        )
        return

    # ── Owner: Bot Balance ──
    if data == 'bot_balance':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        if api:
            wallets = api.get_agent_wallets()
            if wallets and 'result' in wallets:
                msg = '💰 أرصدة البوت:\n\n'
                for w in wallets['result']:
                    currency = w.get('currencyCode', 'N/A')
                    balance = w.get('balance', 0)
                    msg += f'💱 {currency}: {balance:,.2f}\n'
                await query.edit_message_text(
                    msg,
                    reply_markup=owner_panel_keyboard()
                )
            else:
                await query.edit_message_text(
                    '❌ فشل في جلب الأرصدة',
                    reply_markup=owner_panel_keyboard()
                )
        else:
            await query.edit_message_text(
                '❌ API غير متاح',
                reply_markup=owner_panel_keyboard()
            )
        return

    # ── Owner: Edit Sham Cash Wallet ──
    if data == 'edit_sham_wallet':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        current = get_setting('sham_cash_wallet')
        set_state(telegram_id, 'awaiting_edit_sham_wallet')
        await query.edit_message_text(
            f'🟠 تعديل محفظة شام كاش\n\n'
            f'المحفظة الحالية: `{current}`\n\n'
            f'أرسل العنوان الجديد:',
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Owner: Edit Syriatel Cash Code ──
    if data == 'edit_syriatel_code':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        current = get_setting('syriatel_cash_code')
        set_state(telegram_id, 'awaiting_edit_syriatel_code')
        await query.edit_message_text(
            f'🔴 تعديل كود سيريتيل كاش\n\n'
            f'الكود الحالي: `{current}`\n\n'
            f'أرسل الكود الجديد:',
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Owner: Broadcast ──
    if data == 'broadcast':
        if not is_owner(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        set_state(telegram_id, 'awaiting_broadcast')
        await query.edit_message_text(
            '📢 الاذاعة\n\n'
            'أرسل الرسالة التي تريد بثها لجميع اللاعبين:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Approve Deposit ──
    if data.startswith('approve_deposit_'):
        if not is_admin(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        pending_id = int(data.split('_')[-1])
        pending = db_execute(
            'SELECT telegram_id, amount, player_id FROM pending_deposits WHERE id=?',
            (pending_id,), fetchone=True
        )
        if not pending:
            await query.answer('⚠️ الطلب غير موجود', show_alert=True)
            return
        t_id, amount, p_id = pending
        player = get_player(t_id)
        if player and api:
            result = api.deposit_to_player(player[1], amount, f'Deposit approved by admin {telegram_id}')
            if result:
                db_execute('UPDATE pending_deposits SET status=? WHERE id=?', ('approved', pending_id))
                await query.edit_message_text(f'✅ تمت الموافقة على الإيداع — المبلغ: {amount:,} {CURRENCY}')
                try:
                    await context.bot.send_message(
                        chat_id=t_id,
                        text=f'✅ تمت الموافقة على إيداعك\n💰 المبلغ: {amount:,} {CURRENCY}'
                    )
                except Exception:
                    pass
            else:
                await query.answer('❌ فشل في تنفيذ الإيداع', show_alert=True)
        else:
            await query.answer('❌ اللاعب غير موجود أو API غير متاح', show_alert=True)
        return

    # ── Reject Deposit ──
    if data.startswith('reject_deposit_'):
        if not is_admin(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        pending_id = int(data.split('_')[-1])
        pending = db_execute(
            'SELECT telegram_id, amount FROM pending_deposits WHERE id=?',
            (pending_id,), fetchone=True
        )
        if not pending:
            await query.answer('⚠️ الطلب غير موجود', show_alert=True)
            return
        t_id, amount = pending
        db_execute('UPDATE pending_deposits SET status=? WHERE id=?', ('rejected', pending_id))
        await query.edit_message_text(f'❌ تم رفض الإيداع — المبلغ: {amount:,} {CURRENCY}')
        set_state(t_id, 'support_chat')
        try:
            await context.bot.send_message(
                chat_id=t_id,
                text='❌ تم رفض طلب الإيداع الخاص بك\nيرجى التواصل مع الدعم الفني لمزيد من المعلومات'
            )
        except Exception:
            pass
        return

    # ── Approve Withdrawal ──
    if data.startswith('approve_withdraw_'):
        if not is_admin(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        pending_id = int(data.split('_')[-1])
        pending = db_execute(
            'SELECT telegram_id, amount, player_id FROM pending_withdrawals WHERE id=?',
            (pending_id,), fetchone=True
        )
        if not pending:
            await query.answer('⚠️ الطلب غير موجود', show_alert=True)
            return
        t_id, amount, p_id = pending
        player = get_player(t_id)
        if player and api:
            result = api.withdraw_from_player(player[1], amount, f'Withdrawal approved by admin {telegram_id}')
            if result:
                db_execute('UPDATE pending_withdrawals SET status=? WHERE id=?', ('approved', pending_id))
                fee = int(amount * WITHDRAW_FEE_PERCENT / 100)
                net_amount = amount - fee
                await query.edit_message_text(
                    f'✅ تمت الموافقة على السحب\n💰 المبلغ: {amount:,} {CURRENCY}\n💸 العمولة: {fee:,} {CURRENCY}\n💵 الصافي: {net_amount:,} {CURRENCY}'
                )
                try:
                    await context.bot.send_message(
                        chat_id=t_id,
                        text=f'✅ تمت الموافقة على سحبك\n💰 المبلغ: {amount:,} {CURRENCY}\n💸 العمولة ({WITHDRAW_FEE_PERCENT}%): {fee:,} {CURRENCY}\n💵 الصافي: {net_amount:,} {CURRENCY}'
                    )
                except Exception:
                    pass
            else:
                await query.answer('❌ فشل في تنفيذ السحب', show_alert=True)
        else:
            await query.answer('❌ اللاعب غير موجود أو API غير متاح', show_alert=True)
        return

    # ── Reject Withdrawal ──
    if data.startswith('reject_withdraw_'):
        if not is_admin(telegram_id):
            await query.answer('⛔ غير مصرح', show_alert=True)
            return
        pending_id = int(data.split('_')[-1])
        pending = db_execute(
            'SELECT telegram_id, amount FROM pending_withdrawals WHERE id=?',
            (pending_id,), fetchone=True
        )
        if not pending:
            await query.answer('⚠️ الطلب غير موجود', show_alert=True)
            return
        t_id, amount = pending
        db_execute('UPDATE pending_withdrawals SET status=? WHERE id=?', ('rejected', pending_id))
        await query.edit_message_text(f'❌ تم رفض السحب — المبلغ: {amount:,} {CURRENCY}')
        try:
            await context.bot.send_message(
                chat_id=t_id,
                text='❌ تم رفض طلب السحب الخاص بك\nيرجى التواصل مع الدعم الفني لمزيد من المعلومات'
            )
        except Exception:
            pass
        return


# ── Message Handler ──────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = update.message.text
    state = get_state(telegram_id)

    if not state:
        # No active state, show main menu
        await update.message.reply_text(
            WELCOME_MSG,
            reply_markup=main_menu_keyboard(telegram_id)
        )
        return

    state_name = state['state']
    state_data = state['data']

    # ── Create Account: Username ──
    if state_name == 'awaiting_username':
        username = text.strip()
        if len(username) < 3:
            await update.message.reply_text('⚠️ اسم المستخدم يجب أن يكون 3 أحرف على الأقل')
            return

        # Generate random password and email
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        email = generate_random_email()

        # Register via API
        if api:
            result = api.register_player(username, password, email)
            if result and 'result' in result:
                player_data = result['result']
                player_id = player_data.get('id', player_data.get('playerId', ''))
                # Save to DB
                db_execute(
                    'INSERT OR REPLACE INTO players (telegram_id, player_id, username, password) VALUES (?, ?, ?, ?)',
                    (telegram_id, str(player_id), username, password)
                )
                clear_state(telegram_id)
                await update.message.reply_text(
                    f'✅ تم إنشاء حسابك بنجاح!\n\n'
                    f'👤 اسم المستخدم: `{username}`\n'
                    f'🔑 كلمة السر: `{password}`\n\n'
                    f'احفظ هذه المعلومات ولا تشاركها مع أحد 🔒',
                    parse_mode='Markdown',
                    reply_markup=main_menu_keyboard(telegram_id)
                )
            else:
                error_msg = result.get('message', 'غير معروف') if isinstance(result, dict) else 'غير معروف'
                await update.message.reply_text(
                    f'❌ فشل في إنشاء الحساب\n'
                    f'السبب: {error_msg}\n\n'
                    f'يرجى المحاولة مرة أخرى أو التواصل مع الدعم الفني',
                    reply_markup=main_menu_keyboard(telegram_id)
                )
                clear_state(telegram_id)
        else:
            await update.message.reply_text(
                '❌ API غير متاح حالياً، يرجى المحاولة لاحقاً',
                reply_markup=main_menu_keyboard(telegram_id)
            )
            clear_state(telegram_id)
        return

    # ── Deposit: Amount ──
    if state_name == 'awaiting_deposit_amount':
        try:
            amount = int(text.strip().replace(',', '').replace('.', ''))
        except ValueError:
            await update.message.reply_text('⚠️ الرجاء إدخال مبلغ صحيح (أرقام فقط)')
            return

        if amount < DEPOSIT_MIN:
            await update.message.reply_text(f'⚠️ الحد الأدنى للإيداع هو {DEPOSIT_MIN:,} {CURRENCY}')
            return

        method = state_data.get('method')
        set_state(telegram_id, 'awaiting_deposit_txid', {'method': method, 'amount': amount})

        if method == 'sham_cash':
            sham_wallet = get_setting('sham_cash_wallet')
            await update.message.reply_text(
                f'📥 إيداع عبر شام كاش\n\n'
                f'💰 المبلغ: {amount:,} {CURRENCY}\n\n'
                f'📍 أرسل المبلغ إلى المحفظة التالية:\n`{sham_wallet}`\n\n'
                f'بعد الإرسال، أرسل رقم العملية (Transaction ID):',
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='deposit')]])
            )
        else:
            syriatel_code = get_setting('syriatel_cash_code')
            await update.message.reply_text(
                f'📥 إيداع عبر سيريتيل كاش\n\n'
                f'💰 المبلغ: {amount:,} {CURRENCY}\n\n'
                f'📍 أرسل المبلغ إلى الكود التالي:\n`{syriatel_code}`\n\n'
                f'بعد الإرسال، أرسل رقم العملية (Transaction ID):',
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='deposit')]])
            )
        return

    # ── Deposit: Transaction ID ──
    if state_name == 'awaiting_deposit_txid':
        transaction_id = text.strip()
        method = state_data.get('method')
        amount = state_data.get('amount')
        player = get_player(telegram_id)

        # Save to pending_deposits
        db_execute(
            'INSERT INTO pending_deposits (telegram_id, amount, method, transaction_id, status) VALUES (?, ?, ?, ?, ?)',
            (telegram_id, amount, method, transaction_id, 'pending')
        )
        pending_id = db_execute(
            'SELECT id FROM pending_deposits WHERE telegram_id=? AND transaction_id=? ORDER BY id DESC LIMIT 1',
            (telegram_id, transaction_id), fetchone=True
        )[0]

        # Send to admin group
        player_name = player[2] if player else 'غير معروف'
        method_ar = 'شام كاش' if method == 'sham_cash' else 'سيريتيل كاش'
        admin_msg = (
            f'📥 طلب إيداع جديد\n\n'
            f'👤 اللاعب: {player_name}\n'
            f'🆔 أيدي: `{telegram_id}`\n'
            f'💰 المبلغ: {amount:,} {CURRENCY}\n'
            f'📌 الطريقة: {method_ar}\n'
            f'🔢 رقم العملية: `{transaction_id}`'
        )
        await context.bot.send_message(
            chat_id=ADMIN_GROUP,
            text=admin_msg,
            parse_mode='Markdown',
            reply_markup=admin_action_keyboard(pending_id, 'deposit')
        )

        clear_state(telegram_id)
        await update.message.reply_text(
            f'✅ تم إرسال طلب الإيداع بنجاح\n\n'
            f'💰 المبلغ: {amount:,} {CURRENCY}\n'
            f'🔢 رقم العملية: {transaction_id}\n\n'
            f'سيتم مراجعة طلبك من قبل المشرفين\n'
            f'يرجى الانتظار ⏳',
            reply_markup=main_menu_keyboard(telegram_id)
        )
        return

    # ── Withdraw: Amount ──
    if state_name == 'awaiting_withdraw_amount':
        try:
            amount = int(text.strip().replace(',', '').replace('.', ''))
        except ValueError:
            await update.message.reply_text('⚠️ الرجاء إدخال مبلغ صحيح (أرقام فقط)')
            return

        if amount < WITHDRAW_MIN:
            await update.message.reply_text(f'⚠️ الحد الأدنى للسحب هو {WITHDRAW_MIN:,} {CURRENCY}')
            return
        if amount > WITHDRAW_MAX:
            await update.message.reply_text(f'⚠️ الحد الأقصى للسحب هو {WITHDRAW_MAX:,} {CURRENCY}')
            return

        method = state_data.get('method')
        set_state(telegram_id, 'awaiting_withdraw_wallet', {'method': method, 'amount': amount})

        if method == 'sham_cash':
            await update.message.reply_text(
                '📍 أرسل عنوان محفظة شام كاش الخاصة بك:',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='withdraw')]])
            )
        else:
            await update.message.reply_text(
                '📍 أرسل كود/رقم سيريتيل كاش الخاص بك:',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='withdraw')]])
            )
        return

    # ── Withdraw: Wallet Address ──
    if state_name == 'awaiting_withdraw_wallet':
        wallet_address = text.strip()
        method = state_data.get('method')
        amount = state_data.get('amount')
        player = get_player(telegram_id)

        # Calculate fee
        fee = int(amount * WITHDRAW_FEE_PERCENT / 100)
        net_amount = amount - fee

        # Save to pending_withdrawals
        db_execute(
            'INSERT INTO pending_withdrawals (telegram_id, amount, method, wallet_address, status) VALUES (?, ?, ?, ?, ?)',
            (telegram_id, amount, method, wallet_address, 'pending')
        )
        pending_id = db_execute(
            'SELECT id FROM pending_withdrawals WHERE telegram_id=? AND wallet_address=? ORDER BY id DESC LIMIT 1',
            (telegram_id, wallet_address), fetchone=True
        )[0]

        # Send to admin group
        player_name = player[2] if player else 'غير معروف'
        method_ar = 'شام كاش' if method == 'sham_cash' else 'سيريتيل كاش'
        admin_msg = (
            f'📤 طلب سحب جديد\n\n'
            f'👤 اللاعب: {player_name}\n'
            f'🆔 أيدي: `{telegram_id}`\n'
            f'💰 المبلغ: {amount:,} {CURRENCY}\n'
            f'💸 العمولة ({WITHDRAW_FEE_PERCENT}%): {fee:,} {CURRENCY}\n'
            f'💵 صافي المبلغ: {net_amount:,} {CURRENCY}\n'
            f'📌 الطريقة: {method_ar}\n'
            f'📍 المحفظة: `{wallet_address}`'
        )
        await context.bot.send_message(
            chat_id=ADMIN_GROUP,
            text=admin_msg,
            parse_mode='Markdown',
            reply_markup=admin_action_keyboard(pending_id, 'withdraw')
        )

        clear_state(telegram_id)
        await update.message.reply_text(
            f'✅ تم إرسال طلب السحب بنجاح\n\n'
            f'💰 المبلغ: {amount:,} {CURRENCY}\n'
            f'💸 العمولة ({WITHDRAW_FEE_PERCENT}%): {fee:,} {CURRENCY}\n'
            f'💵 صافي المبلغ: {net_amount:,} {CURRENCY}\n\n'
            f'سيتم مراجعة طلبك من قبل المشرفين\n'
            f'يرجى الانتظار ⏳',
            reply_markup=main_menu_keyboard(telegram_id)
        )
        return

    # ── Support Chat ──
    if state_name == 'support_chat':
        player = get_player(telegram_id)
        player_name = player[2] if player else update.effective_user.first_name or 'غير معروف'
        admin_msg = (
            f'🆘 رسالة دعم فني\n\n'
            f'👤 اللاعب: {player_name}\n'
            f'🆔 أيدي: `{telegram_id}`\n\n'
            f'💬 الرسالة:\n{text}'
        )
        await context.bot.send_message(
            chat_id=ADMIN_GROUP,
            text=admin_msg,
            parse_mode='Markdown'
        )
        await update.message.reply_text(
            '✅ تم إرسال رسالتك إلى فريق الدعم\n'
            'سيتم الرد عليك في أقرب وقت ⏳'
        )
        clear_state(telegram_id)
        return

    # ── Owner: Add Owner ──
    if state_name == 'awaiting_add_owner':
        try:
            new_id = int(text.strip())
        except ValueError:
            await update.message.reply_text('⚠️ الرجاء إدخال أيدي صحيح (أرقام فقط)')
            return
        db_execute('INSERT OR REPLACE INTO admins (telegram_id, role) VALUES (?, ?)', (new_id, 'owner'))
        clear_state(telegram_id)
        await update.message.reply_text(
            f'✅ تم إضافة {new_id} كمالك بنجاح',
            reply_markup=owner_panel_keyboard()
        )
        return

    # ── Owner: Add Admin ──
    if state_name == 'awaiting_add_admin':
        try:
            new_id = int(text.strip())
        except ValueError:
            await update.message.reply_text('⚠️ الرجاء إدخال أيدي صحيح (أرقام فقط)')
            return
        db_execute('INSERT OR REPLACE INTO admins (telegram_id, role) VALUES (?, ?)', (new_id, 'admin'))
        clear_state(telegram_id)
        await update.message.reply_text(
            f'✅ تم إضافة {new_id} كمشرف بنجاح',
            reply_markup=owner_panel_keyboard()
        )
        return

    # ── Owner: Edit Sham Cash Wallet ──
    if state_name == 'awaiting_edit_sham_wallet':
        update_setting('sham_cash_wallet', text.strip())
        clear_state(telegram_id)
        await update.message.reply_text(
            f'✅ تم تحديث محفظة شام كاش بنجاح\n'
            f'📍 العنوان الجديد: `{text.strip()}`',
            parse_mode='Markdown',
            reply_markup=owner_panel_keyboard()
        )
        return

    # ── Owner: Edit Syriatel Code ──
    if state_name == 'awaiting_edit_syriatel_code':
        update_setting('syriatel_cash_code', text.strip())
        clear_state(telegram_id)
        await update.message.reply_text(
            f'✅ تم تحديث كود سيريتيل كاش بنجاح\n'
            f'📍 الكود الجديد: `{text.strip()}`',
            parse_mode='Markdown',
            reply_markup=owner_panel_keyboard()
        )
        return

    # ── Owner: Broadcast ──
    if state_name == 'awaiting_broadcast':
        players = db_execute('SELECT telegram_id FROM players', fetch=True)
        success = 0
        fail = 0
        for (pid,) in players:
            try:
                await context.bot.send_message(chat_id=pid, text=f'📢 {text}')
                success += 1
            except Exception:
                fail += 1
        clear_state(telegram_id)
        await update.message.reply_text(
            f'📢 تم الإذاعة\n\n'
            f'✅ نجاح: {success}\n'
            f'❌ فشل: {fail}',
            reply_markup=owner_panel_keyboard()
        )
        return


# Group reply handler - when admin replies to a support message in the group
async def group_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != ADMIN_GROUP:
        return

    # Check if message is a reply
    if not update.message.reply_to_message:
        return

    # Check if replier is admin
    if not is_admin(update.effective_user.id):
        return

    replied_text = update.message.reply_to_message.text or ''
    # Extract player telegram_id from the replied message
    import re
    match = re.search(r'🆔 أيدي: `(\d+)`', replied_text)
    if not match:
        return

    player_id = int(match.group(1))
    reply_text = update.message.text

    try:
        await context.bot.send_message(
            chat_id=player_id,
            text=f'🆘 رد الدعم الفني:\n\n{reply_text}'
        )
    except Exception as e:
        logger.error('❌ Failed to send support reply: %s', e)


# Owner /panel command
async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_owner(update.effective_user.id):
        await update.effective_message.reply_text(
            '⚙️ قائمة تحكم البوت',
            reply_markup=owner_panel_keyboard()
        )
    else:
        await update.effective_message.reply_text('⛔ هذا القسم متاح فقط لمالك البوت')


# ═══════════════════════════════════════════════════════════════
# Flask App + Webhook (PTB v21+ correct pattern)
# ═══════════════════════════════════════════════════════════════
app = Flask(__name__)

# Global references
telegram_app = None
telegram_loop = None
telegram_thread = None
telegram_ready = threading.Event()
api = None  # Global AgentAPI instance


def run_telegram_app():
    """Run the PTB Application event loop in a background thread.
    
    Key fix for PTB v21+: Use updater=None so we control webhook intake,
    initialize the Application ONCE at startup (not per-request),
    and feed updates via application.update_queue.put() in the Flask route.
    This avoids the _Application__stop_running_marker crash and
    'Application has no attribute username' errors.
    """
    global telegram_app, telegram_loop, api

    telegram_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telegram_loop)

    try:
        # Initialize database
        init_db()

        # Initialize Agent API
        api = AgentAPI()

        # Build PTB Application with updater=None (webhook mode)
        telegram_app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .updater(None)  # Critical: no updater, we feed updates manually
            .build()
        )

        # Register all handlers
        telegram_app.add_handler(CommandHandler('start', start_command))
        telegram_app.add_handler(CommandHandler('panel', panel_command))
        telegram_app.add_handler(CallbackQueryHandler(button_handler))
        telegram_app.add_handler(
            MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, message_handler)
        )
        telegram_app.add_handler(
            MessageHandler(filters.Chat(ADMIN_GROUP) & filters.REPLY, group_reply_handler)
        )

        # Initialize the application ONCE
        telegram_loop.run_until_complete(telegram_app.initialize())
        logger.info('✅ PTB Application initialized')

        # Start the application's internal processing
        telegram_loop.run_until_complete(telegram_app.start())
        logger.info('✅ PTB Application started')

        # Set webhook on Telegram's side
        if WEBHOOK_URL:
            telegram_loop.run_until_complete(
                telegram_app.bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
            )
            logger.info('🔗 Webhook set to %s', WEBHOOK_URL)

        # Signal readiness
        telegram_ready.set()
        logger.info('✅ Telegram bot ready — receiving updates via webhook')

        # Run the event loop forever (this blocks until loop.stop() is called)
        telegram_loop.run_forever()

    except Exception as e:
        logger.error('❌ Telegram thread crashed: %s', e, exc_info=True)
        telegram_ready.set()  # Prevent Flask from hanging


def ensure_telegram():
    """Ensure the Telegram background thread is running."""
    global telegram_thread
    if telegram_thread is not None and telegram_thread.is_alive() and telegram_ready.is_set():
        return
    if telegram_thread is None or not telegram_thread.is_alive():
        telegram_ready.clear()
        telegram_thread = threading.Thread(target=run_telegram_app, daemon=True)
        telegram_thread.start()
        logger.info('🔄 Starting Telegram background thread...')


# ── Flask Routes ─────────────────────────────────────────────

@app.route('/')
def home():
    ensure_telegram()
    return '✅ Texas4Win Bot is online!'


@app.route('/health')
def health_check():
    ensure_telegram()
    return jsonify({
        'status': 'healthy',
        'telegram_ready': telegram_ready.is_set(),
        'api_authenticated': api is not None and api.access_token is not None,
        'proxy_enabled': bool(THORDATA_PROXY),
        'webunlocker_enabled': bool(THORDATA_TOKEN),
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    """Receive webhook updates from Telegram and feed them to PTB.
    
    Critical: We do NOT call application.initialize() or shutdown() here.
    We simply deserialize the Update and put it on the update_queue.
    The PTB event loop (running in background thread) picks it up and
    dispatches to handlers.
    """
    ensure_telegram()

    if not telegram_ready.wait(timeout=15):
        logger.error('❌ Telegram thread not ready after 15s')
        return 'Not Ready', 503

    try:
        data = request.get_json(force=True)
        if not data:
            return 'Bad Request', 400

        # Deserialize the Update and put it on the queue
        update = Update.de_json(data, telegram_app.bot)

        # Schedule the update processing in the PTB event loop
        future = asyncio.run_coroutine_threadsafe(
            telegram_app.process_update(update),
            telegram_loop
        )
        # Wait for processing with timeout
        try:
            future.result(timeout=30)
        except Exception as e:
            logger.error('❌ Update processing error: %s', e)

        return 'OK'

    except Exception:
        logger.exception('❌ Webhook processing error')
        return 'Error', 500


@app.route('/deposit', methods=['POST'])
def handle_deposit():
    """External endpoint to notify bot about deposits."""
    return jsonify({'status': 'ok'})


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    ensure_telegram()
    app.run(host='0.0.0.0', port=PORT)
