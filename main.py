import os
import re
import json
import time
import random
import logging
import threading
import base64
import html
from datetime import datetime
from flask import Flask, request, abort
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import functools, time as _time

def _retry(max_attempts=3, delay=1, backoff=2, max_delay=10):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            attempt, current_delay = 1, delay
            while True:
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt >= max_attempts:
                        raise
                    _time.sleep(min(current_delay, max_delay))
                    attempt += 1
                    current_delay *= backoff
        return wrapper
    return decorator

# =============================================================================
# Logging
# =============================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# =============================================================================
# Environment & Config
# =============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL", "https://your-render-app.onrender.com")
OWNER_ID = os.environ.get("OWNER_ID", "")
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
AGENT_USERNAME = os.environ.get("AGENT_USERNAME", "")
AGENT_PASSWORD = os.environ.get("AGENT_PASSWORD", "")
SHAM_CASH_WALLET = os.environ.get("SHAM_CASH_WALLET", "")
SYRIATEL_CASH_CODE = os.environ.get("SYRIATEL_CASH_CODE", "")
RESIDENTIAL_PROXY = os.environ.get("RESIDENTIAL_PROXY", "")
PROXY_LIST = [p.strip() for p in os.environ.get("PROXY_LIST", "").split(",") if p.strip()]
_BASE_PROXIES = []
if RESIDENTIAL_PROXY:
    _BASE_PROXIES.append(RESIDENTIAL_PROXY)
_BASE_PROXIES.extend(PROXY_LIST)

BASE_API = "https://agents.texas4win.com/"
OWNERS_FILE = "owners.json"
ADMINS_FILE = "admins.json"
USERS_FILE = "users.json"
PLAYERS_FILE = "players.json"

# =============================================================================
# Global State
# =============================================================================
access_token = None
refresh_token = None
agent_affiliate_id = None
owners_list = []
admins_list = []
users_list = set()
players_db = {}

user_states = {}
state_data = {}
pending_deposits = {}
pending_withdrawals = {}
active_support_replies = {}
support_tickets = {}

app = Flask(__name__)
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# =============================================================================
# Helpers
# =============================================================================
def load_json(file_path, default):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save {file_path}: {e}")

def load_owners():
    global owners_list
    owners_list = [str(x) for x in load_json(OWNERS_FILE, [])]

def load_admins():
    global admins_list
    admins_list = [str(x) for x in load_json(ADMINS_FILE, [])]

def load_users_list():
    global users_list
    users_list = set(str(x) for x in load_json(USERS_FILE, []))

def load_players_db():
    global players_db
    players_db = load_json(PLAYERS_FILE, {})

def save_players_db(data):
    save_json(PLAYERS_FILE, data)

def save_list_to_file(file_path, data):
    save_json(file_path, data)

def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding
            return json.loads(base64.b64decode(payload))
    except Exception as e:
        logger.error(f"JWT decode error: {e}")
    return {}

# =============================================================================
# Keyboard Markups
# =============================================================================
def main_menu_markup(uid):
    """Main menu using InlineKeyboardMarkup (appears at top of chat)."""
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("📝 تسجيل حساب", callback_data="menu_register"),
        InlineKeyboardButton("🎮 اللعب الآن", callback_data="menu_play"),
        InlineKeyboardButton("💰 إيداع", callback_data="menu_deposit"),
        InlineKeyboardButton("🏧 سحب", callback_data="menu_withdraw"),
        InlineKeyboardButton("📊 رصيدي", callback_data="menu_balance"),
        InlineKeyboardButton("📞 الدعم الفني", callback_data="menu_support"),
    ]
    if str(uid) in owners_list or str(uid) == str(OWNER_ID):
        buttons.append(InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="menu_admin"))
    markup.add(*buttons)
    return markup

def back_to_main_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="menu_back"))
    return markup

def admin_panel_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👤 بيانات الوكيل", callback_data="admin_agent_data"),
        InlineKeyboardButton("💰 رصيد الخزنة", callback_data="admin_balance"),
        InlineKeyboardButton("💳 محفظة شام", callback_data="admin_sham_wallet"),
        InlineKeyboardButton("📱 كود سيرياتيل", callback_data="admin_syriatel_code"),
        InlineKeyboardButton("📢 إذاعة", callback_data="admin_broadcast"),
        InlineKeyboardButton("➕ إضافة مالك", callback_data="admin_add_owner"),
        InlineKeyboardButton("➕ إضافة مشرف", callback_data="admin_add_admin"),
        InlineKeyboardButton("➖ إزالة مالك", callback_data="admin_remove_owner"),
        InlineKeyboardButton("➖ إزالة مشرف", callback_data="admin_remove_admin"),
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")
    )
    return markup

# =============================================================================
# API Request
# =============================================================================
import cloudscraper

# Try to import curl_cffi for better Cloudflare bypass
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
    logger.info("curl_cffi loaded — will use as primary fallback")
except Exception as e:
    CURL_CFFI_AVAILABLE = False
    logger.warning(f"curl_cffi not available: {e}")

# Cloudflare-aware session (reused across requests)
_scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

_proxy_rotation_index = 0

def _get_proxies(rotate=False):
    """Return proxy dict. If rotate=True, cycles through PROXY_LIST."""
    global _proxy_rotation_index
    if not _BASE_PROXIES:
        return {}
    if rotate and len(_BASE_PROXIES) > 1:
        proxy = _BASE_PROXIES[_proxy_rotation_index % len(_BASE_PROXIES)]
        _proxy_rotation_index += 1
    else:
        proxy = _BASE_PROXIES[0]
    return {"http": proxy, "https": proxy}

def _get_proxy_url():
    """Return current proxy URL string for logging."""
    proxies = _get_proxies()
    return proxies.get("http", "none") if proxies else "none"

