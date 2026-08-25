"""
Texas4Win Agent Bot — Arabic Telegram Casino Bot
No proxy needed — IP 74.220.48.202 whitelisted on Cloudflare
"""

import os
import json
import re
import sqlite3
import random
import string
import threading
import asyncio
import time
import logging
from datetime import datetime

import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# ─── Configuration ────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE')
OWNER_IDS = [6693251012]
ADMIN_GROUP = int(os.environ.get('ADMIN_GROUP', '-1003983996094'))
AGENT_USERNAME = os.environ.get('AGENT_USERNAME', 'Bero@yahoo.com')
AGENT_PASSWORD = os.environ.get('AGENT_PASSWORD', 'Aazzam@318')
PARENT_ID = int(os.environ.get('PARENT_ID', '2688288'))
CURRENCY = os.environ.get('CURRENCY', 'SYP')
SHAM_CASH_WALLET = os.environ.get('SHAM_CASH_WALLET', 'a18758d5324eb7595d4463ca355ad221')
SYRIATEL_CASH_CODE = os.environ.get('SYRIATEL_CASH_CODE', '48122120')
DEPOSIT_MIN = int(os.environ.get('DEPOSIT_MIN', '100000'))
WITHDRAW_MIN = int(os.environ.get('WITHDRAW_MIN', '200000'))
WITHDRAW_MAX = int(os.environ.get('WITHDRAW_MAX', '2000000'))
WITHDRAW_FEE_PERCENT = int(os.environ.get('WITHDRAW_FEE_PERCENT', '10'))
API_BASE = os.environ.get('API_BASE', 'https://agents.texas4win.com/global/api/User/')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://bahr-bot-c3ac.onrender.com/webhook')
PORT = int(os.environ.get('PORT', '5000'))
DB_PATH = os.environ.get('DB_PATH', '/tmp/texas4win.db')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Database ─────────────────────────────────────────────────────────────────
def db_init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        telegram_id INTEGER PRIMARY KEY,
        player_id TEXT,
        username TEXT,
        password TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        telegram_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'admin'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        type TEXT,
        method TEXT,
        amount INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        admin_action INTEGER DEFAULT 0
    )''')
    # Insert default config
    c.execute('INSERT OR IGNORE INTO config VALUES (?, ?)', ('sham_cash_wallet', SHAM_CASH_WALLET))
    c.execute('INSERT OR IGNORE INTO config VALUES (?, ?)', ('syriatel_cash_code', SYRIATEL_CASH_CODE))
    # Insert owner as admin
    for oid in OWNER_IDS:
        c.execute('INSERT OR IGNORE INTO admins VALUES (?, ?)', (oid, 'owner'))
    conn.commit()
    conn.close()

def db_execute(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def db_fetch(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def db_fetchone(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    row = c.fetchone()
    conn.close()
    return row

# ─── User State Management ───────────────────────────────────────────────────
user_states = {}

def set_state(telegram_id, state, data=None):
    user_states[telegram_id] = {'state': state, 'data': data or {}}

def get_state(telegram_id):
    return user_states.get(telegram_id, {'state': 'main', 'data': {}})

def clear_state(telegram_id):
    user_states.pop(telegram_id, None)

# ─── Agent API ────────────────────────────────────────────────────────────────
class AgentAPI:
    def __init__(self):
        self._access_token = None
        self._refresh_token = None
        self._token_expires = 0
        self._last_auth_time = 0
        self._session = requests.Session()
        self._session.headers.update({'Content-Type': 'application/json'})

    def _request(self, endpoint, payload=None):
        """Send POST request to API."""
        url = API_BASE + endpoint
        
        # Ensure authenticated
        if not self._ensure_auth():
            return {'success': False, 'message': 'فشل تسجيل الدخول إلى الخادم'}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._access_token}'
        }
        
        try:
            resp = self._session.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 401:
                # Token expired, refresh and retry
                if self._refresh_auth():
                    headers['Authorization'] = f'Bearer {self._access_token}'
                    resp = self._session.post(url, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f'API error {resp.status_code}: {resp.text[:200]}')
                return {'success': False, 'message': f'خطأ الخادم: {resp.status_code}'}
        except requests.exceptions.RequestException as e:
            logger.error(f'Request exception: {e}')
            return {'success': False, 'message': f'خطأ الاتصال: {str(e)[:100]}'}

    def _ensure_auth(self):
        """Ensure we have a valid access token."""
        if self._access_token and time.time() < self._token_expires - 60:
            return True
        
        # Try refresh first if we have a refresh token
        if self._refresh_token and self._last_auth_time > 0:
            if self._refresh_auth():
                return True
        
        # Fresh login
        return self._sign_in()

    def _sign_in(self):
        """Sign in to get new tokens."""
        try:
            resp = self._session.post(
                API_BASE + 'signIn',
                json={'username': AGENT_USERNAME, 'password': AGENT_PASSWORD},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                if 'result' in data:
                    self._access_token = data['result'].get('accessToken')
                    self._refresh_token = data['result'].get('refreshToken')
                    self._token_expires = time.time() + 3600  # 1 hour
                    self._last_auth_time = time.time()
                    logger.info('API authentication successful')
                    return True
            logger.error(f'Sign-in failed: {resp.status_code} {resp.text[:200]}')
            return False
        except Exception as e:
            logger.error(f'Sign-in exception: {e}')
            return False

    def _refresh_auth(self):
        """Refresh the access token."""
        try:
            resp = self._session.post(
                API_BASE + 'refreshToken',
                json={'refreshToken': self._refresh_token},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                if 'result' in data:
                    self._access_token = data['result'].get('accessToken')
                    self._refresh_token = data['result'].get('refreshToken')
                    self._token_expires = time.time() + 3600
                    self._last_auth_time = time.time()
                    logger.info('API token refreshed')
                    return True
            return False
        except Exception as e:
            logger.error(f'Refresh exception: {e}')
            return False

    # ── API Methods ────────────────────────────────────────────────────────────

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

    def get_players(self, filter_val='', start=0, limit=100):
        return self._request('getPlayersForCurrentAgent', {
            'filter': filter_val,
            'start': start,
            'limit': limit
        })

    def get_agent_wallets(self):
        return self._request('getAgentAllWallets', {})

    def withdraw_from_agent(self, amount, comment='', money_status=5):
        return self._request('withdrawFromAgent', {
            'amount': amount,
            'comment': comment,
            'affiliateId': str(PARENT_ID),
            'moneyStatus': money_status,
            'currencyCode': CURRENCY
        })

    def is_authenticated(self):
        return self._access_token is not None and time.time() < self._token_expires


api = AgentAPI()

# ─── Helper Functions ─────────────────────────────────────────────────────────
def is_registered(telegram_id):
    row = db_fetchone('SELECT player_id FROM players WHERE telegram_id = ?', (telegram_id,))
    return row is not None and row[0]

def get_player_info(telegram_id):
    return db_fetchone('SELECT player_id, username, password FROM players WHERE telegram_id = ?', (telegram_id,))

def is_owner(telegram_id):
    return telegram_id in OWNER_IDS

def is_admin(telegram_id):
    row = db_fetchone('SELECT role FROM admins WHERE telegram_id = ?', (telegram_id,))
    return row is not None

def get_sham_wallet():
    row = db_fetchone('SELECT value FROM config WHERE key = ?', ('sham_cash_wallet',))
    return row[0] if row else SHAM_CASH_WALLET

def get_syriatel_code():
    row = db_fetchone('SELECT value FROM config WHERE key = ?', ('syriatel_cash_code',))
    return row[0] if row else SYRIATEL_CASH_CODE

def generate_random_email():
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f'{name}@gmail.com'

def format_amount(amount):
    return f'{int(amount):,}'

# ─── Keyboards ────────────────────────────────────────────────────────────────
def main_menu_keyboard(telegram_id):
    if is_registered(telegram_id):
        buttons = [
            ['معلومات الحساب', 'سحب'],
            ['ايداع', 'الدعم الفني'],
            ['🔙 رجوع']
        ]
    else:
        buttons = [
            ['إنشاء حساب', 'الدعم الفني'],
            ['🔙 رجوع']
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def deposit_keyboard():
    return ReplyKeyboardMarkup([
        ['شام كاش', 'سيرياتيل كاش'],
        ['🔙 رجوع']
    ], resize_keyboard=True)

def withdraw_keyboard():
    return ReplyKeyboardMarkup([
        ['شام كاش', 'سيرياتيل كاش'],
        ['🔙 رجوع']
    ], resize_keyboard=True)

def owner_panel_keyboard():
    return ReplyKeyboardMarkup([
        ['اضافة مالك', 'اضافة مشرف'],
        ['ازالة مشرف', 'تفقد رصيد البوت'],
        ['تعديل محفظة شام كاش', 'تعديل كود شام كاش'],
        ['الاذاعة'],
        ['🔙 رجوع']
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup([['🔙 رجوع']], resize_keyboard=True)

# ─── Welcome Message ──────────────────────────────────────────────────────────
WELCOME_MSG = 'أهلا بك في عائلتنا جميع عمليات السحب والايداع مبرمجة بالكامل تفضل باختيار طلبك من القائمة ادناه'

# ─── Bot Handlers ────────────────────────────────────────────────────────────
async def start_cmd(update: Update, context):
    telegram_id = update.effective_user.id
    clear_state(telegram_id)
    await update.message.reply_text(WELCOME_MSG, reply_markup=main_menu_keyboard(telegram_id))

async def panel_cmd(update: Update, context):
    telegram_id = update.effective_user.id
    if not is_owner(telegram_id):
        await update.message.reply_text('⛔ هذا الأمر للمالك فقط')
        return
    clear_state(telegram_id)
    set_state(telegram_id, 'owner_panel')
    await update.message.reply_text('👑 لوحة تحكم المالك:', reply_markup=owner_panel_keyboard())

async def handle_message(update: Update, context):
    telegram_id = update.effective_user.id
    text = update.message.text.strip()
    state = get_state(telegram_id)
    current_state = state['state']
    state_data = state['data']

    # ── Support chat relay (admin replying) ──
    if update.effective_chat.id == ADMIN_GROUP and current_state != 'owner_panel':
        # Admin is replying to a forwarded support message
        if update.message.reply_to_message:
            original_text = update.message.reply_to_message.text or update.message.reply_to_message.caption or ''
            # Try to extract telegram_id from forwarded message
            # Format: "📩 رسالة من اللاعب [ID: 12345]"
            match = re.search(r'\[ID:\s*(\d+)\]', original_text)
            if match:
                player_tid = int(match.group(1))
                try:
                    await context.bot.send_message(
                        chat_id=player_tid,
                        text=f'📩 رد الدعم الفني:\n\n{text}'
                    )
                    await update.message.reply_text('✅ تم إرسال الرد للاعب')
                except Exception as e:
                    await update.message.reply_text(f'❌ فشل إرسال الرد: {e}')
            return
        return

    # ── Back button ──
    if text == '🔙 رجوع':
        clear_state(telegram_id)
        await update.message.reply_text(WELCOME_MSG, reply_markup=main_menu_keyboard(telegram_id))
        return

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN MENU HANDLING
    # ══════════════════════════════════════════════════════════════════════════

    if current_state == 'main' or current_state == 'owner_panel_return':
        # ── إنشاء حساب ──
        if text == 'إنشاء حساب':
            set_state(telegram_id, 'create_account_username')
            await update.message.reply_text(
                '👤 اختر الاسم الذي تريده:',
                reply_markup=cancel_keyboard()
            )
            return

        # ── معلومات الحساب ──
        if text == 'معلومات الحساب':
            info = get_player_info(telegram_id)
            if info:
                player_id, username, password = info
                await update.message.reply_text(
                    f'📋 معلومات حسابك:\n\n'
                    f'🆔 رقم الحساب: `{player_id}`\n'
                    f'👤 اسم المستخدم: `{username}`\n'
                    f'🔑 كلمة السر: `{password}`\n\n'
                    f'احفظ هذه المعلومات ولا تشاركها مع أحد 🔒',
                    parse_mode='Markdown',
                    reply_markup=main_menu_keyboard(telegram_id)
                )
            else:
                await update.message.reply_text('❌ لم يتم العثور على حسابك', reply_markup=main_menu_keyboard(telegram_id))
            return

        # ── ايداع ──
        if text == 'ايداع':
            set_state(telegram_id, 'deposit_method')
            await update.message.reply_text(
                '💰 اختر طريقة الإيداع:',
                reply_markup=deposit_keyboard()
            )
            return

        # ── سحب ──
        if text == 'سحب':
            set_state(telegram_id, 'withdraw_method')
            await update.message.reply_text(
                '💸 اختر طريقة السحب:',
                reply_markup=withdraw_keyboard()
            )
            return

        # ── الدعم الفني ──
        if text == 'الدعم الفني':
            set_state(telegram_id, 'support_message')
            await update.message.reply_text(
                '📩 اكتب رسالتك وسنقوم بتحويلها للإدارة:',
                reply_markup=cancel_keyboard()
            )
            return

    # ══════════════════════════════════════════════════════════════════════════
    # CREATE ACCOUNT FLOW
    # ══════════════════════════════════════════════════════════════════════════

    if current_state == 'create_account_username':
        if len(text) < 3:
            await update.message.reply_text('❌ اسم المستخدم يجب أن يكون 3 أحرف على الأقل')
            return
        state_data['username'] = text
        set_state(telegram_id, 'create_account_password', state_data)
        await update.message.reply_text('🔑 اختر كلمة السر:', reply_markup=cancel_keyboard())
        return

    if current_state == 'create_account_password':
        if len(text) < 4:
            await update.message.reply_text('❌ كلمة السر يجب أن تكون 4 أحرف على الأقل')
            return
        username = state_data['username']
        password = text
        email = generate_random_email()

        result = api.register_player(username, password, email)
        if result and 'result' in result:
            player_data = result['result']
            player_id = player_data.get('id', player_data.get('playerId', ''))
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
                f'❌ فشل إنشاء الحساب: {error_msg}\nحاول مرة أخرى',
                reply_markup=main_menu_keyboard(telegram_id)
            )
            clear_state(telegram_id)
        return

    # ══════════════════════════════════════════════════════════════════════════
    # DEPOSIT FLOW
    # ══════════════════════════════════════════════════════════════════════════

    if current_state == 'deposit_method':
        if text in ('شام كاش', 'سيرياتيل كاش'):
            method = text
            state_data['method'] = method
            set_state(telegram_id, 'deposit_amount', state_data)
            wallet_info = ''
            if method == 'شام كاش':
                wallet_info = f'📱 محفظة شام كاش: `{get_sham_wallet()}`'
            else:
                wallet_info = f'📱 كود سيرياتيل كاش: `{get_syriatel_code()}`'
            await update.message.reply_text(
                f'💰 قم بتحويل المبلغ إلى:\n{wallet_info}\n\n'
                f'ثم أرسل المبلغ الذي أودعته (الحد الأدنى {format_amount(DEPOSIT_MIN)} SYP):',
                parse_mode='Markdown',
                reply_markup=cancel_keyboard()
            )
        return

    if current_state == 'deposit_amount':
        try:
            amount = int(text.replace(',', '').replace(' ', ''))
        except ValueError:
            await update.message.reply_text('❌ أرسل رقماً صحيحاً')
            return
        
        if amount < DEPOSIT_MIN:
            await update.message.reply_text(f'❌ الحد الأدنى للإيداع {format_amount(DEPOSIT_MIN)} SYP')
            return
        
        state_data['amount'] = amount
        set_state(telegram_id, 'deposit_transaction_id', state_data)
        await update.message.reply_text(
            f'💵 المبلغ: {format_amount(amount)} SYP\n\n'
            f'أرسل رقم العملية (Transaction ID):',
            reply_markup=cancel_keyboard()
        )
        return

    if current_state == 'deposit_transaction_id':
        method = state_data['method']
        amount = state_data['amount']
        transaction_id = text
        
        info = get_player_info(telegram_id)
        if not info:
            await update.message.reply_text('❌ لم يتم العثور على حسابك', reply_markup=main_menu_keyboard(telegram_id))
            clear_state(telegram_id)
            return
        
        player_id, username, _ = info
        
        # Save transaction
        db_execute(
            'INSERT INTO transactions (telegram_id, type, method, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (telegram_id, 'deposit', method, amount, 'pending', datetime.now().isoformat())
        )
        
        # Send to admin group
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton('✅ موافق', callback_data=f'approve_dep_{telegram_id}_{amount}'),
                 InlineKeyboardButton('❌ رفض', callback_data=f'reject_dep_{telegram_id}_{amount}')]
            ])
            await context.bot.send_message(
                chat_id=ADMIN_GROUP,
                text=(
                    f'📥 طلب إيداع جديد\n\n'
                    f'👤 اللاعب: {username}\n'
                    f'🆔 رقم الحساب: {player_id}\n'
                    f'📱 الطريقة: {method}\n'
                    f'💵 المبلغ: {format_amount(amount)} SYP\n'
                    f'🔢 رقم العملية: {transaction_id}\n'
                    f'🆔 تيليجرام: [ID: {telegram_id}]'
                ),
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f'Failed to send deposit to admin group: {e}')
        
        clear_state(telegram_id)
        await update.message.reply_text(
            '⏳ تم إرسال طلب الإيداع للإدارة. سيتم إشعارك بالموافقة قريباً.',
            reply_markup=main_menu_keyboard(telegram_id)
        )
        return

    # ══════════════════════════════════════════════════════════════════════════
    # WITHDRAW FLOW
    # ══════════════════════════════════════════════════════════════════════════

    if current_state == 'withdraw_method':
        if text in ('شام كاش', 'سيرياتيل كاش'):
            method = text
            state_data['method'] = method
            set_state(telegram_id, 'withdraw_confirm_fee', state_data)
            fee_amount = ''
            await update.message.reply_text(
                f'⚠️ تنبيه: عمولة السحب {WITHDRAW_FEE_PERCENT}%\n\n'
                f'مثلاً: إذا طلبت سحب {format_amount(WITHDRAW_MIN)} ستستلم {format_amount(int(WITHDRAW_MIN * 0.9))} SYP\n\n'
                f'اضغط على أي رسالة للمتابعة أو 🔙 رجوع للإلغاء',
                reply_markup=cancel_keyboard()
            )
        return

    if current_state == 'withdraw_confirm_fee':
        set_state(telegram_id, 'withdraw_amount', state_data)
        await update.message.reply_text(
            f'💸 أرسل مبلغ السحب (من {format_amount(WITHDRAW_MIN)} إلى {format_amount(WITHDRAW_MAX)} SYP):',
            reply_markup=cancel_keyboard()
        )
        return

    if current_state == 'withdraw_amount':
        try:
            amount = int(text.replace(',', '').replace(' ', ''))
        except ValueError:
            await update.message.reply_text('❌ أرسل رقماً صحيحاً')
            return
        
        if amount < WITHDRAW_MIN or amount > WITHDRAW_MAX:
            await update.message.reply_text(
                f'❌ مبلغ السحب يجب أن يكون بين {format_amount(WITHDRAW_MIN)} و {format_amount(WITHDRAW_MAX)} SYP'
            )
            return
        
        state_data['amount'] = amount
        set_state(telegram_id, 'withdraw_wallet', state_data)
        await update.message.reply_text(
            f'📱 أرسل عنوان المحفظة (عنوان شام كاش أو سيرياتيل كاش):',
            reply_markup=cancel_keyboard()
        )
        return

    if current_state == 'withdraw_wallet':
        method = state_data['method']
        amount = state_data['amount']
        wallet_address = text
        net_amount = int(amount * (1 - WITHDRAW_FEE_PERCENT / 100))
        
        info = get_player_info(telegram_id)
        if not info:
            await update.message.reply_text('❌ لم يتم العثور على حسابك', reply_markup=main_menu_keyboard(telegram_id))
            clear_state(telegram_id)
            return
        
        player_id, username, _ = info
        
        # Save transaction
        db_execute(
            'INSERT INTO transactions (telegram_id, type, method, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (telegram_id, 'withdraw', method, amount, 'pending', datetime.now().isoformat())
        )
        
        # Send to admin group
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton('✅ موافق', callback_data=f'approve_wd_{telegram_id}_{amount}'),
                 InlineKeyboardButton('❌ رفض', callback_data=f'reject_wd_{telegram_id}_{amount}')]
            ])
            await context.bot.send_message(
                chat_id=ADMIN_GROUP,
                text=(
                    f'📤 طلب سحب جديد\n\n'
                    f'👤 اللاعب: {username}\n'
                    f'🆔 رقم الحساب: {player_id}\n'
                    f'📱 الطريقة: {method}\n'
                    f'💵 المبلغ: {format_amount(amount)} SYP\n'
                    f'💰 صافي الاستلام: {format_amount(net_amount)} SYP (بعد عمولة {WITHDRAW_FEE_PERCENT}%)\n'
                    f'📱 عنوان المحفظة: {wallet_address}\n'
                    f'🆔 تيليجرام: [ID: {telegram_id}]'
                ),
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f'Failed to send withdrawal to admin group: {e}')
        
        clear_state(telegram_id)
        await update.message.reply_text(
            f'⏳ تم إرسال طلب السحب للإدارة.\n\n'
            f'💵 المبلغ: {format_amount(amount)} SYP\n'
            f'💰 صافي الاستلام: {format_amount(net_amount)} SYP (بعد عمولة {WITHDRAW_FEE_PERCENT}%)\n\n'
            f'سيتم إشعارك بالموافقة قريباً.',
            reply_markup=main_menu_keyboard(telegram_id)
        )
        return

    # ══════════════════════════════════════════════════════════════════════════
    # SUPPORT FLOW
    # ══════════════════════════════════════════════════════════════════════════

    if current_state == 'support_message':
        # Forward to admin group
        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP,
                text=(
                    f'📩 رسالة من اللاعب [ID: {telegram_id}]\n\n'
                    f'👤 الاسم: {update.effective_user.first_name}\n'
                    f'📝 الرسالة:\n{text}'
                )
            )
        except Exception as e:
            logger.error(f'Failed to forward support message: {e}')
        
        clear_state(telegram_id)
        await update.message.reply_text(
            '✅ تم إرسال رسالتك للإدارة. سيتم الرد عليك قريباً.',
            reply_markup=main_menu_keyboard(telegram_id)
        )
        return

    # ══════════════════════════════════════════════════════════════════════════
    # OWNER PANEL
    # ══════════════════════════════════════════════════════════════════════════

    if current_state == 'owner_panel':
        # ── اضافة مالك ──
        if text == 'اضافة مالك':
            set_state(telegram_id, 'owner_add_owner_id')
            await update.message.reply_text('👑 أرسل ID تيليجرام للمالك الجديد:', reply_markup=cancel_keyboard())
            return

        # ── اضافة مشرف ──
        if text == 'اضافة مشرف':
            set_state(telegram_id, 'owner_add_admin_id')
            await update.message.reply_text('👨‍💼 أرسل ID تيليجرام للمشرف الجديد:', reply_markup=cancel_keyboard())
            return

        # ── ازالة مشرف ──
        if text == 'ازالة مشرف':
            set_state(telegram_id, 'owner_remove_admin_id')
            await update.message.reply_text('❌ أرسل ID تيليجرام للمشرف المطلوب إزالته:', reply_markup=cancel_keyboard())
            return

        # ── تفقد رصيد البوت ──
        if text == 'تفقد رصيد البوت':
            wallets = api.get_agent_wallets()
            if wallets and 'result' in wallets:
                balance_info = '💰 أرصدة الوكيل:\n\n'
                for w in wallets['result']:
                    currency = w.get('currencyCode', w.get('currency', 'N/A'))
                    balance = w.get('balance', 0)
                    balance_info += f'💱 {currency}: {format_amount(balance)}\n'
                await update.message.reply_text(balance_info, reply_markup=owner_panel_keyboard())
            else:
                await update.message.reply_text('❌ فشل جلب الرصيد', reply_markup=owner_panel_keyboard())
            return

        # ── تعديل محفظة شام كاش ──
        if text == 'تعديل محفظة شام كاش':
            set_state(telegram_id, 'owner_edit_sham_wallet')
            current_wallet = get_sham_wallet()
            await update.message.reply_text(
                f'📱 المحفظة الحالية: `{current_wallet}`\n\nأرسل عنوان المحفظة الجديدة:',
                parse_mode='Markdown',
                reply_markup=cancel_keyboard()
            )
            return

        # ── تعديل كود شام كاش ──
        if text == 'تعديل كود شام كاش':
            set_state(telegram_id, 'owner_edit_syriatel_code')
            current_code = get_syriatel_code()
            await update.message.reply_text(
                f'📱 الكود الحالي: `{current_code}`\n\nأرسل الكود الجديد:',
                parse_mode='Markdown',
                reply_markup=cancel_keyboard()
            )
            return

        # ── الاذاعة ──
        if text == 'الاذاعة':
            set_state(telegram_id, 'owner_broadcast_msg')
            await update.message.reply_text('📢 أرسل رسالة الإذاعة (سيتم إرسالها لجميع اللاعبين المسجلين):', reply_markup=cancel_keyboard())
            return

    # ── Owner sub-states ──

    if current_state == 'owner_add_owner_id':
        try:
            new_owner_id = int(text)
            if new_owner_id not in OWNER_IDS:
                OWNER_IDS.append(new_owner_id)
            db_execute('INSERT OR REPLACE INTO admins VALUES (?, ?)', (new_owner_id, 'owner'))
            await update.message.reply_text(f'✅ تم إضافة المالك: {new_owner_id}', reply_markup=owner_panel_keyboard())
        except ValueError:
            await update.message.reply_text('❌ أرسل ID صحيح')
            return
        set_state(telegram_id, 'owner_panel')
        return

    if current_state == 'owner_add_admin_id':
        try:
            new_admin_id = int(text)
            db_execute('INSERT OR REPLACE INTO admins VALUES (?, ?)', (new_admin_id, 'admin'))
            await update.message.reply_text(f'✅ تم إضافة المشرف: {new_admin_id}', reply_markup=owner_panel_keyboard())
        except ValueError:
            await update.message.reply_text('❌ أرسل ID صحيح')
            return
        set_state(telegram_id, 'owner_panel')
        return

    if current_state == 'owner_remove_admin_id':
        try:
            remove_id = int(text)
            if remove_id in OWNER_IDS:
                await update.message.reply_text('❌ لا يمكن إزالة مالك', reply_markup=owner_panel_keyboard())
            else:
                db_execute('DELETE FROM admins WHERE telegram_id = ? AND role != ?', (remove_id, 'owner'))
                await update.message.reply_text(f'✅ تم إزالة المشرف: {remove_id}', reply_markup=owner_panel_keyboard())
        except ValueError:
            await update.message.reply_text('❌ أرسل ID صحيح')
            return
        set_state(telegram_id, 'owner_panel')
        return

    if current_state == 'owner_edit_sham_wallet':
        db_execute('UPDATE config SET value = ? WHERE key = ?', (text, 'sham_cash_wallet'))
        await update.message.reply_text(f'✅ تم تحديث محفظة شام كاش: `{text}`', parse_mode='Markdown', reply_markup=owner_panel_keyboard())
        set_state(telegram_id, 'owner_panel')
        return

    if current_state == 'owner_edit_syriatel_code':
        db_execute('UPDATE config SET value = ? WHERE key = ?', (text, 'syriatel_cash_code'))
        await update.message.reply_text(f'✅ تم تحديث كود سيرياتيل كاش: `{text}`', parse_mode='Markdown', reply_markup=owner_panel_keyboard())
        set_state(telegram_id, 'owner_panel')
        return

    if current_state == 'owner_broadcast_msg':
        # Get all registered players
        players = db_fetch('SELECT telegram_id FROM players WHERE player_id IS NOT NULL')
        sent = 0
        failed = 0
        for (tid,) in players:
            try:
                await context.bot.send_message(chat_id=tid, text=f'📢 إذاعة:\n\n{text}')
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f'📢 تم إرسال الإذاعة:\n✅ نجح: {sent}\n❌ فشل: {failed}',
            reply_markup=owner_panel_keyboard()
        )
        set_state(telegram_id, 'owner_panel')
        return


async def callback_handler(update: Update, context):
    """Handle inline keyboard callbacks (approve/reject)."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    telegram_id = query.from_user.id
    
    # Only admins can approve/reject
    if not is_admin(telegram_id):
        await query.answer('⛔ غير مصرح', show_alert=True)
        return
    
    parts = data.split('_')
    action = parts[0]  # approve or reject
    tx_type = parts[1]  # dep or wd
    player_tid = int(parts[2])
    amount = int(parts[3])
    
    info = get_player_info(player_tid)
    if not info:
        await query.answer('❌ لم يتم العثور على اللاعب', show_alert=True)
        return
    
    player_id, username, _ = info
    
    if action == 'approve':
        if tx_type == 'dep':
            # Deposit to player
            result = api.deposit_to_player(player_id, amount, f'إيداع من البوت - موافقة الإدارة')
            if result and 'result' in result:
                await context.bot.send_message(
                    chat_id=player_tid,
                    text=f'✅ تم الموافقة على إيداعك بمبلغ {format_amount(amount)} SYP'
                )
                await query.answer('✅ تم الإيداع بنجاح', show_alert=True)
                # Update original message
                await query.edit_message_text(f'✅ تمت الموافقة - إيداع {format_amount(amount)} SYP للاعب {username}')
            else:
                error_msg = result.get('message', 'غير معروف') if isinstance(result, dict) else 'خطأ'
                await query.answer(f'❌ فشل الإيداع: {error_msg}', show_alert=True)
        elif tx_type == 'wd':
            # Withdraw from player
            result = api.withdraw_from_player(player_id, amount, f'سحب من البوت - موافقة الإدارة')
            if result and 'result' in result:
                net_amount = int(amount * (1 - WITHDRAW_FEE_PERCENT / 100))
                await context.bot.send_message(
                    chat_id=player_tid,
                    text=f'✅ تم الموافقة على سحبك بمبلغ {format_amount(amount)} SYP (صافي {format_amount(net_amount)} SYP)'
                )
                await query.answer('✅ تم السحب بنجاح', show_alert=True)
                await query.edit_message_text(f'✅ تمت الموافقة - سحب {format_amount(amount)} SYP من اللاعب {username}')
            else:
                error_msg = result.get('message', 'غير معروف') if isinstance(result, dict) else 'خطأ'
                await query.answer(f'❌ فشل السحب: {error_msg}', show_alert=True)
    
    elif action == 'reject':
        if tx_type == 'dep':
            await context.bot.send_message(
                chat_id=player_tid,
                text=f'❌ تم رفض طلب إيداعك بمبلغ {format_amount(amount)} SYP'
            )
            await query.answer('❌ تم الرفض', show_alert=True)
            await query.edit_message_text(f'❌ تم الرفض - إيداع {format_amount(amount)} SYP من اللاعب {username}')
        elif tx_type == 'wd':
            await context.bot.send_message(
                chat_id=player_tid,
                text=f'❌ تم رفض طلب سحبك بمبلغ {format_amount(amount)} SYP'
            )
            await query.answer('❌ تم الرفض', show_alert=True)
            await query.edit_message_text(f'❌ تم الرفض - سحب {format_amount(amount)} SYP من اللاعب {username}')


# ─── Flask App + Webhook ─────────────────────────────────────────────────────
app_flask = Flask(__name__)

# PTB v21+ Application — single initialization
ptb_app = None
ptb_loop = None


def init_ptb():
    """Initialize PTB Application once in background thread."""
    global ptb_app, ptb_loop
    
    ptb_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    
    # Register handlers
    ptb_app.add_handler(CommandHandler('start', start_cmd))
    ptb_app.add_handler(CommandHandler('panel', panel_cmd))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    ptb_app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Create event loop and initialize
    ptb_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ptb_loop)
    
    ptb_loop.run_until_complete(ptb_app.initialize())
    
    # Set webhook
    async def set_webhook():
        await ptb_app.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f'Webhook set to: {WEBHOOK_URL}')
    
    ptb_loop.run_until_complete(set_webhook())
    logger.info('PTB Application initialized successfully')


# Start PTB in background thread
ptb_thread = threading.Thread(target=init_ptb, daemon=True)
ptb_thread.start()

# Wait for initialization
import time as _time
_time.sleep(2)


@app_flask.route('/webhook', methods=['POST'])
def webhook():
    """Receive Telegram updates via webhook."""
    if ptb_app is None or ptb_loop is None:
        return jsonify({'error': 'Bot not initialized'}), 503
    
    try:
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, ptb_app.bot)
        
        # Feed update to PTB in the running event loop
        future = asyncio.run_coroutine_threadsafe(
            ptb_app.process_update(update),
            ptb_loop
        )
        # Wait for processing (with timeout)
        future.result(timeout=30)
        
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f'Webhook error: {e}')
        return jsonify({'error': str(e)}), 500


@app_flask.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'api_authenticated': api.is_authenticated(),
        'bot_initialized': ptb_app is not None,
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    db_init()
    app_flask.run(host='0.0.0.0', port=PORT)
else:
    db_init()
