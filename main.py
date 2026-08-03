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
# 1. إعداد خادم الويب والمنافذ لمنصة Render  #
# ========================================== #
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 BOT IS LIVE AND RUNNING 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ========================================== #
# 2. إعداد مفاتيح وبوابات الـ API الموثقة    #
# ========================================== #
# 🌟 حقن التوكن الجديد الصافي والمطهر كلياً لعام 2026
BOT_TOKEN = "8624354425:AAEsyz52w-VgqDhEeLiitYFrCae81A3DFzs"
OWNER_ID = 6693251012
CONFIG_FILE = "config.json"
DB_FILE = "players_db.txt"

PANEL_BASE = "https://texas4win.com"
SIGNIN_API_URL = f"{PANEL_BASE}/global/api/UserApi/signIn"
REFRESH_API_URL = f"{PANEL_BASE}/global/api/UserApi/refreshToken"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

access_token = None
refresh_token = None
token_lock = threading.Lock()
user_steps = {}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {"agent_user": "Bero@yahoo.com", "agent_pass": "Aazzam@318", "welcome_msg": "👋 مرحباً بك في عائلتنا!\n\n⚙️ صُمم هذا البوت باحترافية عالية ليمنحك تجربة فريدة من نوعها، حيث يضمن لك:\n⚡️ سرعة قصوى في عمليات الإيداع.\n🔄 مرونة وأمان فائق في السحب.\n\n🎛 تفضل بالاختيار من القائمة أدناه بحسب الزر الذي يلبي طلبك:", "is_active": True}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(cfg, f, ensure_ascii=False, indent=4)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)

def agent_sign_in():
    global access_token, refresh_token
    cfg = load_config()
    try:
        print("[*] ضرب بوابة تسجيل الدخول الرسمية عبر سيرفر ريندر الموثق...", flush=True)
        res = requests.post(SIGNIN_API_URL, json={"username": cfg["agent_user"], "password": cfg["agent_pass"]}, headers={"Content-Type": "application/json"}, timeout=15)
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
    time.sleep(5)
    agent_sign_in()
    while True:
        time.sleep(2700)
        agent_refresh_token()

def api_register_player(username, password):
    global access_token
    if not access_token: agent_sign_in()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
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
# 3. إعداد محرك تليجرام والقوائم الذكية       #
# ========================================== #
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
global_bot.delete_webhook(drop_pending_updates=True)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    if message.from_user.id == OWNER_ID: markup.add(telebot.types.KeyboardButton("⚙️ قائمة التحكم (للمالك)"))
    global_bot.send_message(message.chat.id, load_config()["welcome_msg"], reply_markup=markup)

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
    if text == "⚙️ قائمة التحكم (للمالك)" and uid == OWNER_ID:
        cfg = load_config()
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(telebot.types.InlineKeyboardButton("🔄 تجديد التوكن فوراً حياً", callback_data="adm_force_token"))
        global_bot.send_message(chat_id, f"⚙️ **لوحة المالك الحية:**\n\n👤 كاشير: `{cfg['agent_user']}`\n🔑 باسورد: `{cfg['agent_pass']}`", parse_mode="Markdown", reply_markup=markup)
        return
    if text == "👤 حسابي": check_my_account(chat_id, uid); return
    if text == "📥 إيداع / شحن رصيد": global_bot.send_message(chat_id, "📥 خيارات الشحن التلقائي قيد التفعيل بالـ API."); return
    if text == "📩 سحب رصيد": global_bot.send_message(chat_id, "📩 خيارات السحب قيد التفعيل بالـ API."); return
    if text == "📞 الدعم الفني": global_bot.send_message(chat_id, "📞 فريق الدعم متواجد لخدمتكم دائماً."); return

@global_bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.data == "adm_force_token":
        global_bot.answer_callback_query(call.id, "🔄 جاري التجديد حياً...")
        global_bot.send_message(chat_id, "✅ تم تحديث وتوليد توكنات أمان جديدة بنجاح!" if agent_refresh_token() else "❌ فشل التجديد الفوري.")
        return
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

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("[+] إطلاق نظام الأتمتة السحابي والـ Web Service على سيرفر Render...", flush=True)
    threading.Thread(target=token_refresher_loop, daemon=True).start()
    global_bot.infinity_polling(skip_pending=True)
