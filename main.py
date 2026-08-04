import os
import json
import time
import string
import random
import threading
import telebot
from flask import Flask, request

# 💡 تخطي حظر الـ 403 وأتمتة الكوكيز الآلية للأبد
import tls_client  

BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

# النطاقات والمسارات الرسمية للوحة
PANEL_BASE = "https://texas4win.com"
LOGIN_PAGE_URL = f"{PANEL_BASE}/global/agent/login/index"
LOGIN_API_URL = f"{PANEL_BASE}/global/api/UserApi/login"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

RENDER_URL = "https://onrender.com"

# حساب الوكيل الخاص بك مدمج وموثق للأتمتة الذاتية
AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"

# متغير الذاكرة المؤقتة للكوكيز
user_cookies = ""
user_steps = {}

global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- دالة أتمتة تسجيل الدخول الذكي وجلب الكوكيز عبر الزيارة التمهيدية لمنع الـ 403 ---
def refresh_agent_session():
    global user_cookies
    print("[🔄] جاري تجديد جلسة الوكيل وتوليد كوكيز جديدة تلقائياً...", flush=True)
    try:
        session = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True
        )
        # خطوة 1: محاكاة زيارة صفحة الدخول أولاً كمتصفح حقيقي لجلب رموز الأمان المبدئية
        init_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
        }
        session.get(LOGIN_PAGE_URL, headers=init_headers, timeout_seconds=15)
        time.sleep(random.uniform(1.0, 2.0))

        # خطوة 2: بناء الهيدرز الصارم والمطابق لإرسال حزمة الدخول العكسي
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": PANEL_BASE,
            "Referer": LOGIN_PAGE_URL,
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        }
        payload = {"login": AGENT_USERNAME, "password": AGENT_PASSWORD, "languageCode": "ar"}
        res = session.post(LOGIN_API_URL, json=payload, headers=headers, timeout_seconds=15)
        print(f"[🔬] رد اللوحة المباشر على تسجيل الدخول: الرمز {res.status_code}", flush=True)
        
        if res.status_code == 200:
            cookies_list = []
            for key, val in res.cookies.items():
                cookies_list.append(f"{key}={val}")
            if "languageCode" not in res.cookies:
                cookies_list.append("languageCode=ar")
                cookies_list.append("language=ar")
            user_cookies = "; ".join(cookies_list)
            print(f"[✅] تم استخراج وتحديث كوكيز الجلسة بنجاح: {user_cookies[:35]}...", flush=True)
            return True
        else:
            print(f"[❌] فشل تسجيل الدخول العكسي، الرمز: {res.status_code} - نص الرد: {res.text[:100]}", flush=True)
            return False
    except Exception as e:
        print(f"[❌] خطأ أثناء تجديد الجلسة: {e}", flush=True)
        return False

# --- مسار استقبال الرسائل الآمن عبر توكن البوت ---
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
    return "🚀 BOT IS LIVE AND RUNNING 24/7 (AUTO-COOKIE MODE)"

# --- دالة الاتصال باللوحة عبر محاكي المتصفح الكاسر للـ 403 ---
def api_register_player(username, password, retry=True):
    global user_cookies
    if not user_cookies:
        refresh_agent_session()
    try:
        session = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True
        )
        cookie_dict = {}
        if user_cookies:
            for item in user_cookies.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookie_dict[k.strip()] = v.strip()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": PANEL_BASE,
            "Referer": f"{PANEL_BASE}/global/agent/User/index",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        }

        time.sleep(random.uniform(0.5, 1.2))
        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}

        print(f"[🚀] قذف حزمة الإنشاء للاعب الجديد: {username}", flush=True)
        res = session.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, cookies=cookie_dict, timeout_seconds=15)
        print(f"[🔬] استجابة اللوحة العكسية: الرمز {res.status_code}", flush=True)
        
        if res.status_code == 403 and retry:
            print("[⚠️] تم كشف انتهاء الجلسة (403)، جاري تجديدها آلياً وإعادة المحاولة...", flush=True)
            if refresh_agent_session():
                return api_register_player(username, password, retry=False)
        
        if res.status_code == 200:
            try:
                res_data = res.json()
                if res_data.get("result") == 1 or res_data.get("status") is True:
                    return True, "نجاح"
                return False, res_data.get("notification", {}).get("content", "فشل")
            except:
                return False, "فشل فك حزمة الـ JSON العكسية."
        return False, f"رمز خطأ الاستجابة {res.status_code} - تفاصيل: {res.text[:50]}"
    except Exception as e:
        return False, str(e)

# ========================================== #
# 3. محرك تليجرام وقوائم التحكم والحالات #
# ========================================== #
@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in user_steps:
        del user_steps[uid]
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    if uid == OWNER_ID:
        markup.add(telebot.types.KeyboardButton("⚙️ تجديد الجلسة آلياً (للمالك)"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة الكاشير السحابية ذاتية التحديث بالملي! 🎉", reply_markup=markup)

@global_bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "start_reg":
        user_steps[call.from_user.id] = {"state": "WAITING_USERNAME"}
        global_bot.send_message(call.message.chat.id, "👤 يرجى إرسال اسم المستخدم المطلوب للحساب الجديد:")

@global_bot.message_handler(func=lambda message: True)
def core_menu_and_states(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text.strip()
    
    if uid in user_steps:
        current_state = user_steps[uid].get("state")
        if current_state == "WAITING_USERNAME":
            user_steps[uid]["username"] = text
            user_steps[uid]["state"] = "WAITING_PASSWORD"
            global_bot.send_message(chat_id, "🔑 يرجى إرسال كلمة المرور للحساب الجديد:")
            return
        elif current_state == "WAITING_PASSWORD":
            username = user_steps[uid].get("username")
            password = text
            del user_steps[uid]
            global_bot.send_message(chat_id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة عبر الجلسة الذكية آلياً...")
            threading.Thread(target=run_safe_api_task, args=(chat_id, uid, username, password), daemon=True).start()
            return

    if (text == "⚙️ تجديد الجلسة آلياً (للمالك)" or "تجديد الجلسة" in text) and uid == OWNER_ID:
        global_bot.send_message(chat_id, "🔄 جاري فحص بيانات الوكيل والاتصال باللوحة لتوليد جلسة طازجة...")
        if refresh_agent_session():
            global_bot.send_message(chat_id, f"✅ **تم تحديث الجلسة وسحب الكوكيز بنجاح قطعي!**\n\n`{user_cookies[:40]}...`")
        else:
            global_bot.send_message(chat_id, "❌ **فشل التحديث الآلي!** تأكد من صحة البيانات داخل كود السكربت.")
        return
        
    if text == "👤 حسابي":
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ اضغط على الزر لإنشاء حساب لاعب فوراً.", reply_markup=markup)
        return
    if text == "📥 إيداع / شحن رصيد":
        global_bot.send_message(chat_id, "📥 خيارات الشحن التلقائي قيد التفعيل بالـ API.")
        return
    if text == "📩 سحب رصيد":
        global_bot.send_message(chat_id, "📩 خيارات السحب قيد التفعيل بالـ API.")
        return
    if text == "📞 الدعم الفني":
        global_bot.send_message(chat_id, "📞 فريق الدعم متواجد لخدمتكم دائماً.")
        return

def run_safe_api_task(chat_id, uid, username, password):
    success, detail = api_register_player(username, password)
    if success:
        # 🌟 إصلاح قطعي ومقاوم للمسافات البادئة: الكتابة المباشرة المكونة من سطرين مستقلين تماماً لمنع تعليق معالج ريندر
        log_line = json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n"