# List of curl_cffi impersonations to try (in order)
CURL_CFFI_IMPERSONATIONS = ["chrome120", "chrome119", "chrome116", "chrome110", "chrome107"]

def _create_curl_session(impersonate="chrome120"):
    """Create a curl_cffi session with browser impersonation."""
    if not CURL_CFFI_AVAILABLE:
        return None
    try:
        session = curl_requests.Session(impersonate=impersonate)
        return session
    except Exception as e:
        logger.warning(f"curl_cffi impersonate '{impersonate}' failed: {e}")
        return None

def _request_with_curl_cffi(method, url, headers, payload, proxies, timeout=30):
    """Make request using curl_cffi with Chrome impersonation.
    Tries multiple impersonation profiles in order."""
    if not CURL_CFFI_AVAILABLE:
        return None
    last_error = None
    for impersonate in CURL_CFFI_IMPERSONATIONS:
        try:
            session = _create_curl_session(impersonate)
            if not session:
                continue
            kwargs = {"headers": headers, "timeout": timeout}
            if payload is not None:
                kwargs["json"] = payload
            if proxies:
                kwargs["proxies"] = proxies
            if method.upper() == "GET":
                resp = session.get(url, **kwargs)
            elif method.upper() == "POST":
                resp = session.post(url, **kwargs)
            else:
                resp = session.request(method, url, **kwargs)
            logger.info(f"curl_cffi success with impersonate={impersonate}, status={resp.status_code}")
            return resp
        except Exception as e:
            last_error = e
            logger.warning(f"curl_cffi impersonate '{impersonate}' request failed: {e}")
            continue
    if last_error:
        logger.error(f"curl_cffi all impersonations failed. Last error: {last_error}")
    return None

@_retry(max_attempts=3, delay=1, backoff=2, max_delay=10)
def api_request(method, endpoint, payload=None, auth=False, add_delay=True):
    global access_token

    url = f"{BASE_API}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Origin": "https://agents.texas4win.com",
        "Referer": "https://agents.texas4win.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    if add_delay:
        time.sleep(random.uniform(1, 3))

    logger.info(f"API {method} {url}")

    # -------------------------------------------------------------------------
    # Try all configured proxies + no-proxy (if none configured)
    # -------------------------------------------------------------------------
    proxy_candidates = []
    if _BASE_PROXIES:
        proxy_candidates = [p for p in _BASE_PROXIES]
    else:
        proxy_candidates = [None]  # no proxy

    for proxy_url in proxy_candidates:
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else {}
        proxy_label = proxy_url if proxy_url else "no-proxy"
        logger.info(f"Trying with proxy: {proxy_label}")

        # Strategy 1: curl_cffi with browser impersonation
        if CURL_CFFI_AVAILABLE:
            try:
                logger.info(f"  → curl_cffi + {proxy_label}")
                resp = _request_with_curl_cffi(method, url, headers, payload, proxies, timeout=30)
                if resp is not None:
                    if resp.status_code == 200:
                        logger.info(f"API response (curl_cffi/{proxy_label}): {resp.status_code}")
                        try:
                            return resp.json()
                        except Exception:
                            return {"__raw__": resp.text}
                    else:
                        logger.warning(f"  curl_cffi got {resp.status_code} via {proxy_label}")
            except Exception as e:
                logger.error(f"  curl_cffi error: {e}")

        # Strategy 2: cloudscraper (with proxy if available)
        try:
            logger.info(f"  → cloudscraper + {proxy_label}")
            resp = _scraper.request(method, url, json=payload, headers=headers, proxies=proxies, timeout=30)
            if resp.status_code == 200:
                logger.info(f"API response (cloudscraper/{proxy_label}): {resp.status_code}")
                try:
                    return resp.json()
                except Exception:
                    return {"__raw__": resp.text}
            elif resp.status_code == 403 and "cloudflare" in resp.text.lower():
                logger.warning(f"  Cloudflare block on cloudscraper, trying fresh session...")
                fresh_scraper = cloudscraper.create_scraper(
                    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
                )
                resp2 = fresh_scraper.request(method, url, json=payload, headers=headers, proxies=proxies, timeout=30)
                if resp2.status_code == 200:
                    logger.info(f"API response (fresh cloudscraper/{proxy_label}): {resp2.status_code}")
                    try:
                        return resp2.json()
                    except Exception:
                        return {"__raw__": resp2.text}
                else:
                    logger.warning(f"  Fresh cloudscraper also blocked: {resp2.status_code}")
        except Exception as e:
            logger.error(f"  cloudscraper error: {e}")

        # Strategy 3: plain requests with proxy
        if proxies:
            try:
                logger.info(f"  → requests + {proxy_label}")
                import requests
                resp = requests.request(method, url, json=payload, headers=headers, proxies=proxies, timeout=30)
                logger.info(f"API response (requests/{proxy_label}): {resp.status_code}")
                try:
                    return resp.json()
                except Exception:
                    return {"__raw__": resp.text}
            except Exception as e:
                logger.error(f"  requests+proxy error: {e}")

    # -------------------------------------------------------------------------
    # Auth refresh if we got 401/403 (non-Cloudflare) with best proxy
    # -------------------------------------------------------------------------
    if auth and access_token:
        logger.warning("Auth failed, re-signing in...")
        if do_signin():
            headers["Authorization"] = f"Bearer {access_token}"
            # Try first proxy again after re-signin
            best_proxy = _get_proxies()
            if CURL_CFFI_AVAILABLE:
                try:
                    resp = _request_with_curl_cffi(method, url, headers, payload, best_proxy, timeout=30)
                    if resp is not None and resp.status_code == 200:
                        try:
                            return resp.json()
                        except Exception:
                            return {"__raw__": resp.text}
                except Exception:
                    pass
            try:
                resp = _scraper.request(method, url, json=payload, headers=headers, proxies=best_proxy, timeout=30)
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except Exception:
                        return {"__raw__": resp.text}
            except Exception as e:
                logger.error(f"Re-signin request error: {e}")
        else:
            logger.error("Re-signin failed")

    logger.error("=" * 60)
    logger.error("All request strategies failed on ALL proxies.")
    logger.error("Cloudflare is blocking this IP — add RESIDENTIAL_PROXY.")
    logger.error("Get a free proxy: https://www.webshare.io")
    logger.error("=" * 60)
    return None


