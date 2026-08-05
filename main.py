import os
import json
import time
import string
import random
import threading
import telebot
import tls_client  # 🌟 استخدام السلاح السري المتقدم لتخطي الـ 403 كالبشر تماماً
from flask import Flask, request

# ========================================== #
# 1. إعداد هويات البوت وبوابات الـ API الموثقة #
# ========================================== #
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

PANEL_BASE = "https://texas4win.com"
SIGNIN_API_URL = f"{PANEL_BASE}/global/api/UserApi/signIn"
REFRESH_API_URL = f"{PANEL_BASE}/global/api/UserApi/refreshToken"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

# حساب كاشير عُمير الصارم والموثق بحروفه الصغيرة
AGENT_USER = "bero@yahoo.com"
AGENT_PASS = "Aazzam@318"

access_token = None
refresh_token = None
token_lock = threading.Lock()
user_steps = {}

# ========================================== #
# 2. تهيئة خادم الويب وجسر الـ Webhook الحي  #
# ========================================== #
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

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
    return "🚀 BOT IS LIVE AND RUNNING 24/7 (STABLE TLS API MODE)"

# ========================================== #
# 3. محرك الأتمتة التلقائي وتدشين التوكنات    #
# ========================================== #
def create_tls_session():
    # بناء جلسة متطابقة 100% مع بصمة متصفح كروم البشري لخداع جدار الحماية
    session = tls_client.Session(client_identifier="chrome_120", random_tls_extensions_order=True)
    return session

def agent_sign_in():
    global access_token, refresh_token
    session = create_tls_session()
    payload = {"username": AGENT_USER, "password": AGENT_PASS}
    headers = {
        "Content-Type": "application/json",
        "Origin": PANEL_BASE,
        "Referer": f"{PANEL_BASE}/",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        print("[*] ضرب بوابة تسجيل الدخول الرسمية بمحاكاة بصمة التصفح البشرية...", flush=True)
        res = session.post(SIGNIN_API_URL, json=payload, headers=headers, timeout_seconds=15)
        if res.status_code == 200:
            res_json = res.json()
            res_result = res_json.get("result", {})
            with token_lock:
                if isinstance(res_result, dict):
                    access_token = res_result.get("accessToken")
                    refresh_token = res_result.get("refreshToken")
                else:
                    access_token = res_json.get("accessToken") or res_json.get("token")
            if access_token:
                print("[✅] نجاح خارق! تم انتزاع توكن الأمان وسحق الـ 403 كلياً من السحاب!", flush=True)
                return True
        print(f"[❌] رفض السيرفر الخلفي الدخول، الرمز: {res.status_code}", flush=True)
        return False
    except Exception as e:
        print(f"[❌] عطل اتصال بالبوابة الخلفية: {e}", flush=True)
        return False

def agent_refresh_token():
    global access_token, refresh_token
    if not refresh_token: return agent_sign_in()
    session = create_tls_session()
    headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    try:
        res = session.post(REFRESH_API_URL, json={"refreshToken": refresh_token}, headers=headers, timeout_seconds=15)
        if res.status_code == 200:
            res_json = res.json()
            res_result = res_json.get("result", {})
            with token_lock:
                if isinstance(res_result, dict):
                    access_token = res_result.get("accessToken")
            if access_token: return True
        return agent_sign_in()
    except: return agent_sign_in()

def token_refresher_loop():
    time.sleep(5)
    agent_sign_in()
    while True:
        time.sleep(2700) # التدوير الصامت والمستمر للتوكنات كل 45 دقيقة تلقائياً
        agent_refresh_token()

def api_register_player(username, password):
    global access_token
    if not access_token: agent_sign_in()
    if not access_token: return False, "فشل جلب مفتاح الأمان من اللوحة."
    
    session = create_tls_session()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Origin": PANEL_BASE,
        "Referer": f"{PANEL_BASE}/global/agent/User/index",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    time.sleep(random.uniform(1.5, 3.0))
    email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
    payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}
    
    try:
        print(f"[🚀] قذف حزمة إنشاء اللاعب الجديد: {username} عبر بوابة الـ API", flush=True)
        res = session.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, timeout_seconds=20)
        print(f"[🔬] رد اللوحة الرسمي: الرمز {res.status_code}", flush=True)
        
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("result") == 1 or res_data.get("status") is True: return True, "نجاح"
            if res_data.get("result") == "ex":
                agent_sign_in()
                return False, "انتهت الجلسة مؤقتاً، أعد المحاولة الآن لتلقيم الحساب حياً."
            try: msg = res_data["notification"]["content"]
            except: msg = res_data.get("html", res.text)
            return False, msg
        return False, f"استجابة اللوحة العكسية: {res.status_code}"
    except Exception as e: return False, str(e)

# ========================================== #
# 4. لوحات التحكم بالتليجرام والقوائم الذكية #
# ========================================== #
@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in user_steps: del user_steps[uid]
        
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة الكاشير السحابية الموثقة بالـ API الرسمي! 🎉\n\nتفضل بالاختيار من القائمة أدناه بحسب طلبك وبدون تعقيد التوكنات اليدوية:", reply_markup=markup)

@global_bot.message_handler(func=lambda message: True)
def core_menu(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text
    if text == "👤 حسابي":
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب لاعب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ اضغط على الزر أدناه لتوليد وإنشاء الحساب تلقائياً مع اللوحة الخلفية:", reply_markup=markup)

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
    global_bot.send_message(message.chat.id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة الخلفية سحابياً...")
    threading.Thread(target=run_safe_api_task, args=(message.chat.id, uid, username, password), daemon=True).start()

def run_safe_api_task(chat_id, uid, username, password):
    success, detail = api_register_player(username, password)
    if success:
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n")
        global_bot.send_message(chat_id, f"✅ **تم إنشاء حساب اللاعب بنجاح وتأمينه بالـ API!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
    else:
        global_bot.send_message(chat_id, f"⚠️ تعذر الإنشاء التلقائي:\n`{str(detail)[:150]}`", parse_mode="Markdown")
    if uid in user_steps: del user_steps[uid]

# ========================================== #
# 5. آلية إقلاع وتنشيط الـ Webhook التلقائي #
# ========================================== #
# حقن تفعيل الويب هوك الإجباري لربط ريندر بتليجرام حياً فور البناء وسحق التعليق
try:
    global_bot.remove_webhook()
    time.sleep(1)
    render_url_link = "https://onrender.com"
    global_bot.set_webhook(url=f"{render_url_link}/{BOT_TOKEN}")
    print("[+] تم ربط وتفعيل الـ Webhook بنجاح مذهل حياً مع تليجرام!", flush=True)
except Exception as webhook_error:
    print(f"[-] تنبيه في تفعيل الويب هوك: {webhook_error}", flush=True)

if __name__ == "__main__":
    # تشغيل محرك التجديد الآلي للتوكنات في قناة مستقلة
    threading.Thread(target=token_refresher_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
