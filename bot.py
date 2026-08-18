import os
import json
import random
import string
import threading
import logging
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, jsonify
import requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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
# Agent API Client
# ═══════════════════════════════════════════════════════════════
class AgentAPI:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self._lock = threading.Lock()
        self._login()

    def _login(self):
        try:
            resp = requests.post(
                f'{API_BASE}signIn',
                json={'username': AGENT_USERNAME, 'password': AGENT_PASSWORD},
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get('result', {}).get('accessToken')
                self.refresh_token = data.get('result', {}).get('refreshToken')
                if self.access_token:
                    logger.info('✅ Agent API login successful')
                    return True
            logger.error('❌ Agent API login failed: %s', resp.text)
            return False
        except Exception as e:
            logger.error('❌ Agent API login error: %s', e)
            return False

    def _refresh(self):
        try:
            resp = requests.post(
                f'{API_BASE}refreshToken',
                json={'refreshToken': self.refresh_token},
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get('result', {}).get('accessToken')
                self.refresh_token = data.get('result', {}).get('refreshToken')
                if self.access_token:
                    logger.info('✅ Token refreshed successfully')
                    return True
            # Refresh failed, try full login
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
                    resp = requests.post(
                        f'{API_BASE}{endpoint}',
                        json=payload,
                        headers=self._headers(),
                        timeout=15
                    )
                    if resp.status_code == 401:
                        # Token expired, refresh and retry
                        if self._refresh():
                            continue
                        return None
                    return resp.json()
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
            msg = (
                f'📋 معلومات حسابك:\n\n'
                f'🆔 أيدي اللاعب: `{player[1]}`\n'
                f'👤 اسم المستخدم: `{player[2]}`\n'
                f'🔑 كلمة السر: `{player[3]}`'
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

    # ── Withdraw ──
    if data == 'withdraw':
        if not is_player(telegram_id):
            await query.edit_message_text('⚠️ يجب إنشاء حساب أولاً')
            return
        await query.edit_message_text(
            '📤 السحب\n\n'
            'اختر طريقة السحب:',
            reply_markup=withdraw_method_keyboard()
        )
        return

    # ── Withdraw: Sham Cash ──
    if data == 'withdraw_sham':
        set_state(telegram_id, 'awaiting_withdraw_amount', {'method': 'sham_cash'})
        await query.edit_message_text(
            f'⚠️ سيحسم مبلغ {WITHDRAW_FEE_PERCENT}% من عملية السحب\n\n'
            f'اكتب المبلغ المراد سحبه:\n'
            f'(الحد الأدنى: {WITHDRAW_MIN:,} {CURRENCY} | الحد الأقصى: {WITHDRAW_MAX:,} {CURRENCY})',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='withdraw')]])
        )
        return

    # ── Withdraw: Syriatel Cash ──
    if data == 'withdraw_syriatel':
        set_state(telegram_id, 'awaiting_withdraw_amount', {'method': 'syriatel_cash'})
        await query.edit_message_text(
            f'⚠️ سيحسم مبلغ {WITHDRAW_FEE_PERCENT}% من عملية السحب\n\n'
            f'اكتب المبلغ المراد سحبه:\n'
            f'(الحد الأدنى: {WITHDRAW_MIN:,} {CURRENCY} | الحد الأقصى: {WITHDRAW_MAX:,} {CURRENCY})',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='withdraw')]])
        )
        return

    # ── Support ──
    if data == 'support':
        set_state(telegram_id, 'support_chat')
        await query.edit_message_text(
            '🆘 الدعم الفني\n\n'
            'فريقنا في خدمتكم على مدار الساعة 🕐\n'
            'فقط اخبرنا بالمشكلة التي تواجهها:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]])
        )
        return

    # ── Owner Panel ──
    if data == 'owner_panel':
        if not is_owner(telegram_id):
            await query.edit_message_text('⛔ هذا القسم متاح فقط لمالك البوت')
            return
        await query.edit_message_text(
            '⚙️ قائمة تحكم البوت',
            reply_markup=owner_panel_keyboard()
        )
        return

    # ── Owner: Add Owner ──
    if data == 'add_owner':
        if not is_owner(telegram_id):
            return
        set_state(telegram_id, 'awaiting_add_owner')
        await query.edit_message_text(
            '👑 اضافة مالك جديد\n\n'
            'أرسل أيدي التليجرام الخاص بالشخص:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Owner: Add Admin ──
    if data == 'add_admin':
        if not is_owner(telegram_id):
            return
        set_state(telegram_id, 'awaiting_add_admin')
        await query.edit_message_text(
            '👤 اضافة مشرف جديد\n\n'
            'أرسل أيدي التليجرام الخاص بالشخص:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Owner: Remove Admin ──
    if data == 'remove_admin':
        if not is_owner(telegram_id):
            return
        admins = db_execute('SELECT telegram_id, role FROM admins', fetch=True)
        if not admins:
            await query.edit_message_text('لا يوجد مشرفين حالياً')
            return
        keyboard = []
        for admin_id, role in admins:
            if admin_id == OWNER_ID:
                continue
            label = '👑 مالك' if role == 'owner' else '👤 مشرف'
            keyboard.append([InlineKeyboardButton(f'{label} - {admin_id}', callback_data=f'remove_admin_{admin_id}')])
        keyboard.append([InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')])
        await query.edit_message_text(
            '❌ ازالة مشرف\n\n'
            'اختر المشرف الذي تريد إزالته:',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ── Owner: Remove Admin (specific) ──
    if data.startswith('remove_admin_'):
        if not is_owner(telegram_id):
            return
        target_id = int(data.split('_')[-1])
        db_execute('DELETE FROM admins WHERE telegram_id=?', (target_id,))
        await query.edit_message_text(
            f'✅ تم إزالة المشرف {target_id} بنجاح',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Owner: Bot Balance ──
    if data == 'bot_balance':
        if not is_owner(telegram_id):
            return
        try:
            result = api.get_agent_wallets()
            if result and result.get('status'):
                wallets = result.get('result', [])
                msg = '💰 أرصدة البوت:\n\n'
                for w in wallets:
                    if w.get('currencyCode') == CURRENCY:
                        msg += (
                            f'💱 العملة: {w.get("currencyCode")}\n'
                            f'💳 الرصيد: {w.get("balance", 0):,.2f}\n'
                            f'✅ المتاح: {w.get("availability", 0):,.2f}\n'
                            f'🎁 المكافأة: {w.get("bonus", 0):,.2f}\n'
                            f'❄️ المجمد: {w.get("frozenBalance", 0):,.2f}\n\n'
                        )
                if not msg.strip().endswith(':'):
                    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]]))
                else:
                    await query.edit_message_text('❌ لم يتم العثور على محفظة SYP', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]]))
            else:
                await query.edit_message_text('❌ فشل في جلب الرصيد', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]]))
        except Exception as e:
            logger.error('❌ Bot balance error: %s', e)
            await query.edit_message_text('❌ خطأ في جلب الرصيد', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]]))
        return

    # ── Owner: Edit Sham Cash Wallet ──
    if data == 'edit_sham_wallet':
        if not is_owner(telegram_id):
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

    # ── Owner: Edit Syriatel Code ──
    if data == 'edit_syriatel_code':
        if not is_owner(telegram_id):
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
            return
        set_state(telegram_id, 'awaiting_broadcast')
        await query.edit_message_text(
            '📢 الاذاعة\n\n'
            'أرسل الرسالة التي تريد بثها لجميع اللاعبين:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='owner_panel')]])
        )
        return

    # ── Admin: Approve Deposit ──
    if data.startswith('approve_deposit_'):
        pending_id = int(data.split('_')[-1])
        row = db_execute('SELECT * FROM pending_deposits WHERE id=? AND status=?', (pending_id, 'pending'), fetchone=True)
        if not row:
            await query.edit_message_text('❌ هذا الطلب تم معالجته مسبقاً')
            return
        player = get_player(row[1])
        if not player:
            await query.edit_message_text('❌ اللاعب غير موجود')
            return
        player_id = player[1]
        amount = row[2]
        method = row[3]
        result = api.deposit_to_player(player_id, amount, f'إيداع {method} - {row[4]}')
        if result and result.get('status'):
            db_execute('UPDATE pending_deposits SET status=? WHERE id=?', ('approved', pending_id))
            await query.edit_message_text(
                f'✅ تم إيداع {amount:,} {CURRENCY} في حساب اللاعب بنجاح'
            )
            try:
                await context.bot.send_message(
                    chat_id=row[1],
                    text=f'✅ تم إيداع {amount:,} {CURRENCY} في حسابك بنجاح!\n\n'
                         f'📌 طريقة الإيداع: {method}\n'
                         f'🔢 رقم العملية: {row[4]}'
                )
            except Exception as e:
                logger.error('❌ Notify player deposit error: %s', e)
        else:
            await query.edit_message_text(
                f'❌ فشل في إيداع المبلغ. النتيجة: {result}'
            )
        return

    # ── Admin: Reject Deposit ──
    if data.startswith('reject_deposit_'):
        pending_id = int(data.split('_')[-1])
        row = db_execute('SELECT * FROM pending_deposits WHERE id=? AND status=?', (pending_id, 'pending'), fetchone=True)
        if not row:
            await query.edit_message_text('❌ هذا الطلب تم معالجته مسبقاً')
            return
        db_execute('UPDATE pending_deposits SET status=? WHERE id=?', ('rejected', pending_id))
        await query.edit_message_text('❌ تم رفض طلب الإيداع')
        try:
            await context.bot.send_message(
                chat_id=row[1],
                text='❌ تم رفض طلب الإيداع. الرجاء التحقق من المعلومات والمحاولة مرة أخرى.'
            )
        except Exception as e:
            logger.error('❌ Notify player reject error: %s', e)
        return

    # ── Admin: Approve Withdrawal ──
    if data.startswith('approve_withdraw_'):
        pending_id = int(data.split('_')[-1])
        row = db_execute('SELECT * FROM pending_withdrawals WHERE id=? AND status=?', (pending_id, 'pending'), fetchone=True)
        if not row:
            await query.edit_message_text('❌ هذا الطلب تم معالجته مسبقاً')
            return
        player = get_player(row[1])
        if not player:
            await query.edit_message_text('❌ اللاعب غير موجود')
            return
        player_id = player[1]
        amount = row[2]
        method = row[3]
        wallet = row[4]
        # Calculate fee
        net_amount = amount
        result = api.withdraw_from_player(player_id, net_amount, f'سحب {method} - {wallet}')
        if result and result.get('status'):
            db_execute('UPDATE pending_withdrawals SET status=? WHERE id=?', ('approved', pending_id))
            await query.edit_message_text(
                f'✅ تم سحب {net_amount:,} {CURRENCY} من حساب اللاعب بنجاح'
            )
            try:
                await context.bot.send_message(
                    chat_id=row[1],
                    text=f'✅ تم سحب {net_amount:,} {CURRENCY} من حسابك بنجاح!\n\n'
                         f'📌 طريقة السحب: {method}\n'
                         f'📍 المحفظة: {wallet}'
                )
            except Exception as e:
                logger.error('❌ Notify player withdraw error: %s', e)
        else:
            await query.edit_message_text(
                f'❌ فشل في سحب المبلغ. النتيجة: {result}'
            )
        return

    # ── Admin: Reject Withdrawal ──
    if data.startswith('reject_withdraw_'):
        pending_id = int(data.split('_')[-1])
        row = db_execute('SELECT * FROM pending_withdrawals WHERE id=? AND status=?', (pending_id, 'pending'), fetchone=True)
        if not row:
            await query.edit_message_text('❌ هذا الطلب تم معالجته مسبقاً')
            return
        db_execute('UPDATE pending_withdrawals SET status=? WHERE id=?', ('rejected', pending_id))
        await query.edit_message_text('❌ تم رفض طلب السحب')
        try:
            await context.bot.send_message(
                chat_id=row[1],
                text='❌ تم رفض طلب السحب. الرجاء التحقق من المعلومات والمحاولة مرة أخرى.'
            )
        except Exception as e:
            logger.error('❌ Notify player reject error: %s', e)
        return


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = update.message.text
    state = get_state(telegram_id)

    if not state:
        return

    state_name = state['state']
    state_data = state['data']

    # ── Create Account: Username ──
    if state_name == 'awaiting_username':
        username = text.strip()
        set_state(telegram_id, 'awaiting_password', {'username': username})
        await update.message.reply_text(
            '🔐 أكتب كلمة السر التي تريدها:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back_main')]])
        )
        return

    # ── Create Account: Password ──
    if state_name == 'awaiting_password':
        username = state_data.get('username')
        password = text.strip()
        email = generate_random_email()

        result = api.register_player(username, password, email)
        if result and result.get('status'):
            # Get player ID from API
            player_search = api.get_players(search=username)
            player_id = None
            if player_search and player_search.get('status'):
                records = player_search.get('result', {}).get('records', [])
                for r in records:
                    if r.get('username', '').lower() == username.lower():
                        player_id = str(r.get('playerId'))
                        break

            if not player_id:
                player_id = str(result.get('result', ''))

            db_execute(
                'INSERT INTO players (telegram_id, player_id, username, password) VALUES (?, ?, ?, ?)',
                (telegram_id, player_id, username, password)
            )
            clear_state(telegram_id)
            await update.message.reply_text(
                f'✅ تم إنشاء حسابك بنجاح!\n\n'
                f'👤 اسم المستخدم: {username}\n'
                f'🔑 كلمة السر: {password}\n\n'
                f'يمكنك الآن استخدام جميع خدمات البوت 🎰',
                reply_markup=main_menu_keyboard(telegram_id)
            )
        else:
            error_msg = 'فشل في إنشاء الحساب'
            if result:
                notifs = result.get('notification', [])
                for n in notifs:
                    if n.get('content'):
                        error_msg = n['content']
                        break
            await update.message.reply_text(
                f'❌ {error_msg}\n\n'
                'الرجاء المحاولة مرة أخرى باسم مستخدم مختلف',
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
        set_state(telegram_id, 'awaiting_deposit_transaction', {'method': method, 'amount': amount, **state_data})

        if method == 'sham_cash':
            wallet = get_setting('sham_cash_wallet')
            await update.message.reply_text(
                f'📥 إيداع عبر شام كاش\n\n'
                f'💰 المبلغ: {amount:,} {CURRENCY}\n\n'
                f'أرسل الأموال إلى المحفظة التالية:\n'
                f'`{wallet}`\n\n'
                f'ثم أرسل رقم العملية:',
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='deposit')]])
            )
        else:
            code = get_setting('syriatel_cash_code')
            await update.message.reply_text(
                f'📥 إيداع عبر سيريتيل كاش\n\n'
                f'💰 المبلغ: {amount:,} {CURRENCY}\n\n'
                f'أرسل الأموال إلى الكود التالي:\n'
                f'`{code}`\n\n'
                f'ثم أرسل رقم العملية:',
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='deposit')]])
            )
        return

    # ── Deposit: Transaction ID ──
    if state_name == 'awaiting_deposit_transaction':
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