def do_signin():
    global access_token, refresh_token
    if not AGENT_USERNAME or not AGENT_PASSWORD:
        logger.error("AGENT_USERNAME or AGENT_PASSWORD not set — cannot sign in.")
        return False

    payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
    logger.info(f"Signing in: {AGENT_USERNAME}")
    result = api_request("POST", "global/api/UserApi/signIn", payload)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        access_token = result["result"].get("accessToken")
        refresh_token = result["result"].get("refreshToken")
        logger.info("Signin OK")
        return True
    logger.error(f"Signin failed: {result}")
    return False


def get_agent_affiliate_id():
    global agent_affiliate_id
    HARDCODED = "2688288"
    if not access_token:
        if not do_signin():
            agent_affiliate_id = HARDCODED
            return agent_affiliate_id
    if access_token:
        jwt = decode_jwt_payload(access_token)
        for key in ["affiliateId", "userId", "id", "sub"]:
            if key in jwt and jwt[key]:
                val = str(jwt[key])
                if val == HARDCODED:
                    agent_affiliate_id = val
                    return agent_affiliate_id
    try:
        result = api_request("POST", "global/api/UserApi/getChildren", {}, auth=True)
        if result and result.get("status") and isinstance(result.get("result"), dict):
            val = str(result["result"].get("parentId", ""))
            if val and val != "0":
                agent_affiliate_id = val
                return agent_affiliate_id
    except Exception as e:
        logger.error(f"getChildren error: {e}")
    try:
        search_payload = {"start": 0, "limit": 1, "filter": {}, "isNextPage": False}
        players = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", search_payload, auth=True)
        if players and players.get("status") and isinstance(players.get("result"), dict):
            records = players["result"].get("records", [])
            if records:
                pid = records[0].get("parentId")
                if pid:
                    agent_affiliate_id = str(pid)
                    return agent_affiliate_id
    except Exception as e:
        logger.error(f"getPlayers error: {e}")
    agent_affiliate_id = HARDCODED
    return agent_affiliate_id


def token_refresh_loop():
    global access_token, refresh_token
    while True:
        time.sleep(45 * 60)
        if refresh_token:
            payload = {"refreshToken": refresh_token}
            result = api_request("POST", "global/api/UserApi/refreshToken", payload)
            if result and result.get("status") and isinstance(result.get("result"), dict):
                access_token = result["result"].get("accessToken")
                refresh_token = result["result"].get("refreshToken")
                logger.info("Token refreshed")
            else:
                logger.warning("Refresh failed, signing in again")
                do_signin()
        else:
            do_signin()

# =============================================================================
# Bot Handlers
# =============================================================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = str(message.from_user.id)
    users_list.add(uid)
    save_list_to_file(USERS_FILE, list(users_list))
    load_players_db()

    welcome = (
        "👋 <b>أهلاً بك في تكساس للربح!</b>\n\n"
        "🎰 <b>المنصة الأولى للألعاب والربح عبر الإنترنت.</b>\n\n"
        "يمكنك من خلال هذا البوت:\n"
        "• 📝 تسجيل حساب جديد\n"
        "• 🎮 الدخول واللعب مباشرة\n"
        "• 💰 إيداع رصيد\n"
        "• 🏧 سحب أرباحك\n"
        "• 📊 متابعة رصيدك\n"
        "• 📞 التواصل مع الدعم الفني\n\n"
        "اختر من القائمة أدناه للبدء:"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu_markup(uid))


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    uid = str(message.from_user.id)
    if uid not in owners_list and uid != str(OWNER_ID):
        bot.send_message(message.chat.id, "⛔️ لا يوجد لديك صلاحية.")
        return
    bot.send_message(message.chat.id, "🔧 <b>لوحة التحكم</b>", reply_markup=admin_panel_markup())


@bot.callback_query_handler(func=lambda call: call.data == "menu_back")
def cb_menu_back(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.from_user.id, "🔙 العودة للقائمة الرئيسية:", reply_markup=main_menu_markup(call.from_user.id))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "menu_register")
def cb_menu_register(call):
    uid = call.from_user.id
    player = players_db.get(str(uid))
    if player:
        bot.send_message(uid, f"✅ لديك حساب مسجل بالفعل.\n\n👤 اسم المستخدم: <b>{html.escape(player.get('username', ''))}</b>\n🔑 كلمة المرور: <tg-spoiler>{html.escape(player.get('password', ''))}</tg-spoiler>", reply_markup=back_to_main_markup())
    else:
        user_states[uid] = "WAITING_REGISTER_USERNAME"
        state_data[uid] = {}
        bot.send_message(uid, "👤 أرسل اسم المستخدم المطلوب:")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REGISTER_USERNAME")
def state_register_username(message):
    uid = message.from_user.id
    username = message.text.strip()
    if not username:
        bot.send_message(uid, "❌ اسم المستخدم فارغ. أرسل اسم مستخدم صالح:")
        return
    state_data[uid]["username"] = username
    user_states[uid] = "WAITING_REGISTER_PASSWORD"
    bot.send_message(uid, "🔒 أرسل كلمة المرور المطلوبة:")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REGISTER_PASSWORD")
