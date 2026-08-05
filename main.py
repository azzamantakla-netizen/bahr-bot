import os
import json
import time
import string
import random
import threading
import telebot
from flask import Flask, request
import tls_client

# ==================== الإعدادات الأساسية والبيانات السرية الديناميكية ====================
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
ADMIN_GROUP_ID = -1003983996094

AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"

PANEL_BASE = "https://texas4win.com"
RENDER_URL = "https://onrender.com"

DB_FILE = "players_db.txt"
OWNERS_FILE = "owners.txt"
ADMINS_FILE = "admins.txt"
USERS_FILE = "users.txt"

SHAM_CASH_WALLET = "a18758d5324eb7595d4463ca355ad221"
SYRIATEL_CASH_CODE = "481 22120"

access_token = None
refresh_token = None
user_steps = {}
pending_deposits = {}
pending_withdraws = {}

owners_list = [OWNER_ID]
admins_list = []

def save_list(filename, data_list):
    try:
        with open(filename, "w") as f:
            for item in data_list:
                f.write(f"{item}\n")
    except:
        pass

def load_lists():
    global owners_list, admins_list
    try:
        if os.path.exists(OWNERS_FILE):
            with open(OWNERS_FILE, "r") as f:
                owners_list = [int(line.strip()) for line in f if line.strip().isdigit()]
        if OWNER_ID not in owners_list:
            owners_list.append(OWNER_ID)
            
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, "r") as f:
                admins_list = [int(line.strip()) for line in f if line.strip().isdigit()]
    except:
        pass

def log_user(user_id):
    try:
        users = set()
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                users = set(line.strip() for line in f if line.strip())
        if str(user_id) not in users:
            with open(USERS_FILE, "a") as f:
                f.write(f"{user_id}\n")
    except:
        pass

load_lists()
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# ==================== أتمتة الـ API وصيانة التوكينات والجلسات ====================
def api_sign_in():
    global access_token, refresh_token
    try:
        session = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        url = f"{PANEL_BASE}/global/api/UserApi/signIn"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
        res = session.post(url, json=payload, headers=headers, timeout_seconds=6)
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("status") is True and "result" in res_data:
                access_token = res_data["result"].get("accessToken")
                refresh_token = res_data["result"].get("refreshToken")
                print("[🔑] تم تجديد وعقد جلسة التوكن بنجاح!", flush=True)
                return True
    except:
        pass
    return False

def api_refresh_token_loop():
    global access_token, refresh_token
    while True:
        time.sleep(2700)
        if refresh_token:
            try:
                session = tls_client.Session(client_identifier="chrome_120")
                url = f"{PANEL_BASE}/global/api/UserApi/refreshToken"
                payload = {"refreshToken": refresh_token}
                res = session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout_seconds=6)
                if res.status_code == 200:
                    res_data = res.json()
                    if res_data.get("status") is True and "result" in res_data:
                        access_token = res_data["result"].get("accessToken")
                        refresh_token = res_data["result"].get("refreshToken")
                        print("[🔄] تم صيانة الجلسة التلقائية بنجاح!", flush=True)
                        continue
            except:
                pass
        api_sign_in()

threading.Thread(target=api_refresh_token_loop, daemon=True).start()

def api_register_player(username, password):
    global access_token
    if not access_token and not api_sign_in():
        return False, "السيرفر غير موثق حالياً."
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}
        res = session.post(url, json=payload, headers=headers, timeout_seconds=5)
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("status") is True or res_data.get("result") == 1:
                return True, "نجاح"
            return False, res_data.get("notification", {}).get("content", "الاسم مستخدم مسبقاً.")
    except Exception as e:
        return False, str(e)
    return False, "خطأ غير معروف"

def api_deposit_to_player(player_id, amount):
    global access_token
    if not access_token and not api_sign_in():
        return False
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"{PANEL_BASE}/global/api/UserApi/depositToPlayer"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {"amount": float(amount), "comment": "ضخ تلقائي", "affiliateId": int(player_id), "moneyStatus": 3, "currencyCode": "AMD"}
        res = session.post(url, json=payload, headers=headers, timeout_seconds=5)
        return res.status_code == 200 and res.json().get("status") is True
    except:
        return False

def api_withdraw_from_player(player_id, amount):
    global access_token
    if not access_token and not api_sign_in():
        return False
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"{PANEL_BASE}/global/api/UserApi/withdrawFromPlayer"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {"amount": float(amount), "comment": "خصم سحب تلقائي", "affiliateId": int(player_id), "moneyStatus": 3, "currencyCode": "AMD"}
        res = session.post(url, json=payload, headers=headers, timeout_seconds=5)
        return res.status_code == 200 and res.json().get("status") is True
    except:
        return False

# ==================== إدارة الـ Webhook والسيرفر على Render ====================
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        global_bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

@app.route('/')
def home():
    return "🚀 ACTIVE AUTOMATION GATEWAY LIVE"

# ==================== معالجة أمر البداية والعودة للقائمة الرئيسية ====================
def send_main_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    welcome = (
        "مرحباً بك في البوت الاحترافي ! 🎉\n"
        "⚡️ نظام معالجة المعاملات التلقائي مستقر ويعمل بأعلى كفاءة.\n"
        "📑 يمكنك الآن إدارة حسابك، شحن رصيدك، أو طلب السحب فوراً بضغطة زر.\n"
        "🔘 يرجى اختيار العملية المطلوبة من القائمة أدناه:"
    )
    global_bot.send_message(chat_id, welcome, reply_markup=markup)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    log_user(message.from_user.id)
    if message.from_user.id in user_steps:
        del user_steps[message.from_user.id]
    send_main_menu(message.chat.id)

# ==================== 1. معالج خطوات تجميع البيانات والممتدة (States Handler) ====================
@global_bot.message_handler(func=lambda message: message.from_user.id in user_steps)
def active_steps_handler(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text.strip()
    state = user_steps[uid].get("state")
    
    if text == "🔙 رجوع" or text == "🔙 إلغاء والعودة":
        del user_steps[uid]
        send_main_menu(chat_id)
        return

    # تدفق إنشاء حساب لاعب جديد
    if state == "WAITING_USERNAME":
        user_steps[uid]["username"] = text
        user_steps[uid]["state"] = "WAITING_PASSWORD"
        global_bot.send_message(chat_id, "🔑 يرجى إرسال كلمة المرور المطلوبة للحساب الجديد:")
        return

    elif state == "WAITING_PASSWORD":
        username = user_steps[uid]["username"]
        password = text
        del user_steps[uid]
        global_bot.send_message(chat_id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة عبر الـ API الرسمي...")
        success, detail = api_register_player(username, password)
        if success:
            try:
                with open(DB_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"login": username, "password": password}) + "\n")
            except:
                pass
            global_bot.send_message(chat_id, f"✅ **تم إنشاء الحساب بنجاح سحابي كاسح ومطابق 100%!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
        else:
            global_bot.send_message(chat_id, f"⚠️ **فشل إنشاء الحساب**: {detail}")
        return

    # تدفق الإيداع المبسط (كتابة المبلغ مباشرة)
    elif state == "WAITING_DEP_AMOUNT":
        user_steps[uid]["amount"] = text
        user_steps[uid]["state"] = "WAITING_DEP_RECEIPT"
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("🔙 إلغاء والعودة"))