# ═══════════════════════════════════════════════════════════════
# Flask App + Webhook
# ═══════════════════════════════════════════════════════════════
app = Flask(__name__)

_telegram_app = None
_telegram_loop = None
_telegram_thread = None
_telegram_ready = threading.Event()

api = None

def _telegram_thread_main():
    global _telegram_app, _telegram_loop, api
    try:
        _telegram_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_telegram_loop)

        # Init API client
        api = AgentAPI()

        # Init database
        init_db()

        # Build Telegram app
        _telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Register handlers
        _telegram_app.add_handler(CommandHandler('start', start_command))
        _telegram_app.add_handler(CommandHandler('panel', lambda u, c: _show_owner_panel(u, c)))
        _telegram_app.add_handler(CallbackQueryHandler(button_handler))
        _telegram_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, message_handler))
        _telegram_app.add_handler(MessageHandler(filters.Chat(ADMIN_GROUP) & filters.REPLY, group_reply_handler))

        # Set webhook
        if WEBHOOK_URL:
            _telegram_loop.run_until_complete(
                _telegram_app.bot.set_webhook(url=WEBHOOK_URL)
            )
            logger.info('🔗 Webhook set to %s', WEBHOOK_URL)

        _telegram_ready.set()
        logger.info('✅ Telegram bot ready')
        _telegram_loop.run_forever()
    except Exception as e:
        logger.error('❌ Telegram thread crashed: %s', e)