def state_register_password(message):
    uid = message.from_user.id
    password = message.text.strip()
    if not password:
        bot.send_message(uid, "❌ كلمة المرور فارغة. أرسل كلمة مرور صالحة:")
        return

    username = state_data[uid].get("username", "")
    state_data[uid]["password"] = password
    user_states[uid] = "WAITING_REGISTER_PHONE"
    bot.send_message(uid, "📱 أرسل رقم الهاتف (مثال: 0941234567):")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REGISTER_PHONE")
def state_register_phone(message):
    uid = message.from_user.id
    phone = message.text.strip()
    if not phone:
        bot.send_message(uid, "❌ رقم الهاتف فارغ. أرسل رقم صالح:")
        return

    state_data[uid]["phone"] = phone
    user_states[uid] = "WAITING_REGISTER_CURRENCY"
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💵 USD", callback_data="curr_USD"),
        InlineKeyboardButton("💶 EUR", callback_data="curr_EUR"),
        InlineKeyboardButton("💴 TRY", callback_data="curr_TRY"),
    )
    bot.send_message(uid, "💱 اختر العملة:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("curr_"))
def cb_currency(call):
    uid = call.from_user.id
    currency = call.data.split("_")[1]
    state_data[uid]["currency"] = currency
    user_states[uid] = "WAITING_REGISTER_LANGUAGE"
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇹🇷 Turkish", callback_data="lang_tr"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🇦🇪 Arabic", callback_data="lang_ar"),
    )
    bot.send_message(uid, "🌐 اختر لغة الحساب:", reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def cb_language(call):
    uid = call.from_user.id
    lang = call.data.split("_")[1]
    state_data[uid]["language"] = lang

    affiliate_id = get_agent_affiliate_id()
    if not affiliate_id:
        bot.send_message(uid, "❌ تعذر الحصول على معرف الوكيل. يرجى المحاولة لاحقاً.", reply_markup=back_to_main_markup())
        user_states.pop(uid, None)
        bot.answer_callback_query(call.id)
        return

    payload = {
        "userName": state_data[uid]["username"],
        "password": state_data[uid]["password"],
        "phone": state_data[uid]["phone"],
        "currency": state_data[uid]["currency"],
        "language": lang,
        "affiliateId": int(affiliate_id),
    }

    result = api_request("POST", "global/api/UserApi/signUp", payload)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        player_id = result["result"].get("playerId")
        players_db[str(uid)] = {
            "username": state_data[uid]["username"],
            "password": state_data[uid]["password"],
            "player_id": player_id,
            "currency": state_data[uid]["currency"],
            "language": lang,
        }
        save_players_db(players_db)
        bot.send_message(
            uid,
            f"✅ <b>تم إنشاء الحساب بنجاح!</b>\n\n"
            f"👤 اسم المستخدم: <b>{html.escape(state_data[uid]['username'])}</b>\n"
            f"🔑 كلمة المرور: <tg-spoiler>{html.escape(state_data[uid]['password'])}</tg-spoiler>\n"
            f"💱 العملة: {state_data[uid]['currency']}\n"
            f"🌐 اللغة: {lang.upper()}",
            reply_markup=back_to_main_markup()
        )
    else:
        error = "Unknown error"
        if result and result.get("notification"):
            error = result["notification"][0].get("content", "Unknown error")
        bot.send_message(uid, f"❌ فشل في التسجيل: {error}", reply_markup=back_to_main_markup())

    user_states.pop(uid, None)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "menu_play")
def cb_menu_play(call):
    uid = call.from_user.id
    player = players_db.get(str(uid))
    if not player:
        bot.send_message(uid, "❌ ليس لديك حساب مسجل. استخدم 📝 تسجيل حساب أولاً.", reply_markup=back_to_main_markup())
        bot.answer_callback_query(call.id)
        return
    token = access_token
    if not token:
        bot.send_message(uid, "⏳ جاري تجهيز الرابط...")
        if not do_signin():
            bot.send_message(uid, "❌ فشل في تسجيل الدخول. حاول لاحقاً.")
            bot.answer_callback_query(call.id)
            return
        token = access_token
    payload = {
        "playerId": player["player_id"],
        "language": player.get("language", "ar"),
        "returnUrl": "https://texas4win.com",
    }
    result = api_request("POST", "global/api/UserApi/getAuthTokenForPlayer", payload, auth=True)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        player_token = result["result"].get("authToken")
        if player_token:
            link = f"https://texas4win.com/auth?token={player_token}"
            bot.send_message(uid, f"🎮 <b>رابط الدخول للعبة:</b>\n\n<a href='{link}'>اضغط هنا للعب</a>", reply_markup=back_to_main_markup())
        else:
            bot.send_message(uid, "❌ فشل في الحصول على رابط اللعب.", reply_markup=back_to_main_markup())
    else:
        bot.send_message(uid, "❌ فشل في الحصول على رابط اللعب.", reply_markup=back_to_main_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "menu_balance")
def cb_menu_balance(call):
    uid = call.from_user.id
    player = players_db.get(str(uid))
    if not player:
        bot.send_message(uid, "❌ ليس لديك حساب مسجل. استخدم 📝 تسجيل حساب أولاً.", reply_markup=back_to_main_markup())
        bot.answer_callback_query(call.id)
        return
    if not access_token:
        do_signin()
    payload = {
        "start": 0,
        "limit": 1,
        "filter": {"search": player["username"]},
        "isNextPage": False,
    }
    result = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", payload, auth=True)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        records = result["result"].get("records", [])
        if records:
            bal = records[0].get("balance", 0)
            bonus = records[0].get("bonus", 0)
            currency = player.get("currency", "EUR")
            bot.send_message(uid, f"📊 <b>رصيدك:</b>\n\n💵 الرصيد: {bal} {currency}\n🎁 البونص: {bonus} {currency}", reply_markup=back_to_main_markup())
        else:
            bot.send_message(uid, "❌ لم يتم العثور على بيانات الرصيد.", reply_markup=back_to_main_markup())
    else:
        bot.send_message(uid, "❌ فشل في جلب الرصيد.", reply_markup=back_to_main_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "menu_deposit")
