import os
import json
import time
import string
import random
import threading
import telebot
from flask import Flask, request
import tls_client

BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

PANEL_BASE = "https://texas4win.com"
LOGIN_PAGE_URL = f"{PANEL_BASE}/global/agent/login/index"
LOGIN_API_URL = f"{PANEL_BASE}/global/api/UserApi/login"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"
RENDER_URL = "https://onrender.com"

# 🌟 الاعتماد الكلي على بيانات الكاشير القديم المستقر الخاص بك لجلب الكوكيز آلياً
AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"

user_cookies = "language=ar; languageCode=ar"
user_steps = {}

global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- دالة عبور جدار الحماية وتسجيل الدخول التلقائي بالخلفية لإنتاج كوكيز حية طازجة للأبد ---
def refresh_agent_cookies_dynamically():
    global user_cookies
    print("[🔄] محرك الأتمتة الميكانيكي: جاري محاكاة الدخول البشري وتوليد جلسة جديدة آلياً...", flush=True)
    try:
        session = tls_client.Session(client_identifier="chrome_120", random_tls_extensions_order=True)
        init_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
        }
        # خطوة 1: فحص أمان جدار الموقع وسحب الكوكيز المبدئية
        session.get(LOGIN_PAGE_URL, headers=init_headers, timeout_seconds=10)
        time.sleep(random.uniform(1.0, 2.0))

        # خطوة 2: قذف بيانات الدخول الموثقة
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": PANEL_BASE,
            "Referer": LOGIN_PAGE_URL,
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        }
        payload = {"login": AGENT_USERNAME, "password": AGENT_PASSWORD, "languageCode": "ar"}
        res = session.post(LOGIN_API_URL, json=payload, headers=headers, timeout_seconds=10)
        
        if res.status_code == 200:
            cookies_list = [f"{k}={v}" for k, v in res.cookies.items()]
            cookies_list.append("languageCode=ar")
            cookies_list.append("language=ar")
            user_cookies = "; ".join(cookies_list)
            print("[✅] محرك الأتمتة: تم استخراج وتحديث كوكيز الـ PHPSESSID الحية بنجاح كاسح!", flush=True)
            return True
        print(f"[❌] محرك الأتمتة: رفض السيرفر الدخول، الرمز: {res.status_code}", flush=True)
        return False
    except Exception as e:
        print(f"[❌] خطأ محرك الأتمتة أثناء توليد الجلسة: {e}", flush=True)
        return False

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

def api_register_player(username, password, retry=True):
    global user_cookies
    
    # إذا كانت الكوكيز فارغة أو افتراضية، يتم توليدها فوراً تلقائياً
    if "PHPSESSID" not in user_cookies:
        refresh_agent_cookies_dynamically()
        
    try:
        session = tls_client.Session(client_identifier="chrome_120", random_tls_extensions_order=True)
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

        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}

        print(f"[🚀] قذف حزمة إنشاء اللاعب الموحدة: {username}", flush=True)
        res = session.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, cookies=cookie_dict, timeout_seconds=6)
        print(f"[🔬] رد لوحة إنشاء الحساب العكسي: الرمز {res.status_code}", flush=True)
        
        # 🌟 ذكاء برمي كاسح: إذا انتهت صلاحية الجلسة المفتوحة (403)، يقوم بتسجيل الدخول الفوري وسحب كوكيز طازجة بالخلفية ويعيد المحاولة في نفس الثانية!
        if res.status_code == 403 and retry:
            print("[⚠️] تم رصد جلسة كوكيز معلقة، جاري التجديد الفوري آلياً بالخلفية وإعادة المحاولة...", flush=True)
            if refresh_agent_cookies_dynamically():
                return api_register_player(username, password, retry=False)
        
        if res.status_code == 200:
            try:
                res_data = res.json()
                if res_data.get("result") == 1 or res_data.get("status") is True:
                    return True, "نجاح"
                return False, res_data.get("notification", {}).get("content", "خطأ في بيانات المدخلات باللوحة")
            except:
                return False, "فشل فك تشفير حزمة الرد الفعلي للوحة."
        return False, f"رد اللوحة بـ الرمز {res.status_code}"
    except Exception as e:
        # إذا علق الطلب في جدار حماية Cloudflare بسبب كوكيز تالفة، ينكسر التجميد تلقائياً خلال 6 ثوانٍ ويجدد الجلسة بالخلفية
        if retry:
            print("[⚠️] انتهت مهلة الـ 6 ثوانٍ، جاري تجديد الكوكيز آلياً بالخلفية وإعادة المحاولة...", flush=True)
            if refresh_agent_cookies_dynamically():
                return api_register_player(username, password, retry=False)
        return False, f"تعذر الاتصال التلقائي باللوحة حالياً. تفاصيل: {str(e)}"

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in user_steps:
        del user_steps[uid]
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("🔄 تجديد الجلسة آلياً (للمالك)"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة التحكم ذاتية الأتمتة والتجديد بالكامل كلياً! 🎉", reply_markup=markup)

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
        if current_state == "WAITING_PASSWORD":
            username = user_steps[uid].get("username")
            password = text
            del user_steps[uid]
            global_bot.send_message(chat_id, "⚡️ جارٍ إنشاء حساب اللاعب وتأكيد الجلسة آلياً بالخلفية الحية...")
            
            success, detail = api_register_player(username, password)
            if success:
                try:
                    log_line = json.dumps({"login": username, "password": password}, ensure_ascii=False) + "\n"
                    f = open(DB_FILE, "a", encoding="utf-8")
                    f.write(log_line)
                    f.close()
                except:
                    pass
                global_bot.send_message(chat_id, f"✅ **تم إنشاء الحساب بنجاح سحابي كاسح ومطابق 100%!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
            else:
                global_bot.send_message(chat_id, f"⚠️ {str(detail)[:150]}", parse_mode="Markdown")
            return

    # زر المالك الجديد لفحص الأتمتة الميكانيكية وتوليد الجلسة بضغطة زر
    if (text == "🔄 تجديد الجلسة آلياً (للمالك)" or "تجديد الجلسة" in text) and uid == OWNER_ID:
        global_bot.send_message(chat_id, "🔄 جاري تشغيل محاكي المتصفح البشري وتوليد كوكيز حية جديدة طازجة...")
        if refresh_agent_cookies_dynamically():
            global_bot.send_message(chat_id, "✅ **تمت الأتمتة وسحب الكوكيز آلياً بنجاح قطعي للأبد! البوت مستعد للعمل الصاروخي.**")
        else:
            global_bot.send_message(chat_id, "❌ **فشلت الأتمتة التلقائية!** جدار حماية الموقع معلق حالياً.")
        return
        
    if text == "👤 حسابي":
        markup_inline = telebot.types.InlineKeyboardMarkup()
        markup_inline.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ اضغط على الزر لإنشاء حساب لاعب فوراً.", reply_markup=markup_inline)
        return
    if text == "📥 إيداع / شحن رصيد":