async def _show_owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_owner(update.effective_user.id):
        await update.effective_message.reply_text(
            '⚙️ قائمة تحكم البوت',
            reply_markup=owner_panel_keyboard()
        )
    else:
        await update.effective_message.reply_text('⛔ هذا القسم متاح فقط لمالك البوت')


def _ensure_telegram():
    global _telegram_thread
    if _telegram_thread is not None and _telegram_thread.is_alive() and _telegram_ready.is_set():
        return
    if _telegram_thread is None or not _telegram_thread.is_alive():
        _telegram_ready.clear()
        _telegram_thread = threading.Thread(target=_telegram_thread_main, daemon=True)
        _telegram_thread.start()
        logger.info('🔄 Telegram thread started, waiting for readiness...')


# Fix: asyncio import needed
import asyncio


@app.route('/')
def home():
    _ensure_telegram()
    return '✅ Texas4Win Bot is online!'


@app.route('/health')
def health_check():
    _ensure_telegram()
    return jsonify({
        'status': 'healthy',
        'telegram_ready': _telegram_ready.is_set(),
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    _ensure_telegram()

    if not TELEGRAM_BOT_TOKEN:
        return 'Bot token missing', 500

    # Wait for the Telegram thread to become ready (up to 12 seconds)
    if not _telegram_ready.wait(timeout=12):
        logger.error('❌ Telegram thread still not ready after 12s')
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


@app.route('/deposit', methods=['POST'])
def handle_deposit():
    """External endpoint to notify bot about deposits."""
    return jsonify({'status': 'ok'})


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    _ensure_telegram()
    app.run(host='0.0.0.0', port=PORT)
