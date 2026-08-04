import os
import json
import time
import string
import random
import threading
import telebot
from flask import Flask

# 💡 حل مشكلة الـ 403 والتجميد: تهيئة متطورة ومضمونة لمحاكي المتصفح المشفر
import tls_client  

# ========================================== #
# 1. إعداد خادم الويب لمنصة Render (الإقلاع) #
# ========================================== #
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 BOT IS LIVE AND RUNNING 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ========================================== #
# 2. إعداد مفاتيح وبوابات الـ API الموثقة #
# ========================================== #
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

PANEL_BASE = "https://texas4win.com"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

# متغير الكوكيز الافتراضي
user_cookies = "PHPSESSID=488a394c83f1f914e66ca4b00759bfa0d8497f6a3eb0036d5912048678335557; languageCode=ar; language=ar"
user_steps = {}

def api_register_player(username, password):
    global user_cookies
    
    try:
        # 🌟 محاكي متصفح من إصدار مستقر جداً لتفادي تجميد الاتصال السحابي
        session = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extensions_order=True
        )
        
        # تفكيك الكوكيز بطريقة آمنة وصارمة لمنع تجميد المكتبة
        cookie_dict = {}
        if user_cookies:
            for cookie in user_cookies.split(";"):
                if "=" in cookie:
                    parts = cookie.strip().split("=", 1)
                    if len(parts) == 2:
                        cookie_dict[parts[0].strip()] = parts[1].strip()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": PANEL_BASE,
            "Referer": f"{PANEL_BASE}/global/agent/User/index",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        }

        # تقليص وقت الانتظار العشوائي لسرعة الاستجابة ومنع تجميد الخيط السحابي
        time.sleep(random.uniform(0.5, 1.5))
        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}

        print(f"[🚀] إرسال حزمة الإنشاء الفورية للاعب: {username}", flush=True)
        
        # 🌟 تعديل الـ Timeout وتمريره بشكل صحيح لمنع الوقوف لانهائياً وضمان كسر الاتصال إذا تأخرت اللوحة
        res = session.post(
            REGISTER_PLAYER_API_URL, 
            json=payload, 
            headers=headers, 
            cookies=cookie_dict,
            timeout_seconds=15
        )
        
        print(f"[🔬] استجابة اللوحة الفورية: الرمز {res.status_code}", flush=True)
        
        if res.status_code == 200:
            try:
                res_data = res.json()
                if res_data.get("result") == 1 or res_data.get("status") is True:
                    return True, "نجاح"
                try:
                    msg = res_data["notification"]["content"]
                except:
                    msg = res_data.get("html", res.text[:100])
                return False, msg
            except Exception as json_err:
                return False, f"فشل قراءة الرد (JSON Error): {str(json_err)}"
                
        return False, f"استجابة اللوحة برمز خطأ: {res.status_code}"
        
    except Exception as e:
        print(f"[❌] خطأ داخلي في دالة الاتصال: {e}", flush=True)
        return False, f"خطأ في الاتصال: {str(e)}"

# ========================================== #
# 3. إعداد محرك تليجرام وقوائم التحكم الحية #
# ========================================== #
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    if message.from_user.id == OWNER_ID:
        markup.add(telebot.types.KeyboardButton("⚙️ تحديث الكوكيز (للمالك)"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة الكاشير السحابية المحدثة بالملي! 🎉\n\nتفضل بالاختيار من القائمة أدناه بحسب طلبك:", reply_markup=markup)

@global_bot.message_handler(func=lambda message: True)
def core_menu(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text
    
    if (text == "⚙️ تحديث الكوكيز (للمالك)" or "تحديث الكوكيز" in text) and uid == OWNER_ID:
        global_bot.send_message(chat_id, f"🔑 **حالة الكوكيز الحالية بالذاكرة:**\n`{str(user_cookies)[:40]}...`\n\nتفضل بلصق وإرسال سطر الـ Cookies الكامل المستخرج حياً لتنشيط البوت:")
        global_bot.register_next_step_handler(message, save_live_cookies)
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

def save_live_cookies(message):
    global user_cookies
    user_cookies = message.text.strip()
    global_bot.send_message(message.chat.id, "✅ **تم حقن الكوكيز الموزونة والمطابقة بنجاح!**")

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
    if uid not in user_steps:
        return
    password = message.text.strip()
    username = user_steps[uid]["username"]
    
    global_bot.send_message(message.chat.id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة عبر الكوكيز الموثقة...")
    
    # حماية الخيط الخلفي من التجمد عبر تفعيل نظام الإغلاق الذاتي والـ Daemon المستقر
    t = threading.Thread(target=run_safe_api_task, args=(message.chat.id, uid, username, password))
    t.daemon = True
    t.start()

def run_safe_api_task(chat_id, uid, username, password):
    success, detail = api_register_player(username, password)
    if success:
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n")
        global_bot.send_message(chat_id, f"✅ **تم إنشاء الحساب بنجاح سحابي كاسح ومطابق 100%!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
    else:
        global_bot.send_message(chat_id, f"⚠️ تعذر الإنشاء التلقائي بسبب رد اللوحة العكسي:\n`{str(detail)[:150]}`", parse_mode="Markdown")
        
    if uid in user_steps:
        del user_steps[uid]

def run_bot_polling():
    print("[+] إطلاق قناة الاستماع الحية للبوت بالخلفية...", flush=True)
    try:
        global_bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
    except:
        pass

    while True:
        try:
            global_bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            if "Conflict" in str(e) or "409" in str(e):
                time.sleep(5)
            else:
                time.sleep(3)

if __name__ == "__main__":
    print("[+] إطلاق نظام الأتمتة السحابي والـ Web Service على سيرفر Render...", flush=True)
    t = threading.Thread(target=run_bot_polling)
    t.daemon = True
    t.start()
    run_flask()