def cb_menu_deposit(call):
    uid = call.from_user.id
    player = players_db.get(str(uid))
    if not player:
        bot.send_message(uid, "❌ ليس لديك حساب مسجل. استخدم 📝 تسجيل حساب أولاً.", reply_markup=back_to_main_markup())
        bot.answer_callback_query(call.id)
        return
    user_states[uid] = "WAITING_DEPOSIT_AMOUNT"
    state_data[uid] = {}
    bot.send_message(uid, "💰 أرسل المبلغ الذي تريد إيداعه (رقم فقط):")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_DEPOSIT_AMOUNT")
def state_deposit_amount(message):
    uid = message.from_user.id
    text = message.text.strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        bot.send_message(uid, "❌ أرسل مبلغاً صالحاً (رقم فقط).")
        return
    state_data[uid]["deposit_amount"] = amount
    user_states[uid] = "WAITING_DEPOSIT_METHOD"
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💳 شام كاش", callback_data="dep_sham"),
        InlineKeyboardButton("📱 سيرياتيل كاش", callback_data="dep_syriatel")
    )
    bot.send_message(uid, "اختر طريقة الإيداع:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["dep_sham", "dep_syriatel"])
def cb_deposit_method(call):
    uid = call.from_user.id
    method = "sham" if call.data == "dep_sham" else "syriatel"
    state_data[uid]["deposit_method"] = method
    amount = state_data[uid].get("deposit_amount", 0)
    if method == "sham":
        msg = f"💳 <b>إيداع عبر شام كاش</b>\n\n💰 المبلغ: {amount}\n📋 المحفظة: <code>{html.escape(SHAM_CASH_WALLET)}</code>\n\nأرسل إيصال التحويل كـ صورة:"
    else:
        msg = f"📱 <b>إيداع عبر سيرياتيل كاش</b>\n\n💰 المبلغ: {amount}\n📋 الكود: <code>{html.escape(SYRIATEL_CASH_CODE)}</code>\n\nأرسل إيصال التحويل كـ صورة:"
    bot.send_message(uid, msg)
    user_states[uid] = "WAITING_DEPOSIT_RECEIPT"
    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=["photo"], func=lambda m: user_states.get(m.from_user.id) == "WAITING_DEPOSIT_RECEIPT")
def state_deposit_receipt(message):
    uid = message.from_user.id
    file_id = message.photo[-1].file_id
    amount = state_data[uid].get("deposit_amount", 0)
    caption = f"📥 <b>طلب إيداع جديد</b>\n\n👤 المستخدم: {uid}\n💰 المبلغ: {amount}\n\nأوافق / أرفض؟"
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ موافق", callback_data="approve_dep"),
        InlineKeyboardButton("❌ رفض", callback_data="reject_dep")
    )
    sent = bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption, reply_markup=markup)
    pending_deposits[sent.message_id] = {"user_id": uid, "amount": amount}
    bot.send_message(uid, "✅ تم إرسال الإيصال للمراجعة. سيتم إشعارك بالنتيجة.", reply_markup=main_menu_markup(uid))
    user_states.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data == "menu_withdraw")
def cb_menu_withdraw(call):
    uid = call.from_user.id
    player = players_db.get(str(uid))
    if not player:
        bot.send_message(uid, "❌ ليس لديك حساب مسجل. استخدم 📝 تسجيل حساب أولاً.", reply_markup=back_to_main_markup())
        bot.answer_callback_query(call.id)
        return
    user_states[uid] = "WAITING_WITHDRAW_AMOUNT"
    state_data[uid] = {}
    bot.send_message(uid, "🏧 أرسل المبلغ الذي تريد سحبه (رقم فقط):")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_WITHDRAW_AMOUNT")
def state_withdraw_amount(message):
    uid = message.from_user.id
    text = message.text.strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        bot.send_message(uid, "❌ أرسل مبلغاً صالحاً (رقم فقط).")
        return
    state_data[uid]["withdraw_amount"] = amount
    user_states[uid] = "WAITING_WITHDRAW_METHOD"
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💳 شام كاش", callback_data="wd_sham"),
        InlineKeyboardButton("📱 سيرياتيل كاش", callback_data="wd_syriatel")
    )
    bot.send_message(uid, "اختر طريقة السحب:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["wd_sham", "wd_syriatel"])
def cb_withdraw_method(call):
    uid = call.from_user.id
    method = "sham" if call.data == "wd_sham" else "syriatel"
    state_data[uid]["withdraw_method"] = method
    user_states[uid] = "WAITING_WITHDRAW_ACCOUNT"
    if method == "sham":
        bot.send_message(uid, "💳 أرسل رقم محفظة شام كاش:")
    else:
        bot.send_message(uid, "📱 أرسل رقم حساب سيرياتيل كاش:")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_WITHDRAW_ACCOUNT")
def state_withdraw_account(message):
    uid = message.from_user.id
    account = message.text.strip()
    if not account:
        bot.send_message(uid, "❌ الحساب فارغ. أرسل رقم صالح:")
        return
    amount = state_data[uid].get("withdraw_amount", 0)
    method = state_data[uid].get("withdraw_method", "")
    method_name = "شام كاش" if method == "sham" else "سيرياتيل كاش"
    text = f"📩 <b>طلب سحب جديد</b>\n\n👤 المستخدم: {uid}\n💰 المبلغ: {amount}\n💳 الطريقة: {method_name}\n🔢 الحساب: <code>{html.escape(account)}</code>\n\nأوافق / أرفض؟"
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ موافق", callback_data="approve_wd"),
        InlineKeyboardButton("❌ رفض", callback_data="reject_wd")
    )
    sent = bot.send_message(ADMIN_GROUP_ID, text, reply_markup=markup)
    pending_withdrawals[sent.message_id] = {"user_id": uid, "amount": amount}
    bot.send_message(uid, "✅ تم إرسال طلب السحب للمراجعة.", reply_markup=main_menu_markup(uid))
    user_states.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data == "menu_support")
