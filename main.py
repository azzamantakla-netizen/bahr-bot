import os
import json
import time
import threading
import logging
import base64
import random
import string
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

try:
    import tls_client
except Exception:
    tls_client = None

try:
    import requests
except Exception:
    requests = None

# =============================================================================
# Logging Setup
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Base Configuration
# =============================================================================
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
ADMIN_GROUP_ID = -1003983996094
PANEL_BASE = "https://agents.texas4win.com"
RENDER_URL = "https://bahr-bot-c3ac.onrender.com"

AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"
SHAM_CASH_WALLET = "a18758d5324eb7595d4463ca355ad221"
SYRIATEL_CASH_CODE = "481 22120"

OWNERS_FILE = "owners.txt"
ADMINS_FILE = "admins.txt"
USERS_FILE = "users.txt"
PLAYERS_DB_FILE = "players_db.json"

owners_list = []
admins_list = []
users_list = []

session = None
if tls_client:
    try:
        session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"tls_client Session failed: {e}")
        session = None
access_token = None
refresh_token = None
agent_affiliate_id = None

user_states = {}
state_data = {}
pending_deposits = {}
pending_withdrawals = {}
support_tickets = {}          # {msg_id_in_group: user_id}
active_support_replies = {}   # {admin_id: user_id}

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# =============================================================================
# File I/O
# =============================================================================
def load_list_from_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_list_to_file(filepath, data_list):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data_list:
            f.write(str(item) + "\n")


def load_owners():
    global owners_list
    owners_list = load_list_from_file(OWNERS_FILE)
    uid = str(OWNER_ID)
    if uid not in owners_list:
        owners_list.append(uid)
        save_list_to_file(OWNERS_FILE, owners_list)
    logger.info(f"Owners loaded: {owners_list}")


def load_admins():
    global admins_list
    admins_list = load_list_from_file(ADMINS_FILE)
    logger.info(f"Admins loaded: {admins_list}")


def load_users_list():
    global users_list
    users_list = load_list_from_file(USERS_FILE)
    logger.info(f"Users list loaded: {len(users_list)} users")


def add_user(user_id):
    uid = str(user_id)
    if uid not in users_list:
        users_list.append(uid)
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(uid + "\n")
        logger.info(f"New user added: {uid}")


def load_players_db():
    if os.path.exists(PLAYERS_DB_FILE):
        with open(PLAYERS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_players_db(data):
    with open(PLAYERS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


players_db = load_players_db()

# =============================================================================
# API Helpers
# =============================================================================
def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            decoded = base64.b64decode(payload_b64)
            return json.loads(decoded)
    except Exception as e:
        logger.error(f"JWT decode error: {e}")
    return {}


def _request_with_tls(url, headers, payload, method):
    if not session:
        return None
    try:
        if method.upper() == "GET":
            return session.get(url, headers=headers, timeout_seconds=30)
        else:
            return session.post(url, headers=headers, json=payload, timeout_seconds=30)
    except Exception as e:
        logger.warning(f"tls_client request failed: {e}")
        return None


def _request_with_requests(url, headers, payload, method):
    if not requests:
        return None
    try:
        if method.upper() == "GET":
            return requests.get(url, headers=headers, json=payload, timeout=30, verify=False)
        else:
            return requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
    except Exception as e:
        logger.warning(f"requests fallback failed: {e}")
        return None


class FakeResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def api_request(method, endpoint, payload=None, auth=False):
    url = f"{PANEL_BASE}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://agents.texas4win.com",
        "Referer": "https://agents.texas4win.com/dashboard"
    }
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    logger.info(f"API REQUEST: {method} {url} | auth={auth} | payload={json.dumps(payload, ensure_ascii=False)[:500]}")
    try:
        # Use requests first (reliable timeout), fallback to tls_client
        response = _request_with_requests(url, headers, payload, method)
        if response is None:
            response = _request_with_tls(url, headers, payload, method)
        if response is None:
            raise Exception("Both requests and tls_client failed to connect")

        # Auto-retry on auth failure
        if auth and response.status_code in (401, 403):
            logger.warning(f"Auth failed ({response.status_code}), attempting re-signin...")
            if do_signin():
                headers["Authorization"] = f"Bearer {access_token}"
                response = _request_with_requests(url, headers, payload, method)
                if response is None:
                    response = _request_with_tls(url, headers, payload, method)
                if response is None:
                    raise Exception("Both requests and tls_client failed on retry")
            else:
                logger.error("Re-signin failed after auth error.")

        logger.info(f"API RESPONSE status: {response.status_code}")
        logger.info(f"API RESPONSE text: {response.text[:2000]}")
        try:
            data = response.json()
            logger.info(f"API RESPONSE json: {json.dumps(data, ensure_ascii=False)[:1000]}")
            return data
        except Exception as e:
            logger.error(f"Non-JSON response: {e}")
            return {"__raw__": response.text}
    except Exception as e:
        logger.error(f"API request error: {e}")
        return None


def do_signin():
    global access_token, refresh_token
    payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
    logger.info(f"Signing in with username: {AGENT_USERNAME}")
    result = api_request("POST", "global/api/UserApi/signIn", payload)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        access_token = result["result"].get("accessToken")
        refresh_token = result["result"].get("refreshToken")
        logger.info(f"Sign in OK. Token prefix: {access_token[:30] if access_token else 'None'}...")
        return True
    logger.error(f"Sign in failed: {result}")
    return False


def get_agent_affiliate_id():
    global agent_affiliate_id
    # Hardcoded confirmed parentId
    HARDCODED_AFFILIATE_ID = "2688288"
    if not access_token:
        logger.warning("No access token, attempting signin first")
        if not do_signin():
            agent_affiliate_id = HARDCODED_AFFILIATE_ID
            return agent_affiliate_id
    if access_token:
        jwt_data = decode_jwt_payload(access_token)
        logger.info(f"JWT keys: {list(jwt_data.keys())}")
        for key in ["affiliateId", "userId", "id", "sub", "affiliate_id"]:
            if key in jwt_data and jwt_data[key]:
                val = str(jwt_data[key])
                if val == HARDCODED_AFFILIATE_ID:
                    agent_affiliate_id = val
                    logger.info(f"Agent affiliateId from JWT ({key}): {agent_affiliate_id}")
                    return agent_affiliate_id
    # Fallback 1: try to get from getChildren
    try:
        result = api_request("POST", "global/api/UserApi/getChildren", {}, auth=True)
        if result and result.get("status") and isinstance(result.get("result"), dict):
            val = str(result["result"].get("parentId", ""))
            if val and val != "0":
                agent_affiliate_id = val
                logger.info(f"Agent affiliateId from getChildren: {agent_affiliate_id}")
                return agent_affiliate_id
    except Exception as e:
        logger.error(f"getChildren error: {e}")
    # Fallback 2: try to get from first player in getPlayersForCurrentAgent
    try:
        search_payload = {
            "start": 0,
            "limit": 1,
            "filter": {},
            "isNextPage": False
        }
        players_result = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", search_payload, auth=True)
        logger.info(f"getPlayersForCurrentAgent affiliate fetch: {players_result}")
        if players_result and players_result.get("status") and isinstance(players_result.get("result"), dict):
            records = players_result["result"].get("records", [])
            if records and isinstance(records, list) and len(records) > 0:
                first_player = records[0]
                parent_id = first_player.get("parentId")
                if parent_id:
                    agent_affiliate_id = str(parent_id)
                    logger.info(f"Agent affiliateId from first player parentId: {agent_affiliate_id}")
                    return agent_affiliate_id
    except Exception as e:
        logger.error(f"Error fetching affiliate from players: {e}")
    # Final fallback: use hardcoded confirmed value
    agent_affiliate_id = HARDCODED_AFFILIATE_ID
    logger.info(f"Using hardcoded affiliateId: {agent_affiliate_id}")
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
# Keyboard Markups
# =============================================================================
def main_menu_markup(user_id):
    is_owner = str(user_id) == str(OWNER_ID) or str(user_id) in owners_list
    logger.info(f"main_menu_markup user_id={user_id} is_owner={is_owner} owners={owners_list}")
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("ðŸ‘¤ Ø­Ø³Ø§Ø¨ÙŠ"),
        KeyboardButton("ðŸ“¥ Ø¥ÙŠØ¯Ø§Ø¹ / Ø´Ø­Ù† Ø±ØµÙŠØ¯"),
        KeyboardButton("ðŸ“© Ø³Ø­Ø¨ Ø±ØµÙŠØ¯"),
        KeyboardButton("ðŸ“ž Ø§Ù„Ø¯Ø¹Ù… Ø§Ù„ÙÙ†ÙŠ")
    )
    if is_owner:
        markup.add(KeyboardButton("âš™ï¸ Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…"))
    return markup


