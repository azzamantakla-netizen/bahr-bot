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

# Improved TLS Client for Cloudflare Bypass
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
access_token = None
refresh_token = None
agent_affiliate_id = None

user_states = {}
state_data = {}
pending_deposits = {}
pending_withdrawals = {}

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# =============================================================================
# Session & API Helpers (Optimized for Debugging)
# =============================================================================
def create_session():
    global session
    if tls_client:
        try:
            session = tls_client.Session(
                client_identifier="chrome_120",
                random_tls_extension_order=True
            )
            logger.info("TLS Session created successfully.")
        except Exception as e:
            logger.error(f"Failed to create TLS session: {e}")
            session = None
    return session

def api_request(method, endpoint, payload=None, auth=False, retries=2):
    url = f"{PANEL_BASE}/{endpoint}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://agents.texas4win.com",
        "Referer": "https://agents.texas4win.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    logger.info(f"DEBUG: Requesting {method} {url} (Auth: {auth})")
    
    for attempt in range(retries + 1):
        try:
            if not session:
                create_session()
            
            if method.upper() == "GET":
                resp = session.get(url, headers=headers, timeout_seconds=30)
            else:
                resp = session.post(url, headers=headers, json=payload, timeout_seconds=30)
            
            logger.info(f"DEBUG: Response Status: {resp.status_code}")
            
            if resp.status_code in (401, 403) and auth:
                logger.warning("DEBUG: Auth expired, re-signing in...")
                if do_signin():
                    headers["Authorization"] = f"Bearer {access_token}"
                    continue
            
            try:
                data = resp.json()
                logger.info(f"DEBUG: Response JSON: {json.dumps(data)[:500]}")
                return data
            except:
                logger.error(f"DEBUG: Failed to parse JSON. Raw Response: {resp.text[:1000]}")
                return {"status": False, "raw": resp.text}
        except Exception as e:
            logger.error(f"DEBUG: Request attempt {attempt} failed: {e}")
            if attempt == retries: return {"status": False, "error": str(e)}
            time.sleep(2)
    return {"status": False, "error": "Max retries reached"}

def do_signin():
    global access_token, refresh_token
    payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
    logger.info(f"DEBUG: Attempting sign-in for {AGENT_USERNAME}")
    result = api_request("POST", "global/api/UserApi/signIn", payload)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        access_token = result["result"].get("accessToken")
        refresh_token = result["result"].get("refreshToken")
        logger.info("DEBUG: Sign-in SUCCESS.")
        return True
    logger.error(f"DEBUG: Sign-in FAILED: {result}")
    return False

def get_agent_affiliate_id():
    global agent_affiliate_id
    HARDCODED_ID = "2688288"
    if not access_token: do_signin()
    agent_affiliate_id = HARDCODED_ID
    return agent_affiliate_id

# =============================================================================
# Bot Handlers (Registration)
# =============================================================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(message.from_user.id)
    bot.send_message(message.chat.id, "مرحباً بك في بوت texas4win! اختر من القائمة:", 
                     reply_markup=main_menu_markup(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def menu_account(message):
    user_id = message.from_user.id
    player = players_db.get(str(user_id))
    if player:
        text = f"👤 **معلومات حسابك:**\n🆔 ID: `{player['player_id']}`\n👤 الاسم: `{player['username']}`"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 إنشاء حساب جديد", callback_data="reg_start"))
        bot.send_message(message.chat.id, "ليس لديك حساب مرتبط بعد.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "reg_start")
def reg_start(call):
    user_states[call.from_user.id] = "WAITING_REG_USERNAME"
    bot.send_message(call.message.chat.id, "👤 أرسل اسم المستخدم المطلوب (بالإنجليزي):", reply_markup=back_markup())
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REG_USERNAME")
def handle_reg_username(message):
    if message.text == "🔙 رجوع":
        user_states.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "تم الرجوع.", reply_markup=main_menu_markup(message.from_user.id))
        return
    state_data[message.from_user.id] = {"username": message.text.strip()}
    user_states[message.from_user.id] = "WAITING_REG_PASSWORD"
    bot.send_message(message.chat.id, "🔒 أرسل كلمة المرور المطلوبة:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REG_PASSWORD")
def handle_reg_password(message):
    user_id = message.from_user.id
    if message.text == "🔙 رجوع":
        user_states[user_id] = "WAITING_REG_USERNAME"
        bot.send_message(message.chat.id, "أرسل اسم المستخدم:")
        return
    
    password = message.text.strip()
    username = state_data[user_id]["username"]
    bot.send_message(message.chat.id, "⏳ جاري إنشاء الحساب...")
    
    email = f"{username}_{random.randint(1000,9999)}@player.bot"
    payload = {
        "player": {
            "login": username,
            "email": email,
            "password": password,
            "parentId": int(agent_affiliate_id or "2688288"),
            "firstName": username,
            "lastName": "Player"
        }
    }
    
    logger.info(f"DEBUG: Attempting to register player: {username}")
    result = api_request("POST", "global/api/UserApi/registerPlayer", payload, auth=True)
    
    if result and result.get("status"):
        player_id = str(result.get("result", {}).get("playerId") or result.get("result") or "")
        players_db[str(user_id)] = {"player_id": player_id, "username": username}
        save_players_db(players_db)
        bot.send_message(message.chat.id, f"✅ تم إنشاء الحساب بنجاح!\n🆔 ID: {player_id}", reply_markup=main_menu_markup(user_id))
    else:
        # Improved error extraction
        error = "خطأ غير معروف"
        if result:
            notif = result.get("notification")
            if isinstance(notif, list) and len(notif) > 0:
                error = notif[0].get("content", "خطأ غير معروف")
            elif isinstance(notif, dict):
                error = notif.get("content", "خطأ غير معروف")
            elif result.get("error"):
                error = result.get("error")
        
        bot.send_message(message.chat.id, f"❌ فشل الإنشاء: {error}", reply_markup=main_menu_markup(user_id))
    
    user_states.pop(user_id, None)

# Helper functions for file management
def load_list_from_file(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_list_to_file(filepath, data_list):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data_list: f.write(str(item) + "\n")

def load_owners():
    global owners_list
    owners_list = load_list_from_file(OWNERS_FILE)
    if str(OWNER_ID) not in owners_list:
        owners_list.append(str(OWNER_ID))
        save_list_to_file(OWNERS_FILE, owners_list)

def load_admins():
    global admins_list
    admins_list = load_list_from_file(ADMINS_FILE)

def load_users_list():
    global users_list
    users_list = load_list_from_file(USERS_FILE)

def add_user(user_id):
    uid = str(user_id)
    if uid not in users_list:
        users_list.append(uid)
        with open(USERS_FILE, "a", encoding="utf-8") as f: f.write(uid + "\n")

def load_players_db():
    if os.path.exists(PLAYERS_DB_FILE):
        with open(PLAYERS_DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_players_db(data):
    with open(PLAYERS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

players_db = load_players_db()

def main_menu_markup(user_id):
    is_owner = str(user_id) in owners_list
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("👤 حسابي"), KeyboardButton("📥 إيداع / شحن رصيد"),
               KeyboardButton("📩 سحب رصيد"), KeyboardButton("📞 الدعم الفني"))
    if is_owner: markup.add(KeyboardButton("⚙️ لوحة التحكم"))
    return markup

def back_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔙 رجوع"))
    return markup

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200
    abort(403)

@app.route("/")
def index(): return "Bot is running!", 200

if __name__ == "__main__":
    load_owners(); load_admins(); load_users_list()
    create_session()
    do_signin()
    get_agent_affiliate_id()
    
    # Set webhook for Render
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
    
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
