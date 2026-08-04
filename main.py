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

AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"

user_cookies = "languageCode=ar; language=ar"
user_steps = {}

global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

def refresh_agent_session():
    global user_cookies
    print("[🔄] جاري محاولة تجديد الجلسة آلياً...", flush=True)
    try:
        session = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        init_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        }
        session.get(LOGIN_PAGE_URL, headers=init_headers, timeout_seconds=10)
        time.sleep(1.0)

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
            if "languageCode" not in res.cookies:
                cookies_list.append("languageCode=ar")
                cookies_list.append("language=ar")
            user_cookies = "; ".join(cookies_list)
            print("[✅] تم تجديد الكوكيز آلياً بنجاح!", flush=True)
            return True
        print(f"[❌] اللوحة رفضت الدخول الآلي بالرمز: {res.status_code}", flush=True)
        return False
    except Exception as e:
        print(f"[❌] خطأ شبكي أثناء تجديد الجلسة: {e}", flush=True)
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
    return "🚀 BOT IS LIVE AND RUNNING 24/7"

def api_register_player(username, password, retry=True):
    global user_cookies
    try:
        session = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
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

        print(f"[🚀] قذف حزمة إنشاء اللاعب: {username}", flush=True)
        res = session.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, cookies=cookie_dict, timeout_seconds=8)
        print(f"[🔬] رد لوحة إنشاء الحساب العكسي: الرمز {res.status_code}", flush=True)

        if res.status_code == 403 and retry:
            if refresh_agent_session():
                return api_register_player(username, password, retry=False)
        
        if res.status_code == 200:
            try:
                res_data = res.json()
                if res_data.get("result") == 1 or res_data.get("status") is True:
                    return True, "نجاح"
                return False, res_data.get("notification", {}).get("content", "خطأ في بيانات اللوحة العكسية")
            except:
                return False, "فشل فك تشفير حزمة رد اللوحة."
                
        return False, f"رد اللوحة بالرمز {res.status_code}"
    except Exception as e:
        return False, f"انتهت مهلة الاتصال باللوحة أو الكوكيز منتهية. تفاصيل: {str(e)}"

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
        markup.add(telebot.types.KeyboardButton("⚙️ تحديت الكوكيز يدوياً (للمالك)"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة الكاشير السحابية المحدثة! 🎉", reply_markup=markup)

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
            global_bot.send_message(chat_id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة...")
            
            # 🌟 تم إلغاء الـ Threading هنا وتشغيل المهمة مباشرة لكسر التعليق وضمان تدفق الرد الفوري لتليجرام!
            success, detail = api_register_player(username, password)
            if success:
                try:
                    log_line = json.dumps({"login": username, "password": password}, ensure_ascii=False) + "\n"
                    f = open(DB_FILE, "a", encoding="utf-8")
                    f.write(log_line)
                    f.close()
                except:
                    pass
                global_bot.send_message(chat_id, f"✅ **تم إنشاء الحساب بنجاح!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
            else:
                global_bot.send_message(chat_id, f"⚠️ تعذر الإنشاء الآلي:\n`{str(detail)[:150]}`", parse_mode="Markdown")
            return
            
        if current_state == "WAITING_COOKIES" and uid == OWNER_ID:
            global user_cookies
            user_cookies = text
            del user_steps[uid]
            global_bot.send_message(chat_id, "✅ **تم حقن الكوكيز اليدوية بنجاح وبدء تفعيل الإنشاء الفوري!**")
            return

    if text == "⚙️ تحديت الكوكيز يدوياً (للمالك)" and uid == OWNER_ID:
        user_steps[uid] = {"state": "WAITING_COOKIES"}
        global_bot.send_message(chat_id, f"🔑 **الكوكيز بالذاكرة حالياً:**\n`{str(user_cookies)[:40]}...`\n\nتفضل بلصق وإرسال سطر الـ Cookies الكامل المستخرج حياً من متصفحك لتنشيط الحساب فوراً:")
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
        threading.Thread(target=refresh_agent_session, daemon=True).start()
    except Exception as e:
        print(f"[❌] فشل تهيئة الـ Webhook: {e}", flush=True)

threading.Thread(target=start_webhook_setup, daemon=True).start()
