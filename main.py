import os
import json
import time
import string
import random
import threading
import requests
import telebot
from flask import Flask

# ========================================== #
# 1. إعداد خادم الويب لمنصة Render (الإقلاع)  #
# ========================================== #
app = Flask(__name__)

@app.route('/')
def home():
    # كسر صمت ريندر فوراً وإرسال الرمز 200 لتخطي الدائرة التي تدور حياً
    return "🚀 BOT IS LIVE AND RUNNING 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ========================================== #
# 2. إعداد مفاتيح وبوابات الـ API الموثقة    #
# ========================================== #
BOT_TOKEN = "8624354425:AAEsyz52w-VgqDhEeLiitYFrCae81A3DFzs"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

PANEL_BASE = "https://texas4win.com"
SIGNIN_API_URL = f"{PANEL_BASE}/global/api/UserApi/signIn"
REFRESH_API_URL = f"{PANEL_BASE}/global/api/UserApi/refreshToken"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

AGENT_USER = "Bero@yahoo.com"
AGENT_PASS = "Aazzam@318"

access_token = None
refresh_token = None
token_lock = threading.Lock()
user_steps = {}

def agent_sign_in():
    global access_token, refresh_token
    payload = {"username": AGENT_USER, "password": AGENT_PASS}
    try:
        print("[*] ضرب بوابة تسجيل الدخول الرسمية عبر سيرفر ريندر الموثق...", flush=True)
        res = requests.post(SIGNIN_API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if res.status_code == 200 and res.json().get("status") is True:
            with token_lock:
                access_token = res.json()["result"].get("accessToken")
                refresh_token = res.json()["result"].get("refreshToken")
            print("[✅] تم انتزاع التوكن بنجاح وسحق جدار الحماية الخارجي!", flush=True)
            return True
        print(f"[❌] رفض السيرفر الخلفي للوحة الدخول، الرمز: {res.status_code}", flush=True)
        return False
    except Exception as e:
        print(f"[❌] عطل اتصال بين ريندر واللوحة: {e}", flush=True)
        return False

def agent_refresh_token():
    global access_token, refresh_token
    if not refresh_token: return agent_sign_in()
    try:
        res = requests.post(REFRESH_API_URL, json={"refreshToken": refresh_token}, headers={"Content-Type": "application/json"}, timeout=15)
        if res.status_code == 200 and res.json().get("status") is True:
            with token_lock:
                access_token = res.json()["result"].get("accessToken")
                refresh_token = res.json()["result"].get("refreshToken")
            return True
        return agent_sign_in()
    except: return agent_sign_in()

def token_refresher_loop():
    time.sleep(10)
    agent_sign_in()
    while True:
        time.sleep(2700)
        agent_refresh_token()

def api_register_player(username, password):
    global access_token
    if not access_token: agent_sign_in()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    time.sleep(random.uniform(1.5, 3.5))
    email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
    try:
        res = requests.post(REGISTER_PLAYER_API_URL, json={"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}, headers=headers, timeout=20)
        if res.status_code == 200:
            if res.json().get("result") == 1 or res.json().get("status") is True: return True, "نجاح"
            try: msg = res.json()["notification"]["content"]
            except: msg = res.json().get("html", res.text)
            return False, msg
        return False, f"استجابة اللوحة: {res.status_code}"
    except Exception as e: return False, str(e)

# ========================================== #
# 3. إعداد محرك تليجرام المستقل بالخلفية     #
# ========================================== #
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
global_bot.delete_webhook(drop_pending_updates=True)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في عائلتنا الموثقة عبر السحاب بالـ API الرسمي! 🎉\n\nتفضل بالاختيار من القائمة أدناه بحسب طلبك:", reply_markup=markup)

def check_my_account(chat_id, uid):
    if not os.path.exists(DB_FILE):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ لا يوجد حساب مرتبط بك. اضغط للإنشاء فوراً.", reply_markup=markup)
        return
    p_found = None
    with open(DB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and json.loads(line.strip()).get("tg_id") == uid:
                p_found = json.loads(line.strip()); break
    if p_found:
        global_bot.send_message(chat_id, f"ℹ️ **معلومات حسابك:**\n\n👤 يوزر: `{p_found['login']}`\n🔑 باسورد: `{p_found['password']}`", parse_mode="Markdown")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ لا يوجد حساب مرتبط بك. اضغط للإنشاء فوراً.", reply_markup=markup)

@global_bot.message_handler(func=lambda message: True)
def core_menu(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text
    if text == "👤 حسابي": check_my_account(chat_id, uid); return
    if text == "📥 إيداع / شحن رصيد": global_bot.send_message(chat_id, "📥 خيارات الشحن التلقائي قيد التفعيل بالـ API."); return
    if text == "📩 سحب رصيد": global_bot.send_message(chat_id, "📩 خيارات السحب التلقائي قيد التفعيل بالـ API."); return
    if text == "📞 الدعم الفني": global_bot.send_message(chat_id, "📞 فريق الدعم متواجد لخدمتكم دائماً."); return

@global_bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.data == "start_reg":
        global_bot.send_message(chat_id, "👤 يرجى إرسال اسم المستخدم المطلوب للحساب الجديد:")
        global_bot.register_next_step_handler(call.message, reg_step_username)

def reg_step_username(message):
    user_steps[message.from_user.id] = {"username": message.text.strip()}
    global_bot.send_message(message.chat.id, "🔑 يرجى إرسال كلمة المرور للحساب الجديد:")
    global_bot.register_next_step_handler(message, reg_step_password)

def reg_step_password(message):
    uid = message.from_user.id
    if uid not in user_steps: return
    password = message.text.strip()
    username = user_steps[uid]["username"]
    global_bot.send_message(message.chat.id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة عبر بوابة المطورين...")
    threading.Thread(target=run_safe_api_task, args=(message.chat.id, uid, username, password), daemon=True).start()

def run_safe_api_task(chat_id, uid, username, password):
    success, detail = api_register_player(username, password)
    if success:
        with open(DB_FILE, "a", encoding="utf-8") as f: f.write(json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n")
        global_bot.send_message(chat_id, f"✅ **تم إنشاء حسابك بنجاح وبصلاحية المطورين!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
    else:
        global_bot.send_message(chat_id, f"⚠️ تعذر الإنشاء التلقائي:\n`{str(detail)[:150]}`", parse_mode="Markdown")
    if uid in user_steps: del user_steps[uid]

def run_bot_polling():
    # تشغيل محرك تليجرام في قناة خلفية مستقلة تماماً لمنع قفل السيرفر
    print("[+] إطلاق قناة الاستماع الحية للبوت بالخلفية...", flush=True)
    global_bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    print("[+] إطلاق نظام الأتمتة السحابي والـ Web Service على سيرفر Render...", flush=True)
    # 1. إقلاع محرك التجديد الصامت للتوكنات
    threading.Thread(target=token_refresher_loop, daemon=True).start()
    # 2. إقلاع محرك تليجرام في خيط مستقل بالخلفية لعدم خنق المعالج
    threading.Thread(target=run_bot_polling, daemon=True).start()
    # 3. تشغيل الـ Flask بالخيط الرئيسي ليرد فوراً على سيرفر ريندر بالرمز 200 وسحق الدائرة
    run_flask()