def back_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("ðŸ”™ Ø±Ø¬ÙˆØ¹"))
    return markup

# =============================================================================
# Admin Panel
# =============================================================================
def show_admin_panel(chat_id, message_id=None):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("ðŸ’¼ ØªØ¹Ø¯ÙŠÙ„ Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ÙˆÙƒÙŠÙ„", callback_data="admin_agent_data"),
        InlineKeyboardButton("ðŸ’° ØªØ¹Ø¯ÙŠÙ„ Ù…Ø­ÙØ¸Ø© Ø´Ø§Ù… ÙƒØ§Ø´", callback_data="admin_sham_wallet"),
        InlineKeyboardButton("ðŸ“± ØªØ¹Ø¯ÙŠÙ„ ÙƒÙˆØ¯ Ø³ÙŠØ±ÙŠØ§ØªÙŠÙ„", callback_data="admin_syriatel_code"),
        InlineKeyboardButton("ðŸ“Š Ø±ØµÙŠØ¯ Ø§Ù„Ø®Ø²Ù†Ø© Ø§Ù„Ø­Ø§Ù„ÙŠ", callback_data="admin_balance"),
        InlineKeyboardButton("ðŸ“¢ Ø¥Ø°Ø§Ø¹Ø© Ø¹Ø§Ù…Ø©", callback_data="admin_broadcast"),
        InlineKeyboardButton("âž• Ø¥Ø¶Ø§ÙØ© Ù…Ø§Ù„ÙƒÙŠÙ†", callback_data="admin_add_owner"),
        InlineKeyboardButton("âž• Ø¥Ø¶Ø§ÙØ© Ù…Ø´Ø±ÙÙŠÙ†", callback_data="admin_add_admin"),
        InlineKeyboardButton("âž– Ø¥Ø²Ø§Ù„Ø© Ù…Ø§Ù„ÙƒÙŠÙ†", callback_data="admin_remove_owner"),
        InlineKeyboardButton("âž– Ø¥Ø²Ø§Ù„Ø© Ù…Ø´Ø±ÙÙŠÙ†", callback_data="admin_remove_admin"),
        InlineKeyboardButton("ðŸ”™ Ø±Ø¬ÙˆØ¹", callback_data="admin_back")
    )
    text = "âš™ï¸ Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ… Ø§Ù„Ø¹Ù„ÙŠØ§:"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

# =============================================================================
# Admin Group Handlers (REGISTERED FIRST - strict order matters!)
# =============================================================================

# 1. Exit active reply mode FIRST (highest priority)
@bot.message_handler(
    content_types=["text"],
    func=lambda m: (
        m.chat.id == ADMIN_GROUP_ID
        and m.from_user.id in active_support_replies
        and m.text is not None
        and m.text.strip() in ["ØªÙ…", "done", "Ø§Ù†Ù‡Ø§Ø¡", "Ø¥Ù†Ù‡Ø§Ø¡", "stop", "Ø®Ø±ÙˆØ¬"]
    )
)
def handle_admin_exit_reply_mode(message):
    admin_id = message.from_user.id
    logger.info(f"Admin {admin_id} exited reply mode.")
    del active_support_replies[admin_id]
    bot.send_message(ADMIN_GROUP_ID, f"ðŸ”š ØªÙ… Ø¥Ù†Ù‡Ø§Ø¡ ÙˆØ¶Ø¹ Ø§Ù„Ø±Ø¯ Ù„Ù„Ù…Ø´Ø±Ù {admin_id}.")


# 2. Reply to a support ticket message (accept ANY content type)
@bot.message_handler(
    content_types=["text", "photo", "video", "document", "audio", "voice", "video_note", "sticker", "animation"],
    func=lambda m: (
        m.chat.id == ADMIN_GROUP_ID
        and m.reply_to_message is not None
        and m.reply_to_message.message_id in support_tickets
    )
)
def handle_admin_group_reply(message):
    original_msg_id = message.reply_to_message.message_id
    user_id = support_tickets[original_msg_id]
    logger.info(f"Admin reply to ticket msg {original_msg_id} -> user {user_id}")
    try:
        bot.send_message(user_id, "ðŸ“© Ø±Ø¯ Ù…Ù† Ø§Ù„Ø¯Ø¹Ù… Ø§Ù„ÙÙ†ÙŠ:")
        try:
            bot.copy_message(user_id, ADMIN_GROUP_ID, message.message_id)
        except Exception as e:
            logger.warning(f"copy_message failed: {e}")
            bot.forward_message(user_id, ADMIN_GROUP_ID, message.message_id)
        bot.send_message(ADMIN_GROUP_ID, f"âœ… ØªÙ… Ø¥Ø±Ø³Ø§Ù„ Ø§Ù„Ø±Ø¯ Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù… {user_id}")
    except Exception as e:
        logger.error(f"Failed to send reply to {user_id}: {e}")
        bot.send_message(ADMIN_GROUP_ID, f"âŒ ÙØ´Ù„ Ø¥Ø±Ø³Ø§Ù„ Ø§Ù„Ø±Ø¯ Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù… {user_id}: {e}")


# 3. Active reply mode (any message while in active reply mode, but NOT a reply to support ticket)
@bot.message_handler(
    content_types=["text", "photo", "video", "document", "audio", "voice", "video_note", "sticker", "animation"],
    func=lambda m: (
        m.chat.id == ADMIN_GROUP_ID
        and m.from_user.id in active_support_replies
        and (m.reply_to_message is None or m.reply_to_message.message_id not in support_tickets)
    )
)
def handle_admin_active_reply(message):
    user_id = active_support_replies.get(message.from_user.id)
    if not user_id:
        return
    logger.info(f"Admin active reply to user {user_id}")
    try:
        bot.send_message(user_id, "ðŸ“© Ø±Ø¯ Ù…Ù† Ø§Ù„Ø¯Ø¹Ù… Ø§Ù„ÙÙ†ÙŠ:")
        try:
            bot.copy_message(user_id, ADMIN_GROUP_ID, message.message_id)
        except Exception as e:
            logger.warning(f"copy_message failed: {e}")
            bot.forward_message(user_id, ADMIN_GROUP_ID, message.message_id)
        bot.send_message(ADMIN_GROUP_ID, f"âœ… ØªÙ… Ø¥Ø±Ø³Ø§Ù„ Ø§Ù„Ø±Ø¯ Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù… {user_id}")
    except Exception as e:
        logger.error(f"Failed to send active reply to {user_id}: {e}")
        bot.send_message(ADMIN_GROUP_ID, f"âŒ ÙØ´Ù„ Ø¥Ø±Ø³Ø§Ù„ Ø§Ù„Ø±Ø¯ Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù… {user_id}: {e}")