def cb_menu_support(call):
    uid = call.from_user.id
    user_states[uid] = "WAITING_SUPPORT_MESSAGE"
    bot.send_message(uid, "📞 أرسل رسالتك لفريق الدعم الفني:")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_SUPPORT_MESSAGE")
def state_support_message(message):
    uid = message.from_user.id
    text = message.text.strip()
    if not text:
        bot.send_message(uid, "❌ الرسالة فارغة. أرسل رسالة صالحة:")
        return
    forward_text = f"📞 <b>رسالة دعم فني جديدة</b>\n\n👤 من المستخدم: {uid}\n💬 الرسالة:\n{html.escape(text)}\n\nاضغط على الزر أدناه للرد."
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✍️ رد على المستخدم", callback_data=f"reply_support_{uid}"))
    sent = bot.send_message(ADMIN_GROUP_ID, forward_text, reply_markup=markup)
    support_tickets[sent.message_id] = uid
    bot.send_message(uid, "✅ تم إرسال رسالتك لفريق الدعم. سيتم الرد عليك قريباً.", reply_markup=main_menu_markup(uid))
    user_states.pop(uid, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_support_"))
def cb_reply_support(call):
    uid = call.from_user.id
    target_uid = int(call.data.split("_")[-1])
    active_support_replies[uid] = target_uid
    bot.send_message(uid, f"✍️ أرسل رسالة الرد للمستخدم {target_uid} الآن:\n\n(ارسل 'إلغاء' للإلغاء)")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: active_support_replies.get(m.from_user.id))
def handle_support_reply(message):
    admin_id = message.from_user.id
    target_uid = active_support_replies.get(admin_id)
    text = message.text.strip()
    if text == "إلغاء":
        active_support_replies.pop(admin_id, None)
        bot.send_message(admin_id, "❌ تم إلغاء الرد.")
        return
    try:
        bot.send_message(target_uid, f"📩 رد من الدعم الفني:\n\n{html.escape(text)}")
        bot.send_message(admin_id, "✅ تم إرسال الرد.")
    except Exception as e:
        bot.send_message(admin_id, f"❌ فشل في إرسال الرد: {e}")
    active_support_replies.pop(admin_id, None)


