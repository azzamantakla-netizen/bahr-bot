import os
import json
import time
import string
import random
import threading
import telebot
from flask import Flask, request
import requests

BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

PANEL_BASE = "https://texas4win.com"
SIGNIN_API_URL = f"{PANEL_BASE}/global/api/UserApi/signIn"
REFRESH_TOKEN_API_URL = f"{PANEL_BASE}/global/api/UserApi/refreshToken"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

RENDER_URL = "https://bahr-bot-c3ac.onrender.com"

AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"

# ذاكرة حفظ الرموز والخطوات الديناميكية (ستعمل فور حقنها بالبوت)
access_token = ""
refresh_token = ""
user_steps = {}

global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

def api_agent_signin():
    global access_token, refresh_token
    print("[🔄] جاري طلب تسجيل دخول الوكيل الرسمي عبر بوابة الـ API...", flush=True)
    try:
        headers = {"Content-Type": "application/json"}
        payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
        res = requests.post(SIGNIN_API_URL, json=payload, headers=headers, timeout=15)
        
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("status") is True and "result" in res_data:
                access_token = res_data["result"].get("accessToken")
                refresh_token = res_data["result"].get("refreshToken")
                print("[✅] نجاح تسجيل الدخول الرسمي واستلام مفاتيح العبور السحابية!", flush=True)
                return True
        print(f"[❌] فشل الدخول عبر الـ API، الرمز: {res.status_code}", flush=True)
        return False
    except Exception as e:
        print(f"[❌] خطأ أثناء الاتصال ببوابة تسجيل الدخول: {e}", flush=True)
        return False

def api_refresh_access_token():
    global access_token, refresh_token
    print("[🔄] جاري تحديث الرمز المؤقت تلقائياً...", flush=True)
    if not refresh_token:
        return api_agent_signin()
    try:
        headers = {"Content-Type": "application/json"}
        payload = {"refreshToken": refresh_token}
        res = requests.post(REFRESH_TOKEN_API_URL, json=payload, headers=headers, timeout=15)
        
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("status") is True and "result" in res_data:
                access_token = res_data["result"].get("accessToken")
                refresh_token = res_data["result"].get("refreshToken")
                print("[✅] تم تدوير وتحديث رموز الأمان بنجاح!", flush=True)
                return True
        return api_agent_signin()
    except Exception as e:
        print(f"[❌] خطأ أثناء تحديث الرمز: {e}", flush=True)
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
    return "🚀 BOT IS LIVE AND RUNNING 24/7 (OFFICIAL API MODE)"

def api_register_player(username, password, retry=True):
    global access_token
    if not access_token:
        return False, "الرجاء تحديث مفاتيح الـ API (Tokens) أولاً من قائمة المالك."
        
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}

        print(f"[🚀] قذف طلب إنشاء اللاعب عبر الـ API الرسمي: {username}", flush=True)
        res = requests.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, timeout=15)
        
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("result") == "ex" and retry:
                if api_refresh_access_token():
                    return api_register_player(username, password, retry=False)
            if res_data.get("status") is True and (res_data.get("result") == 1 or res_data.get("result") is True):
                return True, "نجاح"
            msg = res_data.get("notification", {}).get("content", "خطأ في بيانات الإنشاء")
            return False, msg
        return False, f"استجابة سيرفر اللوحة بالرمز: {res.status_code}"
    except Exception as e:
        return False, str(e)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in user_steps:
        del user_steps[uid]
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("⚙️ إدخال مفتاح الـ API يدوياً (للمالك)"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة الكاشير السحابية الرسمية المحدثة بالملي! 🎉", reply_markup=markup)

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
            global_bot.send_message(chat_id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة عبر البوابة الرسمية...")
            
            success, detail = api_register_player(username, password)
            if success:
                try:
                    log_line = json.dumps({"login": username, "password": password}, ensure_ascii=False) + "\n"
                    f = open(DB_FILE, "a", encoding="utf-8")
                    f.write(log_line)
                    f.close()
                except:
                    pass
                global_bot.send_message(chat_id, f"✅ **تم إنشاء الحساب بنجاح رسمي كاسح ومطابق 100%!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
            else:
                global_bot.send_message(chat_id, f"⚠️ تعذر الإنشاء عبر الـ API:\n`{str(detail)[:150]}`", parse_mode="Markdown")
            return
        if current_state == "WAITING_TOKEN" and uid == OWNER_ID:
            global access_token, refresh_token
            try:
                tokens = json.loads(text)
                access_token = tokens.get("accessToken")
                refresh_token = tokens.get("refreshToken")
                del user_steps[uid]
                global_bot.send_message(chat_id, "✅ **تم حقن التوكنات الرسمية بنجاح! البوت جاهز لإنشاء اللاعبين.**")
            except:
                global_bot.send_message(chat_id, "❌ صيغة الـ JSON خاطئة، الرجاء نسخ حزمة الرد الكاملة.")
            return

    if text == "⚙️ إدخال مفتاح الـ API يدوياً (للمالك)" and uid == OWNER_ID:
        user_steps[uid] = {"state": "WAITING_TOKEN"}
        global_bot.send_message(chat_id, "🔑 يرجى إرسال حزمة نجاح الـ JSON المستخرجة (Success response example) التي تحتوي على الـ accessToken والـ refreshToken:")
        return
        
    if text == "👤 حسابي":
        markup_inline = telebot.types.InlineKeyboardMarkup()
        markup_inline.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ اضغط على الزر لإنشاء حساب لاعب فوراً.", reply_markup=markup_inline)
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

def start_webhook_setup():
    time.sleep(3)  
    try:
        global_bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
        global_bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        print("[✅] تم تهيئة واستقرار النظام بالملي مع تليجرام!", flush=True)
        threading.Thread(target=api_agent_signin, daemon=True).start()
    except Exception as e:
        print(f"[❌] فشل تهيئة الـ Webhook: {e}", flush=True)

threading.Thread(target=start_webhook_setup, daemon=True).start()