# =============================================================================
# Commands
# =============================================================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    add_user(message.chat.id)
    welcome = (
        "Ù…Ø±Ø­Ø¨Ø§Ù‹ Ø¨Ùƒ ÙÙŠ Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø§Ø­ØªØ±Ø§ÙÙŠ ! ðŸŽ‰\n"
        "âš¡ï¸ Ù†Ø¸Ø§Ù… Ù…Ø¹Ø§Ù„Ø¬Ø© Ø§Ù„Ù…Ø¹Ø§Ù…Ù„Ø§Øª Ø§Ù„ØªÙ„Ù‚Ø§Ø¦ÙŠ Ù…Ø³ØªÙ‚Ø± ÙˆÙŠØ¹Ù…Ù„ Ø¨Ø£Ø¹Ù„Ù‰ ÙƒÙØ§Ø¡Ø©.\n"
        "ðŸ“‘ ÙŠÙ…ÙƒÙ†Ùƒ Ø§Ù„Ø¢Ù† Ø¥Ø¯Ø§Ø±Ø© Ø­Ø³Ø§Ø¨ÙƒØŒ Ø´Ø­Ù† Ø±ØµÙŠØ¯ÙƒØŒ Ø£Ùˆ Ø·Ù„Ø¨ Ø§Ù„Ø³Ø­Ø¨ ÙÙˆØ±Ø§Ù‹ Ø¨Ø¶ØºØ·Ø© Ø²Ø±.\n"
        "ðŸ”˜ ÙŠØ±Ø¬Ù‰ Ø§Ø®ØªÙŠØ§Ø± Ø§Ù„Ø¹Ù…Ù„ÙŠØ© Ø§Ù„Ù…Ø·Ù„ÙˆØ¨Ø© Ù…Ù† Ø§Ù„Ù‚Ø§Ø¦Ù…Ø© Ø£Ø¯Ù†Ø§Ù‡:"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu_markup(message.chat.id))


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if str(message.chat.id) not in owners_list and str(message.chat.id) != str(OWNER_ID):
        bot.send_message(message.chat.id, "â›”ï¸ Ù„ÙŠØ³ Ù„Ø¯ÙŠÙƒ ØµÙ„Ø§Ø­ÙŠØ© Ø§Ù„ÙˆØµÙˆÙ„.")
        return
    show_admin_panel(message.chat.id)

# =============================================================================
# Back Handler
# =============================================================================
@bot.message_handler(func=lambda m: m.text is not None and m.text == "ðŸ”™ Ø±Ø¬ÙˆØ¹")
def handle_back(message):
    user_states.pop(message.from_user.id, None)
    state_data.pop(message.from_user.id, None)
    bot.send_message(
        message.from_user.id,
        "ðŸ”™ ØªÙ… Ø§Ù„Ø¹ÙˆØ¯Ø© Ù„Ù„Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ©.",
        reply_markup=main_menu_markup(message.from_user.id)
    )