@bot.callback_query_handler(func=lambda call: call.data == "menu_admin")
def cb_menu_admin(call):
    uid = str(call.from_user.id)
    if uid not in owners_list and uid != str(OWNER_ID):
        bot.answer_callback_query(call.id, "⛔️ ليس لديك صلاحية!")
        return
    bot.send_message(call.from_user.id, "🔧 <b>لوحة التحكم</b>", reply_markup=admin_panel_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_") or call.data.startswith("edit_"))
def cb_admin_panel(call):
    uid = str(call.from_user.id)
    if uid not in owners_list and uid != str(OWNER_ID):
        bot.answer_callback_query(call.id, "⛔️ ليس لديك صلاحية!")
        return

    data = call.data

    if data == "admin_agent_data":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("تعديل اسم المستخدم", callback_data="edit_agent_username"),
            InlineKeyboardButton("تعديل كلمة المرور", callback_data="edit_agent_password"),
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_back_to_menu")
        )
        bot.edit_message_text("💼 اختر ما تريد تعديله:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "edit_agent_username":
        user_states[call.from_user.id] = "WAITING_ADMIN_AGENT_USERNAME"
        bot.send_message(call.from_user.id, "📝 أرسل اسم المستخدم الجديد للوكيل:")

    elif data == "edit_agent_password":
        user_states[call.from_user.id] = "WAITING_ADMIN_AGENT_PASSWORD"
        bot.send_message(call.from_user.id, "🔒 أرسل كلمة المرور الجديدة للوكيل:")

    elif data == "admin_sham_wallet":
        user_states[call.from_user.id] = "WAITING_ADMIN_SHAM_WALLET"
        bot.send_message(call.from_user.id, "💰 أرسل عنوان محفظة شام كاش الجديد:")

    elif data == "admin_syriatel_code":
        user_states[call.from_user.id] = "WAITING_ADMIN_SYRIATEL_CODE"
        bot.send_message(call.from_user.id, "📱 أرسل كود سيرياتيل كاش الجديد:")

    elif data == "admin_balance":
        result = api_request("POST", "global/api/UserApi/getAgentAllWallets", {}, auth=True)
        if result and result.get("status") and result.get("result"):
            balances = result["result"]
            text = "📊 <b>أرصدة الخزنة الحالية:</b>\n\n"
            for bal in balances:
                text += f"💵 {bal.get('currencyName', 'Unknown')} ({bal.get('currencyCode', 'N/A')}):\n"
                text += f"   الرصيد: {bal.get('balance', 0)}\n"
                text += f"   المتاح: {bal.get('availability', 0)}\n"
                text += f"   البونص: {bal.get('bonus', 0)}\n\n"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("❌ فشل في جلب الأرصدة.", call.message.chat.id, call.message.message_id)

    elif data == "admin_broadcast":
        user_states[call.from_user.id] = "WAITING_ADMIN_BROADCAST"
        bot.send_message(call.from_user.id, "📢 أرسل الرسالة التي تريد بثها للجميع:")

    elif data == "admin_add_owner":
        user_states[call.from_user.id] = "WAITING_ADMIN_ADD_OWNER"
        bot.send_message(call.from_user.id, "➕ أرسل معرف المستخدم (User ID) للمالك الجديد:")

    elif data == "admin_add_admin":
        user_states[call.from_user.id] = "WAITING_ADMIN_ADD_ADMIN"
        bot.send_message(call.from_user.id, "➕ أرسل معرف المستخدم (User ID) للمشرف الجديد:")

    elif data == "admin_remove_owner":
        user_states[call.from_user.id] = "WAITING_ADMIN_REMOVE_OWNER"
        current = "\n".join(owners_list) if owners_list else "(لا يوجد مالكين)"
        bot.send_message(call.from_user.id, f"➖ أرسل معرف المستخدم للمالك المراد إزالته.\n\nالمالكين الحاليين:\n{current}")

    elif data == "admin_remove_admin":
        user_states[call.from_user.id] = "WAITING_ADMIN_REMOVE_ADMIN"
        current = "\n".join(admins_list) if admins_list else "(لا يوجد مشرفين)"
        bot.send_message(call.from_user.id, f"➖ أرسل معرف المستخدم للمشرف المراد إزالته.\n\nالمشرفين الحاليين:\n{current}")

    elif data == "admin_back":
        bot.send_message(call.from_user.id, "🔙 تم إغلاق لوحة التحكم.", reply_markup=main_menu_markup(call.from_user.id))

    elif data == "admin_back_to_menu":
        bot.edit_message_text("🔧 <b>لوحة التحكم</b>", call.message.chat.id, call.message.message_id, reply_markup=admin_panel_markup())

    bot.answer_callback_query(call.id)


# Admin state handlers
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_AGENT_USERNAME")
def state_admin_agent_username(message):
    uid = message.from_user.id
    global AGENT_USERNAME
    AGENT_USERNAME = message.text.strip()
    bot.send_message(uid, f"✅ تم تحديث اسم المستخدم للوكيل: {AGENT_USERNAME}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_AGENT_PASSWORD")
def state_admin_agent_password(message):
    uid = message.from_user.id
    global AGENT_PASSWORD
    AGENT_PASSWORD = message.text.strip()
    bot.send_message(uid, "✅ تم تحديث كلمة المرور للوكيل.")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_SHAM_WALLET")
def state_admin_sham_wallet(message):
    uid = message.from_user.id
    global SHAM_CASH_WALLET
    SHAM_CASH_WALLET = message.text.strip()
    bot.send_message(uid, f"✅ تم تحديث محفظة شام كاش: {SHAM_CASH_WALLET}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_SYRIATEL_CODE")
def state_admin_syriatel_code(message):
    uid = message.from_user.id
    global SYRIATEL_CASH_CODE
    SYRIATEL_CASH_CODE = message.text.strip()
    bot.send_message(uid, f"✅ تم تحديث كود سيرياتيل كاش: {SYRIATEL_CASH_CODE}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_BROADCAST")
def state_admin_broadcast(message):
    uid = message.from_user.id
    text = message.text.strip()
    if not text:
        bot.send_message(uid, "❌ الرسالة فارغة.")
        return
    count = 0
    for user_id in users_list:
        try:
            bot.send_message(int(user_id), f"📢 إذاعة:\n\n{html.escape(text)}")
            count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {user_id}: {e}")
    bot.send_message(uid, f"✅ تم إرسال الإذاعة إلى {count} مستخدم.")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_ADD_OWNER")
def state_admin_add_owner(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target in owners_list:
        bot.send_message(uid, "❌ المستخدم مالك بالفعل.")
    else:
        owners_list.append(target)
        save_list_to_file(OWNERS_FILE, owners_list)
        bot.send_message(uid, f"✅ تم إضافة المالك: {target}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_ADD_ADMIN")
def state_admin_add_admin(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target in admins_list:
        bot.send_message(uid, "❌ المستخدم مشرف بالفعل.")
    else:
        admins_list.append(target)
        save_list_to_file(ADMINS_FILE, admins_list)
        bot.send_message(uid, f"✅ تم إضافة المشرف: {target}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_REMOVE_OWNER")
def state_admin_remove_owner(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target == str(OWNER_ID):
        bot.send_message(uid, "❌ لا يمكن إزالة المالك الأساسي.")
    elif target in owners_list:
        owners_list.remove(target)
        save_list_to_file(OWNERS_FILE, owners_list)
        bot.send_message(uid, f"✅ تم إزالة المالك: {target}")
    else:
        bot.send_message(uid, "❌ المستخدم ليس مالكاً.")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_REMOVE_ADMIN")
def state_admin_remove_admin(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target in admins_list:
        admins_list.remove(target)
        save_list_to_file(ADMINS_FILE, admins_list)
        bot.send_message(uid, f"✅ تم إزالة المشرف: {target}")
    else:
        bot.send_message(uid, "❌ المستخدم ليس مشرفاً.")
    user_states.pop(uid, None)


# Deposit / Withdraw approval callbacks
@bot.callback_query_handler(func=lambda call: call.data in ["approve_dep", "reject_dep"])
def cb_deposit_action(call):
    msg_id = call.message.message_id
    if msg_id not in pending_deposits:
        bot.answer_callback_query(call.id, "❌ طلب غير موجود أو تم معالجته.")
        return
    dep = pending_deposits.pop(msg_id)
    user_id = dep["user_id"]
    amount = dep["amount"]

    if call.data == "approve_dep":
        player_info = players_db.get(str(user_id))
        if not player_info:
            bot.send_message(call.message.chat.id, f"❌ لم يتم العثور على ربط حساب اللاعب للمستخدم {user_id}")
            bot.answer_callback_query(call.id)
            return
        player_id = player_info["player_id"]
        currency = player_info.get("currency", "EUR")
        payload = {
            "amount": float(amount),
            "comment": f"Deposit via bot for user {user_id}",
            "playerId": player_id,
            "currencyCode": currency,
            "currency": currency,
            "moneyStatus": 5
        }
        if not access_token:
            do_signin()
        result = api_request("POST", "global/api/UserApi/depositToPlayer", payload, auth=True)
        if result and result.get("status"):
            try:
                bot.send_message(user_id, f"✅ تم اعتماد إيصالك وشحن رصيدك بمبلغ {amount} {currency} بنجاح!")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                new_caption = call.message.caption + "\n\n✅ تمت المعالجة: معتمد وشحن."
                bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"Failed to edit deposit message: {e}")
        else:
            error_msg = "Unknown error"
            if result and result.get("notification"):
                error_msg = result["notification"][0].get("content", "Unknown error")
            bot.send_message(call.message.chat.id, f"❌ فشل في الشحن: {error_msg}")
    else:
        try:
            bot.send_message(user_id, "❌ تم رفض إيصال الإيداع. يرجى التواصل مع الدعم الفني.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            new_caption = call.message.caption + "\n\n❌ تمت المعالجة: مرفوض."
            bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"Failed to edit deposit message: {e}")
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data in ["approve_wd", "reject_wd"])
def cb_withdraw_action(call):
    msg_id = call.message.message_id
    if msg_id not in pending_withdrawals:
        bot.answer_callback_query(call.id, "❌ طلب غير موجود أو تم معالجته.")
        return
    wd = pending_withdrawals.pop(msg_id)
    user_id = wd["user_id"]
    amount = wd["amount"]

    if call.data == "approve_wd":
        player_info = players_db.get(str(user_id))
        if not player_info:
            bot.send_message(call.message.chat.id, f"❌ لم يتم العثور على ربط حساب اللاعب للمستخدم {user_id}")
            bot.answer_callback_query(call.id)
            return
        player_id = player_info["player_id"]
        currency = player_info.get("currency", "EUR")
        payload = {
            "amount": -float(amount),
            "comment": f"Withdraw via bot for user {user_id}",
            "playerId": player_id,
            "currencyCode": currency,
            "currency": currency,
            "moneyStatus": 5
        }
        if not access_token:
            do_signin()
        result = api_request("POST", "global/api/UserApi/withdrawFromPlayer", payload, auth=True)
        if result and result.get("status"):
            try:
                bot.send_message(user_id, "✅ تمت عملية السحب بنجاح! تم خصم المبلغ من رصيدك.")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                new_text = call.message.text + "\n\n✅ تمت المعالجة: تم التحويل والخصم."
                bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"Failed to edit withdraw message: {e}")
        else:
            error_msg = "Unknown error"
            if result and result.get("notification"):
                error_msg = result["notification"][0].get("content", "Unknown error")
            bot.send_message(call.message.chat.id, f"❌ فشل في الخصم: {error_msg}")
    else:
        try:
            bot.send_message(user_id, "❌ تم رفض طلب السحب. يرجى التواصل مع الدعم الفني.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            new_text = call.message.text + "\n\n❌ تمت المعالجة: مرفوض."
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"Failed to edit withdraw message: {e}")
    bot.answer_callback_query(call.id)


# =============================================================================
# Flask Webhook
# =============================================================================
@app.route(f"/{BOT_TOKEN}", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "Webhook active. Send POST for Telegram updates.", 200
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        abort(403)


@app.route("/")
def index():
    return "Bot is running!", 200


def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")


# =============================================================================
# Initialization (runs on module import — required for Gunicorn)
# =============================================================================
load_owners()
load_admins()
load_users_list()
load_players_db()

_proxy_warn_logged = False

logger.info(f"RESIDENTIAL_PROXY env: {'SET' if RESIDENTIAL_PROXY else 'NOT SET'}")
logger.info(f"PROXY_LIST env: {len(PROXY_LIST)} proxies configured")
logger.info(f"curl_cffi available: {CURL_CFFI_AVAILABLE}")
logger.info("Bot initialized. Starting...")

def _init_background():
    """Background initialization: signin + get affiliate ID."""
    global _proxy_warn_logged
    try:
        ok = do_signin()
        if ok:
            get_agent_affiliate_id()
        else:
            if not _proxy_warn_logged:
                _proxy_warn_logged = True
                logger.error(
                    "=" * 70 + "\n"
                    "  SIGNIN FAILED — Cloudflare is blocking your Render IP.\n"
                    "  The ONLY way to fix this is to add a RESIDENTIAL PROXY.\n\n"
                    "  1) Get a free proxy from https://www.webshare.io (free tier)\n"
                    "  2) In Render Dashboard → Environment → add:\n"
                    "     RESIDENTIAL_PROXY=http://user:pass@host:port\n"
                    "  3) Redeploy\n"
                    "=" * 70
                )
    except Exception as e:
        logger.error(f"Background init error: {e}")

init_thread = threading.Thread(target=_init_background, daemon=True)
init_thread.start()

refresh_thread = threading.Thread(target=token_refresh_loop, daemon=True)
refresh_thread.start()

set_webhook()
logger.info("Webhook set. Ready for updates.")

# =============================================================================
# Main (local dev only — Gunicorn ignores this block)
# =============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