# =============================================================================
# Main Menu Handlers
# =============================================================================
@bot.message_handler(func=lambda m: m.text is not None and m.text == "ðŸ‘¤ Ø­Ø³Ø§Ø¨ÙŠ")
def menu_my_account(message):
    add_user(message.from_user.id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("ðŸ†• Ø¥Ù†Ø´Ø§Ø¡ Ø­Ø³Ø§Ø¨ Ø¬Ø¯ÙŠØ¯", callback_data="create_account"))
    markup.add(InlineKeyboardButton("ðŸ”™ Ø±Ø¬ÙˆØ¹", callback_data="back_to_main"))
    bot.send_message(message.chat.id, "ðŸ‘¤ Ø¥Ø¯Ø§Ø±Ø© Ø­Ø³Ø§Ø¨Ùƒ:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text is not None and m.text == "ðŸ“¥ Ø¥ÙŠØ¯Ø§Ø¹ / Ø´Ø­Ù† Ø±ØµÙŠØ¯")
def menu_deposit(message):
    add_user(message.from_user.id)
    user_states[message.from_user.id] = "WAITING_DEP_AMOUNT"
    bot.send_message(
        message.from_user.id,
        "ðŸ’° ÙŠØ±Ø¬Ù‰ ÙƒØªØ§Ø¨Ø© Ø§Ù„Ù…Ø¨Ù„Øº Ø§Ù„Ù…Ø±Ø§Ø¯ Ø´Ø­Ù†Ù‡ ÙˆØ§Ø¶ØºØ· Ø¥Ø±Ø³Ø§Ù„:",
        reply_markup=back_markup()
    )


@bot.message_handler(func=lambda m: m.text is not None and m.text == "ðŸ“© Ø³Ø­Ø¨ Ø±ØµÙŠØ¯")
def menu_withdraw(message):
    add_user(message.from_user.id)
    text = (
        "âš ï¸ <b>ØªÙ†Ø¨ÙŠÙ‡ Ø´Ø±ÙˆØ· Ø§Ù„Ø³Ø­Ø¨ Ø§Ù„ÙÙˆØ±ÙŠ:</b>\n"
        "â€¢ ÙŠØ±Ø¬Ù‰ Ø§Ù„Ø¹Ù„Ù… Ø£Ù†Ù‡ Ø³ÙŠØªÙ… Ø®ØµÙ… Ø¹Ù…ÙˆÙ„Ø© Ø¨Ù‚ÙŠÙ…Ø© <b>10%</b> ØªÙ„Ù‚Ø§Ø¦ÙŠØ§Ù‹ Ù…Ù† Ø§Ù„Ù…Ø¨Ù„Øº Ø§Ù„Ù…Ø³Ø­ÙˆØ¨.\n"
        "â€¢ Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ø¯Ù†Ù‰ Ù„Ù„Ø³Ø­Ø¨ Ù‡Ùˆ: <b>200,000</b> Ù„ÙŠØ±Ø©.\n"
        "â€¢ Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ø¹Ù„Ù‰ Ù„Ù„Ø³Ø­Ø¨ Ù‡Ùˆ: <b>1,000,000</b> Ù„ÙŠØ±Ø©."
    )
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("ðŸ’³ Ù…Ø­ÙØ¸Ø© Ø´Ø§Ù… ÙƒØ§Ø´", callback_data="wd_method:sham"),
        InlineKeyboardButton("ðŸ“± Ø³ÙŠØ±ÙŠØ§ØªÙŠÙ„ ÙƒØ§Ø´", callback_data="wd_method:syriatel"),
        InlineKeyboardButton("ðŸ”™ Ø±Ø¬ÙˆØ¹", callback_data="wd_back")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")


@bot.message_handler(func=lambda m: m.text is not None and m.text == "ðŸ“ž Ø§Ù„Ø¯Ø¹Ù… Ø§Ù„ÙÙ†ÙŠ")
def menu_support(message):
    add_user(message.from_user.id)
    user_states[message.from_user.id] = "WAITING_SUPPORT_TICKET"
    bot.send_message(
        message.from_user.id,
        "Ø£Ù†Øª Ø¨Ø£Ù…Ø§Ù†ØŒ ÙØ±ÙŠÙ‚Ù†Ø§ Ù…ÙˆØ¬ÙˆØ¯ Ø¨Ø¬Ø§Ù†Ø¨Ùƒ Ø¹Ù„Ù‰ Ù…Ø¯Ø§Ø± Ø§Ù„Ø³Ø§Ø¹Ø© ÙÙ‚Ø· Ø£Ø®Ø¨Ø±Ù†Ø§ Ø¨Ù…Ø´ÙƒÙ„ØªÙƒ:",
        reply_markup=back_markup()
    )


@bot.message_handler(func=lambda m: m.text is not None and m.text == "âš™ï¸ Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…")
def menu_admin_panel(message):
    add_user(message.from_user.id)
    if str(message.from_user.id) not in owners_list and str(message.from_user.id) != str(OWNER_ID):
        bot.send_message(message.chat.id, "â›”ï¸ Ù„ÙŠØ³ Ù„Ø¯ÙŠÙƒ ØµÙ„Ø§Ø­ÙŠØ© Ø§Ù„ÙˆØµÙˆÙ„.")
        return
    show_admin_panel(message.chat.id)

# =============================================================================
# State: Registration
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REG_USERNAME" and m.text is not None)
def handle_reg_username(message):
    chat_id = message.chat.id
    logger.info(f"handle_reg_username TRIGGERED chat={chat_id}")
    if message.text == "ðŸ”™ Ø±Ø¬ÙˆØ¹":
        return
    username = message.text.strip()
    if not username or len(username) < 3:
        bot.send_message(chat_id, "âŒ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… Ù‚ØµÙŠØ± Ø¬Ø¯Ø§Ù‹.")
        return
    state_data[message.from_user.id] = {"username": username}
    user_states[message.from_user.id] = "WAITING_REG_PASSWORD"
    bot.send_message(chat_id, "ðŸ”’ ÙŠØ±Ø¬Ù‰ Ø¥Ø±Ø³Ø§Ù„ ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±:", reply_markup=back_markup())


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REG_PASSWORD" and m.text is not None)
def handle_reg_password(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    logger.info(f"handle_reg_password TRIGGERED chat={chat_id} user={user_id} text_len={len(message.text)}")
    if message.text == "ðŸ”™ Ø±Ø¬ÙˆØ¹":
        return
    try:
        password = message.text.strip()
        if not password:
            bot.send_message(chat_id, "âŒ ÙŠØ±Ø¬Ù‰ Ø¥Ø¯Ø®Ø§Ù„ ÙƒÙ„Ù…Ø© Ø³Ø± ØµØ§Ù„Ø­Ø©.")
            return

        username = state_data.get(user_id, {}).get("username")
        logger.info(f"Reg data: username={username}")
        if not username:
            bot.send_message(chat_id, "âŒ Ø®Ø·Ø£ ÙÙŠ Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª. Ø§Ø¶ØºØ· /start ÙˆØ£Ø¹Ø¯ Ø§Ù„Ù…Ø­Ø§ÙˆÙ„Ø©.")
            return

        # Show processing message
        bot.send_message(chat_id, "â³ Ø¬Ø§Ø±ÙŠ Ù…Ø¹Ø§Ù„Ø¬Ø© Ø§Ù„Ø¹Ù…Ù„ÙŠØ©... Ø§Ù„Ø±Ø¬Ø§Ø¡ Ø§Ù„Ø§Ù†ØªØ¸Ø§Ø±")

        # Ensure we have a valid affiliate_id
        if not agent_affiliate_id or agent_affiliate_id == "0":
            logger.info("affiliate_id missing or zero, fetching...")
            try:
                get_agent_affiliate_id()
            except Exception as e:
                logger.error(f"get_agent_affiliate_id failed: {e}")

        parent_id = agent_affiliate_id if agent_affiliate_id else "2688288"

        # Generate random email to avoid conflicts
        rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        email = f"{username}.{rand_suffix}@player.bot"

        logger.info(f"Registering player. username={username}, email={email}, parentId={parent_id}, token_exists={bool(access_token)}")

        payload = {
            "player": {
                "login": username,
                "email": email,
                "password": password,
                "parentId": str(parent_id)
            }
        }

        result = api_request("POST", "global/api/Player/registerPlayer", payload, auth=True)
        logger.info(f"registerPlayer result: {result}")

        if result and result.get("status"):
            reg_result = result.get("result")
            player_id = None
            currency = "EUR"

            if isinstance(reg_result, dict):
                player_id = str(reg_result.get("playerId") or reg_result.get("id") or reg_result.get("userId") or "")
            elif isinstance(reg_result, (int, str)):
                player_id = str(reg_result)

            if not player_id or player_id == "None":
                logger.info("Player ID not in register result, searching via getPlayersForCurrentAgent...")
                time.sleep(1.5)
                search_payload = {
                    "start": 0,
                    "limit": 20,
                    "filter": {
                        "withoutTotalCount": {"action": "=", "value": True},
                        "userName": {"action": "=", "value": username, "valueLabel": username}
                    },
                    "isNextPage": False
                }
                search_result = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", search_payload, auth=True)
                logger.info(f"getPlayersForCurrentAgent result: {search_result}")
                if search_result and search_result.get("result") and search_result["result"].get("records"):
                    player = search_result["result"]["records"][0]
                    player_id = str(player.get("playerId"))
                    currency = player.get("currency", "EUR")
                    logger.info(f"Player found via search: id={player_id}, currency={currency}")

            if player_id and player_id != "None":
                players_db[str(chat_id)] = {
                    "player_id": player_id,
                    "username": username,
                    "currency": currency
                }
                save_players_db(players_db)
                bot.send_message(
                    chat_id,
                    f"âœ… ØªÙ… Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„Ø­Ø³Ø§Ø¨ Ø¨Ù†Ø¬Ø§Ø­!\nðŸ†” Ù…Ø¹Ø±Ù Ø§Ù„Ù„Ø§Ø¹Ø¨: {player_id}\nðŸ’° Ø§Ù„Ø¹Ù…Ù„Ø©: {currency}",
                    reply_markup=main_menu_markup(chat_id)
                )
            else:
                bot.send_message(
                    chat_id,
                    "âš ï¸ ØªÙ… Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„Ø­Ø³Ø§Ø¨ Ù„ÙƒÙ† Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø§Ù„Ù…Ø¹Ø±Ù. Ø­Ø§ÙˆÙ„ Ù„Ø§Ø­Ù‚Ø§Ù‹ Ø£Ùˆ ØªÙˆØ§ØµÙ„ Ù…Ø¹ Ø§Ù„Ø¯Ø¹Ù….",
                    reply_markup=main_menu_markup(chat_id)
                )
        else:
            # Handle errors - detect if username is already taken
            error_msg = "Unknown error"
            raw_text = ""
            if result:
                notif = result.get("notification")
                if isinstance(notif, list) and len(notif) > 0:
                    error_msg = notif[0].get("content", "Unknown error")
                elif isinstance(notif, dict):
                    error_msg = notif.get("content", "Unknown error")
                if result.get("__raw__"):
                    raw_text = result["__raw__"]
                    error_msg += f" | Raw: {raw_text[:200]}"
            elif result is None:
                error_msg = "No response from server (network error)."

            # Check if error is about username already taken
            lower_err = (error_msg + " " + raw_text).lower()
            username_taken_keywords = [
                "already exists", "already taken", "duplicate", "exists", "used",
                "Ù…Ø³ØªØ®Ø¯Ù…", "Ù…ÙˆØ¬ÙˆØ¯", "Ù…ÙƒØ±Ø±", "taken", "existe", "user name", "username"
            ]
            is_username_taken = any(k in lower_err for k in username_taken_keywords)

            logger.error(f"Registration failed for {username}: is_username_taken={is_username_taken} | {result}")

            if is_username_taken:
                bot.send_message(
                    chat_id,
                    "âŒ Ù‡Ø°Ø§ Ø§Ù„Ø§Ø³Ù… Ù…Ø³ØªØ®Ø¯Ù… Ø¨Ø§Ù„ÙØ¹Ù„. ÙŠØ±Ø¬Ù‰ Ø§Ø®ØªÙŠØ§Ø± Ø§Ø³Ù… Ø¢Ø®Ø±.\nðŸ“ Ø§Ø¶ØºØ· Ø¹Ù„Ù‰ Ø²Ø± Ø¥Ù†Ø´Ø§Ø¡ Ø­Ø³Ø§Ø¨ ÙˆØ­Ø§ÙˆÙ„ Ù…Ø±Ø© Ø£Ø®Ø±Ù‰.",
                    reply_markup=main_menu_markup(chat_id)
                )
            else:
                bot.send_message(chat_id, f"âŒ ÙØ´Ù„ ÙÙŠ Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„Ø­Ø³Ø§Ø¨: {error_msg}")

        user_states.pop(user_id, None)
        state_data.pop(user_id, None)
    except Exception as e:
        logger.exception(f"CRITICAL ERROR in handle_reg_password: {e}")
        bot.send_message(chat_id, f"âŒ Ø­Ø¯Ø« Ø®Ø·Ø£ Ø¯Ø§Ø®Ù„ÙŠ: {e}")
        user_states.pop(user_id, None)
        state_data.pop(user_id, None)

# =============================================================================
# State: Deposit
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_DEP_AMOUNT" and m.text is not None)
def handle_dep_amount(message):
    if message.text == "ðŸ”™ Ø±Ø¬ÙˆØ¹":
        return
    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount <= 0:
            raise ValueError
        state_data[message.from_user.id] = {"amount": amount}
        user_states[message.from_user.id] = "WAITING_DEP_RECEIPT"
        text = (
            f"ðŸ’³ <b>Ø®ÙŠØ§Ø±Ø§Øª Ø§Ù„Ø¯ÙØ¹ Ø§Ù„Ù…ØªØ§Ø­Ø© Ù„Ø´Ø­Ù† Ø­Ø³Ø§Ø¨Ùƒ Ø­ÙŠØ§Ù‹:</b>\n"
            f"â€¢ <b>Ù…Ø­ÙØ¸Ø© Ø´Ø§Ù… ÙƒØ§Ø´</b>: {SHAM_CASH_WALLET}\n"
            f"â€¢ <b>ÙƒÙˆØ¯ Ø³ÙŠØ±ÙŠØ§ØªÙŠÙ„ ÙƒØ§Ø´</b>: {SYRIATEL_CASH_CODE}\n\n"
            f"âš ï¸ Ù‚Ù… Ø¨ØªØ­ÙˆÙŠÙ„ Ø§Ù„Ù…Ø¨Ù„Øº Ø§Ù„Ù…Ø·Ø§Ø¨Ù‚ ØªÙ…Ø§Ù…Ø§Ù‹ Ù„Ø·Ù„Ø¨ÙƒØŒ Ø«Ù… <b>Ù‚Ù… Ø¨Ø±ÙØ¹ ÙˆØ¥Ø±Ø³Ø§Ù„ ØµÙˆØ±Ø© Ø§Ù„Ø¥ÙŠØµØ§Ù„ Ù‡Ù†Ø§.</b>\n"
            f"âœ… Ø³ÙŠØªÙ… Ù…Ø±Ø§Ø¬Ø¹Ø© Ø¥ÙŠØµØ§Ù„Ùƒ ÙˆØ´Ø­Ù† Ø±ØµÙŠØ¯Ùƒ Ø®Ù„Ø§Ù„ Ø¯Ù‚Ø§Ø¦Ù‚."
        )
        bot.send_message(message.from_user.id, text, parse_mode="HTML", reply_markup=back_markup())
    except ValueError:
        bot.send_message(message.from_user.id, "âŒ ÙŠØ±Ø¬Ù‰ Ø¥Ø¯Ø®Ø§Ù„ Ù…Ø¨Ù„Øº ØµØ­ÙŠØ­.")


@bot.message_handler(content_types=["photo"], func=lambda m: user_states.get(m.from_user.id) == "WAITING_DEP_RECEIPT")
def handle_dep_receipt(message):
    user_id = message.from_user.id
    amount = state_data.get(user_id, {}).get("amount")
    if not amount:
        bot.send_message(user_id, "âŒ Ø®Ø·Ø£ ÙÙŠ Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª. Ø£Ø¹Ø¯ Ø§Ù„Ù…Ø­Ø§ÙˆÙ„Ø©.")
        return

    file_id = message.photo[-1].file_id
    caption = (
        f"ðŸ”„ <b>Ø·Ù„Ø¨ Ø¥ÙŠØ¯Ø§Ø¹ Ø¬Ø¯ÙŠØ¯</b>\n\n"
        f"ðŸ‘¤ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…: <code>{user_id}</code>\n"
        f"ðŸ’° Ø§Ù„Ù…Ø¨Ù„Øº: <b>{amount}</b>\n"
        f"ðŸ“Ž ØªÙ… Ø¥Ø±ÙØ§Ù‚ Ø¥ÙŠØµØ§Ù„ Ø§Ù„Ø¯ÙØ¹."
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("âœ… Ù…ÙˆØ§ÙÙ‚Ø©", callback_data="approve_dep"),
        InlineKeyboardButton("âŒ Ø±ÙØ¶", callback_data="reject_dep")
    )
    sent = bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
    pending_deposits[sent.message_id] = {"user_id": user_id, "amount": amount}
    bot.send_message(user_id, "ðŸ“¤ ØªÙ… Ø¥Ø±Ø³Ø§Ù„ Ø¥ÙŠØµØ§Ù„Ùƒ Ù„Ù„Ù…Ø±Ø§Ø¬Ø¹Ø©. Ø³ÙŠØªÙ… Ø¥Ø´Ø¹Ø§Ø±Ùƒ Ø¨Ø§Ù„Ù†ØªÙŠØ¬Ø©.", reply_markup=main_menu_markup(user_id))
    user_states.pop(user_id, None)
    state_data.pop(user_id, None)

# =============================================================================
# State: Withdraw
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_WITHDRAW_AMOUNT" and m.text is not None)
def handle_wd_amount(message):
    if message.text == "ðŸ”™ Ø±Ø¬ÙˆØ¹":
        return
    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount < 200000:
            bot.send_message(message.from_user.id, "âŒ Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ø¯Ù†Ù‰ Ù„Ù„Ø³Ø­Ø¨ Ù‡Ùˆ 200,000 Ù„ÙŠØ±Ø©.")
            return
        if amount > 1000000:
            bot.send_message(message.from_user.id, "âŒ Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ø¹Ù„Ù‰ Ù„Ù„Ø³Ø­Ø¨ Ù‡Ùˆ 1,000,000 Ù„ÙŠØ±Ø©.")
            return
        state_data[message.from_user.id]["amount"] = amount
        user_states[message.from_user.id] = "WAITING_WITHDRAW_PHONE"
        bot.send_message(
            message.from_user.id,
            "ðŸ“± ÙŠØ±Ø¬Ù‰ Ø¥Ø±Ø³Ø§Ù„ Ø±Ù‚Ù… Ù‡Ø§ØªÙÙƒ (Ù…Ø­ÙØ¸Ø© Ø´Ø§Ù… ÙƒØ§Ø´ Ø£Ùˆ Ø³ÙŠØ±ÙŠØ§ØªÙŠÙ„ ÙƒØ§Ø´):",
            reply_markup=back_markup()
        )
    except ValueError:
        bot.send_message(message.from_user.id, "âŒ ÙŠØ±Ø¬Ù‰ Ø¥Ø¯Ø®Ø§Ù„ Ù…Ø¨Ù„Øº ØµØ­ÙŠØ­.")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_WITHDRAW_PHONE" and m.text is not None)
def handle_wd_phone(message):
    if message.text == "ðŸ”™ Ø±Ø¬ÙˆØ¹":
        return
    phone = message.text.strip()
    if not phone:
        bot.send_message(message.from_user.id, "âŒ ÙŠØ±Ø¬Ù‰ Ø¥Ø±Ø³Ø§Ù„ Ø±Ù‚Ù… ØµØ­ÙŠØ­.")
        return
    state_data[message.from_user.id]["phone"] = phone
    user_states[message.from_user.id] = "WAITING_WITHDRAW_CONFIRM"
    amount = state_data[message.from_user.id].get("amount", 0)
    commission = amount * 0.10
    net = amount - commission
    text = (
        f"âš ï¸ <b>Ù…Ø±Ø§Ø¬Ø¹Ø© Ø·Ù„Ø¨ Ø§Ù„Ø³Ø­Ø¨:</b>\n\n"
        f"ðŸ’° Ø§Ù„Ù…Ø¨Ù„Øº: {amount}\n"
        f"ðŸ“‰ Ø§Ù„Ø¹Ù…ÙˆÙ„Ø© (10%): {commission}\n"
        f"ðŸ“¨ Ø§Ù„ØµØ§ÙÙŠ: {net}\n"
        f"ðŸ“± Ø§Ù„Ø±Ù‚Ù…: {phone}\n\n"
        f"âœ… Ø§Ø¶ØºØ· 'ØªØ£ÙƒÙŠØ¯' Ù„Ø¥Ø±Ø³Ø§Ù„ Ø§Ù„Ø·Ù„Ø¨."
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("âœ… ØªØ£ÙƒÙŠØ¯", callback_data="confirm_wd"),
        InlineKeyboardButton("âŒ Ø¥Ù„ØºØ§Ø¡", callback_data="cancel_wd")
    )
    bot.send_message(message.from_user.id, text, reply_markup=markup, parse_mode="HTML")

# =============================================================================
# State: Support
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_SUPPORT_TICKET" and m.text is not None)
def handle_support_ticket(message):
    if message.text == "ðŸ”™ Ø±Ø¬ÙˆØ¹":
        return
    ticket_text = message.text.strip()
    if not ticket_text:
        bot.send_message(message.from_user.id, "âŒ ÙŠØ±Ø¬Ù‰ ÙƒØªØ§Ø¨Ø© Ù†Øµ Ø§Ù„Ø±Ø³Ø§Ù„Ø©.")
        return
    caption = (
        f"ðŸ“© <b>ØªØ°ÙƒØ±Ø© Ø¯Ø¹Ù… ÙÙ†ÙŠ Ø¬Ø¯ÙŠØ¯Ø©</b>\n\n"
        f"ðŸ‘¤ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…: <code>{message.from_user.id}</code>\n"
        f"ðŸ“ Ø§Ù„Ø±Ø³Ø§Ù„Ø©:\n{ticket_text}"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("ðŸ“ Ø±Ø¯ Ø¹Ù„Ù‰ Ù‡Ø°Ø§ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…", callback_data=f"reply_support:{message.from_user.id}"))
    sent = bot.send_message(ADMIN_GROUP_ID, caption, reply_markup=markup, parse_mode="HTML")
    support_tickets[sent.message_id] = message.from_user.id
    bot.send_message(message.from_user.id, "âœ… ØªÙ… Ø¥Ø±Ø³Ø§Ù„ ØªØ°ÙƒØ±ØªÙƒ. Ø³ÙŠØªÙ… Ø§Ù„Ø±Ø¯ Ø¹Ù„ÙŠÙƒ Ù‚Ø±ÙŠØ¨Ø§Ù‹.", reply_markup=main_menu_markup(message.from_user.id))
    user_states.pop(message.from_user.id, None)

# =============================================================================
# State: Admin Panel States
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_AGENT_USERNAME" and m.text is not None)
def handle_admin_agent_username(message):
    global AGENT_USERNAME
    AGENT_USERNAME = message.text.strip()
    bot.send_message(message.from_user.id, f"âœ… ØªÙ… ØªØ­Ø¯ÙŠØ« Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…: {AGENT_USERNAME}")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_AGENT_PASSWORD" and m.text is not None)
def handle_admin_agent_password(message):
    global AGENT_PASSWORD
    AGENT_PASSWORD = message.text.strip()
    bot.send_message(message.from_user.id, "ðŸ”’ ØªÙ… ØªØ­Ø¯ÙŠØ« ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±. Ø¬Ø§Ø±ÙŠ Ø¥Ø¹Ø§Ø¯Ø© ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„...")
    if do_signin():
        get_agent_affiliate_id()
        bot.send_message(message.from_user.id, "âœ… ØªÙ… Ø¥Ø¹Ø§Ø¯Ø© ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„ Ø¨Ù†Ø¬Ø§Ø­.")
    else:
        bot.send_message(message.from_user.id, "âŒ ÙØ´Ù„ Ø¥Ø¹Ø§Ø¯Ø© ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„. ØªØ­Ù‚Ù‚ Ù…Ù† Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª.")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_SHAM_WALLET" and m.text is not None)
def handle_admin_sham_wallet(message):
    global SHAM_CASH_WALLET
    SHAM_CASH_WALLET = message.text.strip()
    bot.send_message(message.from_user.id, f"âœ… ØªÙ… ØªØ­Ø¯ÙŠØ« Ù…Ø­ÙØ¸Ø© Ø´Ø§Ù… ÙƒØ§Ø´: {SHAM_CASH_WALLET}")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_SYRIATEL_CODE" and m.text is not None)
def handle_admin_syriatel_code(message):
    global SYRIATEL_CASH_CODE
    SYRIATEL_CASH_CODE = message.text.strip()
    bot.send_message(message.from_user.id, f"âœ… ØªÙ… ØªØ­Ø¯ÙŠØ« ÙƒÙˆØ¯ Ø³ÙŠØ±ÙŠØ§ØªÙŠÙ„: {SYRIATEL_CASH_CODE}")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_BROADCAST" and m.text is not None)
def handle_admin_broadcast(message):
    text = message.text
    all_recipients = set(users_list + list(players_db.keys()) + owners_list + admins_list)
    success = 0
    failed = 0
    logger.info(f"Broadcasting to {len(all_recipients)} users...")
    for uid in all_recipients:
        try:
            bot.send_message(int(uid), f"ðŸ“¢ Ø¥Ø°Ø§Ø¹Ø©:\n\n{text}")
            success += 1
        except Exception as e:
            logger.error(f"Broadcast failed for {uid}: {e}")
            failed += 1
    bot.send_message(message.chat.id, f"âœ… ØªÙ… Ø§Ù„Ø¥Ø±Ø³Ø§Ù„: {success} | âŒ ÙØ´Ù„: {failed} | ðŸ“Š Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù…Ø´ØªØ±ÙƒÙŠÙ†: {len(all_recipients)}")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_ADD_OWNER" and m.text is not None)
def handle_admin_add_owner(message):
    uid = message.text.strip()
    if uid not in owners_list:
        owners_list.append(uid)
        save_list_to_file(OWNERS_FILE, owners_list)
    bot.send_message(message.from_user.id, f"âœ… ØªÙ…Øª Ø¥Ø¶Ø§ÙØ© Ø§Ù„Ù…Ø§Ù„Ùƒ: {uid}")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_ADD_ADMIN" and m.text is not None)
def handle_admin_add_admin(message):
    uid = message.text.strip()
    if uid not in admins_list:
        admins_list.append(uid)
        save_list_to_file(ADMINS_FILE, admins_list)
    bot.send_message(message.from_user.id, f"âœ… ØªÙ…Øª Ø¥Ø¶Ø§ÙØ© Ø§Ù„Ù…Ø´Ø±Ù: {uid}")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_REMOVE_OWNER" and m.text is not None)
def handle_admin_remove_owner(message):
    uid = message.text.strip()
    if uid in owners_list:
        owners_list.remove(uid)
        save_list_to_file(OWNERS_FILE, owners_list)
        bot.send_message(message.from_user.id, f"âœ… ØªÙ…Øª Ø¥Ø²Ø§Ù„Ø© Ø§Ù„Ù…Ø§Ù„Ùƒ: {uid}")
    else:
        bot.send_message(message.from_user.id, f"âŒ Ø§Ù„Ù…Ø§Ù„Ùƒ {uid} ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ ÙÙŠ Ø§Ù„Ù‚Ø§Ø¦Ù…Ø©.")
    user_states.pop(message.from_user.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_REMOVE_ADMIN" and m.text is not None)
def handle_admin_remove_admin(message):
    uid = message.text.strip()
    if uid in admins_list:
        admins_list.remove(uid)
        save_list_to_file(ADMINS_FILE, admins_list)
        bot.send_message(message.from_user.id, f"âœ… ØªÙ…Øª Ø¥Ø²Ø§Ù„Ø© Ø§Ù„Ù…Ø´Ø±Ù: {uid}")
    else:
        bot.send_message(message.from_user.id, f"âŒ Ø§Ù„Ù…Ø´Ø±Ù {uid} ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ ÙÙŠ Ø§Ù„Ù‚Ø§Ø¦Ù…Ø©.")
    user_states.pop(message.from_user.id, None)

# =============================================================================
# Callbacks - Main Menu / Back
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def cb_back_to_main(call):
    bot.send_message(call.from_user.id, "ðŸ”™ ØªÙ… Ø§Ù„Ø¹ÙˆØ¯Ø© Ù„Ù„Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ©.", reply_markup=main_menu_markup(call.from_user.id))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data in ["wd_back", "cancel_wd"])
def cb_wd_back(call):
    bot.send_message(call.from_user.id, "ðŸ”™ ØªÙ… Ø§Ù„Ø¹ÙˆØ¯Ø© Ù„Ù„Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ©.", reply_markup=main_menu_markup(call.from_user.id))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "create_account")
def cb_create_account(call):
    add_user(call.from_user.id)
    user_states[call.from_user.id] = "WAITING_REG_USERNAME"
    bot.send_message(call.from_user.id, "ðŸ“ ÙŠØ±Ø¬Ù‰ Ø¥Ø±Ø³Ø§Ù„ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… Ø§Ù„Ù…Ø·Ù„ÙˆØ¨:", reply_markup=back_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_method:"))
def cb_wd_method(call):
    method = call.data.split(":")[1]
    state_data[call.from_user.id] = {"method": method}
    user_states[call.from_user.id] = "WAITING_WITHDRAW_AMOUNT"
    bot.edit_message_text("ðŸ’° ÙŠØ±Ø¬Ù‰ ÙƒØªØ§Ø¨Ø© Ø§Ù„Ù…Ø¨Ù„Øº Ø§Ù„Ù…Ø±Ø§Ø¯ Ø³Ø­Ø¨Ù‡:", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "confirm_wd")
def cb_confirm_wd(call):
    chat_id = call.from_user.id
    data = state_data.get(chat_id, {})
    amount = data.get("amount", 0)
    phone = data.get("phone", "")
    method = data.get("method", "")
    method_name = "Ø´Ø§Ù… ÙƒØ§Ø´" if method == "sham" else "Ø³ÙŠØ±ÙŠØ§ØªÙŠÙ„ ÙƒØ§Ø´"
    commission = amount * 0.10
    net = amount - commission
    caption = (
        f"ðŸ“¤ <b>Ø·Ù„Ø¨ Ø³Ø­Ø¨ Ø¬Ø¯ÙŠØ¯</b>\n\n"
        f"ðŸ‘¤ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…: <code>{chat_id}</code>\n"
        f"ðŸ’° Ø§Ù„Ù…Ø¨Ù„Øº: {amount}\n"
        f"ðŸ“‰ Ø§Ù„Ø¹Ù…ÙˆÙ„Ø©: {commission}\n"
        f"ðŸ“¨ Ø§Ù„ØµØ§ÙÙŠ: {net}\n"
        f"ðŸ“± Ø§Ù„Ø±Ù‚Ù…: {phone}\n"
        f"ðŸ’³ Ø§Ù„Ø·Ø±ÙŠÙ‚Ø©: {method_name}"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("âœ… Ù…ÙˆØ§ÙÙ‚Ø©", callback_data="approve_wd"),
        InlineKeyboardButton("âŒ Ø±ÙØ¶", callback_data="reject_wd")
    )
    sent = bot.send_message(ADMIN_GROUP_ID, caption, reply_markup=markup, parse_mode="HTML")
    pending_withdrawals[sent.message_id] = {"user_id": chat_id, "amount": amount}
    bot.send_message(chat_id, "ðŸ“¤ ØªÙ… Ø¥Ø±Ø³Ø§Ù„ Ø·Ù„Ø¨ Ø§Ù„Ø³Ø­Ø¨ Ù„Ù„Ù…Ø±Ø§Ø¬Ø¹Ø©.", reply_markup=main_menu_markup(chat_id))
    bot.answer_callback_query(call.id)
    user_states.pop(chat_id, None)
    state_data.pop(chat_id, None)

# =============================================================================
# Callbacks - Support Reply
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_support:"))
def cb_reply_support(call):
    user_id = int(call.data.split(":")[1])
    admin_id = call.from_user.id
    active_support_replies[admin_id] = user_id
    bot.send_message(
        ADMIN_GROUP_ID,
        f"ðŸ“ Ø§Ù„Ù…Ø´Ø±Ù {admin_id} Ø¯Ø®Ù„ ÙˆØ¶Ø¹ Ø§Ù„Ø±Ø¯ Ø¹Ù„Ù‰ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… {user_id}.\n"
        f"âœï¸ Ø§ÙƒØªØ¨ Ø£ÙŠ Ø±Ø³Ø§Ù„Ø© Ø§Ù„Ø¢Ù† (Ù†ØµØŒ ØµÙˆØ±Ø©ØŒ ÙÙŠØ¯ÙŠÙˆØŒ Ù…Ù„Ù...) ÙˆØ³ÙŠØªÙ… Ø¥Ø±Ø³Ø§Ù„Ù‡Ø§ Ù…Ø¨Ø§Ø´Ø±Ø© Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù….\n"
        f"ðŸ”š Ø§ÙƒØªØ¨ 'ØªÙ…' Ø£Ùˆ 'done' Ø£Ùˆ 'Ø¥Ù†Ù‡Ø§Ø¡' Ù„Ù„Ø®Ø±ÙˆØ¬ Ù…Ù† ÙˆØ¶Ø¹ Ø§Ù„Ø±Ø¯."
    )
    bot.answer_callback_query(call.id)

# =============================================================================
# Callbacks - Admin Panel
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_") or call.data.startswith("edit_"))
def cb_admin_panel(call):
    uid = str(call.from_user.id)
    if uid not in owners_list and uid != str(OWNER_ID):
        bot.answer_callback_query(call.id, "â›”ï¸ Ù„ÙŠØ³ Ù„Ø¯ÙŠÙƒ ØµÙ„Ø§Ø­ÙŠØ©!")
        return

    data = call.data

    if data == "admin_agent_data":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("ØªØ¹Ø¯ÙŠÙ„ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…", callback_data="edit_agent_username"),
            InlineKeyboardButton("ØªØ¹Ø¯ÙŠÙ„ ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±", callback_data="edit_agent_password"),
            InlineKeyboardButton("ðŸ”™ Ø±Ø¬ÙˆØ¹", callback_data="admin_back_to_menu")
        )
        bot.edit_message_text("ðŸ’¼ Ø§Ø®ØªØ± Ù…Ø§ ØªØ±ÙŠØ¯ ØªØ¹Ø¯ÙŠÙ„Ù‡:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif data == "edit_agent_username":
        user_states[call.from_user.id] = "WAITING_ADMIN_AGENT_USERNAME"
        bot.send_message(call.from_user.id, "ðŸ“ Ø£Ø±Ø³Ù„ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… Ø§Ù„Ø¬Ø¯ÙŠØ¯ Ù„Ù„ÙˆÙƒÙŠÙ„:")
        bot.answer_callback_query(call.id)

    elif data == "edit_agent_password":
        user_states[call.from_user.id] = "WAITING_ADMIN_AGENT_PASSWORD"
        bot.send_message(call.from_user.id, "ðŸ”’ Ø£Ø±Ø³Ù„ ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ± Ø§Ù„Ø¬Ø¯ÙŠØ¯Ø© Ù„Ù„ÙˆÙƒÙŠÙ„:")
        bot.answer_callback_query(call.id)

    elif data == "admin_sham_wallet":
        user_states[call.from_user.id] = "WAITING_ADMIN_SHAM_WALLET"
        bot.send_message(call.from_user.id, "ðŸ’° Ø£Ø±Ø³Ù„ Ø¹Ù†ÙˆØ§Ù† Ù…Ø­ÙØ¸Ø© Ø´Ø§Ù… ÙƒØ§Ø´ Ø§Ù„Ø¬Ø¯ÙŠØ¯:")
        bot.answer_callback_query(call.id)

    elif data == "admin_syriatel_code":
        user_states[call.from_user.id] = "WAITING_ADMIN_SYRIATEL_CODE"
        bot.send_message(call.from_user.id, "ðŸ“± Ø£Ø±Ø³Ù„ ÙƒÙˆØ¯ Ø³ÙŠØ±ÙŠØ§ØªÙŠÙ„ ÙƒØ§Ø´ Ø§Ù„Ø¬Ø¯ÙŠØ¯:")
        bot.answer_callback_query(call.id)

    elif data == "admin_balance":
        result = api_request("POST", "global/api/UserApi/getAgentAllWallets", {}, auth=True)
        if result and result.get("status") and result.get("result"):
            balances = result["result"]
            text = "ðŸ“Š Ø£Ø±ØµØ¯Ø© Ø§Ù„Ø®Ø²Ù†Ø© Ø§Ù„Ø­Ø§Ù„ÙŠØ©:\n\n"
            for bal in balances:
                text += f"ðŸ’µ {bal.get('currencyName', 'Unknown')} ({bal.get('currencyCode', 'N/A')}):\n"
                text += f"   Ø§Ù„Ø±ØµÙŠØ¯: {bal.get('balance', 0)}\n"
                text += f"   Ø§Ù„Ù…ØªØ§Ø­: {bal.get('availability', 0)}\n"
                text += f"   Ø§Ù„Ø¨ÙˆÙ†Ø³: {bal.get('bonus', 0)}\n\n"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("âŒ ÙØ´Ù„ ÙÙŠ Ø¬Ù„Ø¨ Ø§Ù„Ø£Ø±ØµØ¯Ø©.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif data == "admin_broadcast":
        user_states[call.from_user.id] = "WAITING_ADMIN_BROADCAST"
        bot.send_message(call.from_user.id, "ðŸ“¢ Ø£Ø±Ø³Ù„ Ø§Ù„Ø±Ø³Ø§Ù„Ø© Ø§Ù„ØªÙŠ ØªØ±ÙŠØ¯ Ø¨Ø«Ù‡Ø§ Ù„Ù„Ø¬Ù…ÙŠØ¹:")
        bot.answer_callback_query(call.id)

    elif data == "admin_add_owner":
        user_states[call.from_user.id] = "WAITING_ADMIN_ADD_OWNER"
        bot.send_message(call.from_user.id, "âž• Ø£Ø±Ø³Ù„ Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… (User ID) Ù„Ù„Ù…Ø§Ù„Ùƒ Ø§Ù„Ø¬Ø¯ÙŠØ¯:")
        bot.answer_callback_query(call.id)

    elif data == "admin_add_admin":
        user_states[call.from_user.id] = "WAITING_ADMIN_ADD_ADMIN"
        bot.send_message(call.from_user.id, "âž• Ø£Ø±Ø³Ù„ Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… (User ID) Ù„Ù„Ù…Ø´Ø±Ù Ø§Ù„Ø¬Ø¯ÙŠØ¯:")
        bot.answer_callback_query(call.id)

    elif data == "admin_remove_owner":
        user_states[call.from_user.id] = "WAITING_ADMIN_REMOVE_OWNER"
        current = "\n".join(owners_list) if owners_list else "(Ù„Ø§ ÙŠÙˆØ¬Ø¯ Ù…Ø§Ù„ÙƒÙŠÙ†)"
        bot.send_message(call.from_user.id, f"âž– Ø£Ø±Ø³Ù„ Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… (User ID) Ù„Ù„Ù…Ø§Ù„Ùƒ Ø§Ù„Ù…Ø±Ø§Ø¯ Ø¥Ø²Ø§Ù„ØªÙ‡.\n\nØ§Ù„Ù…Ø§Ù„ÙƒÙŠÙ† Ø§Ù„Ø­Ø§Ù„ÙŠÙŠÙ†:\n{current}")
        bot.answer_callback_query(call.id)

    elif data == "admin_remove_admin":
        user_states[call.from_user.id] = "WAITING_ADMIN_REMOVE_ADMIN"
        current = "\n".join(admins_list) if admins_list else "(Ù„Ø§ ÙŠÙˆØ¬Ø¯ Ù…Ø´Ø±ÙÙŠÙ†)"
        bot.send_message(call.from_user.id, f"âž– Ø£Ø±Ø³Ù„ Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… (User ID) Ù„Ù„Ù…Ø´Ø±Ù Ø§Ù„Ù…Ø±Ø§Ø¯ Ø¥Ø²Ø§Ù„ØªÙ‡.\n\nØ§Ù„Ù…Ø´Ø±ÙÙŠÙ† Ø§Ù„Ø­Ø§Ù„ÙŠÙŠÙ†:\n{current}")
        bot.answer_callback_query(call.id)

    elif data == "admin_back":
        bot.send_message(call.from_user.id, "ðŸ”™ ØªÙ… Ø¥ØºÙ„Ø§Ù‚ Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ….", reply_markup=main_menu_markup(call.from_user.id))
        bot.answer_callback_query(call.id)

    elif data == "admin_back_to_menu":
        show_admin_panel(call.from_user.id, call.message.message_id)
        bot.answer_callback_query(call.id)

# =============================================================================
# Callbacks - Deposit Action
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data in ["approve_dep", "reject_dep"])
def cb_deposit_action(call):
    msg_id = call.message.message_id
    if msg_id not in pending_deposits:
        bot.answer_callback_query(call.id, "âŒ Ø·Ù„Ø¨ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ Ø£Ùˆ ØªÙ… Ù…Ø¹Ø§Ù„Ø¬ØªÙ‡.")
        return

    dep = pending_deposits.pop(msg_id)
    user_id = dep["user_id"]
    amount = dep["amount"]

    if call.data == "approve_dep":
        player_info = players_db.get(str(user_id))
        if not player_info:
            bot.send_message(call.message.chat.id, f"âŒ Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø±Ø¨Ø· Ø­Ø³Ø§Ø¨ Ø§Ù„Ù„Ø§Ø¹Ø¨ Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù… {user_id}")
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
                bot.send_message(user_id, f"âœ… ØªÙ… Ø§Ø¹ØªÙ…Ø§Ø¯ Ø¥ÙŠØµØ§Ù„Ùƒ ÙˆØ´Ø­Ù† Ø±ØµÙŠØ¯Ùƒ Ø¨Ù…Ø¨Ù„Øº {amount} {currency} Ø¨Ù†Ø¬Ø§Ø­!")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                new_caption = call.message.caption + "\n\nâœ… ØªÙ…Øª Ø§Ù„Ù…Ø¹Ø§Ù„Ø¬Ø©: Ù…Ø¹ØªÙ…Ø¯ ÙˆØ´Ø­Ù†."
                bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"Failed to edit deposit message: {e}")
        else:
            error_msg = "Unknown error"
            if result and result.get("notification"):
                error_msg = result["notification"][0].get("content", "Unknown error")
            bot.send_message(call.message.chat.id, f"âŒ ÙØ´Ù„ ÙÙŠ Ø§Ù„Ø´Ø­Ù†: {error_msg}")
    else:
        try:
            bot.send_message(user_id, "âŒ ØªÙ… Ø±ÙØ¶ Ø¥ÙŠØµØ§Ù„ Ø§Ù„Ø¥ÙŠØ¯Ø§Ø¹. ÙŠØ±Ø¬Ù‰ Ø§Ù„ØªÙˆØ§ØµÙ„ Ù…Ø¹ Ø§Ù„Ø¯Ø¹Ù… Ø§Ù„ÙÙ†ÙŠ.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            new_caption = call.message.caption + "\n\nâŒ ØªÙ…Øª Ø§Ù„Ù…Ø¹Ø§Ù„Ø¬Ø©: Ù…Ø±ÙÙˆØ¶."
            bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"Failed to edit deposit message: {e}")

    bot.answer_callback_query(call.id)

# =============================================================================
# Callbacks - Withdraw Action
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data in ["approve_wd", "reject_wd"])
def cb_withdraw_action(call):
    msg_id = call.message.message_id
    if msg_id not in pending_withdrawals:
        bot.answer_callback_query(call.id, "âŒ Ø·Ù„Ø¨ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ Ø£Ùˆ ØªÙ… Ù…Ø¹Ø§Ù„Ø¬ØªÙ‡.")
        return

    wd = pending_withdrawals.pop(msg_id)
    user_id = wd["user_id"]
    amount = wd["amount"]

    if call.data == "approve_wd":
        player_info = players_db.get(str(user_id))
        if not player_info:
            bot.send_message(call.message.chat.id, f"âŒ Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø±Ø¨Ø· Ø­Ø³Ø§Ø¨ Ø§Ù„Ù„Ø§Ø¹Ø¨ Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù… {user_id}")
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
                bot.send_message(user_id, "âœ… ØªÙ…Øª Ø¹Ù…Ù„ÙŠØ© Ø§Ù„Ø³Ø­Ø¨ Ø¨Ù†Ø¬Ø§Ø­! ØªÙ… Ø®ØµÙ… Ø§Ù„Ù…Ø¨Ù„Øº Ù…Ù† Ø±ØµÙŠØ¯Ùƒ.")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                new_text = call.message.text + "\n\nâœ… ØªÙ…Øª Ø§Ù„Ù…Ø¹Ø§Ù„Ø¬Ø©: ØªÙ… Ø§Ù„ØªØ­ÙˆÙŠÙ„ ÙˆØ§Ù„Ø®ØµÙ…."
                bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"Failed to edit withdraw message: {e}")
        else:
            error_msg = "Unknown error"
            if result and result.get("notification"):
                error_msg = result["notification"][0].get("content", "Unknown error")
            bot.send_message(call.message.chat.id, f"âŒ ÙØ´Ù„ ÙÙŠ Ø§Ù„Ø®ØµÙ…: {error_msg}")
    else:
        try:
            bot.send_message(user_id, "âŒ ØªÙ… Ø±ÙØ¶ Ø·Ù„Ø¨ Ø§Ù„Ø³Ø­Ø¨. ÙŠØ±Ø¬Ù‰ Ø§Ù„ØªÙˆØ§ØµÙ„ Ù…Ø¹ Ø§Ù„Ø¯Ø¹Ù… Ø§Ù„ÙÙ†ÙŠ.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            new_text = call.message.text + "\n\nâŒ ØªÙ…Øª Ø§Ù„Ù…Ø¹Ø§Ù„Ø¬Ø©: Ù…Ø±ÙÙˆØ¶."
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"Failed to edit withdraw message: {e}")

    bot.answer_callback_query(call.id)

# =============================================================================
# Flask Webhook
# =============================================================================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
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
# Main
# =============================================================================
if __name__ == "__main__":
    load_owners()
    load_admins()
    load_users_list()

    if do_signin():
        get_agent_affiliate_id()
    else:
        logger.error("Initial signin failed. API calls may fail until signin succeeds.")

    refresh_thread = threading.Thread(target=token_refresh_loop, daemon=True)
    refresh_thread.start()

    set_webhook()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
