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
    return "🚀 BOT IS LIVE AND RUNNING 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ========================================== #
# 2. إعداد مفاتيح وبوابات الـ API الموثقة    #
# ========================================== #
# 🌟 التوكن الجديد الصافي والمطهر تماماً لمنع الـ 409
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

# النطاق الرسمي الأساسي الموثق لحساب كاشير عُمير لعام 2026
PANEL_BASE = "https://texas4win.com"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

# متغير التوكن السحري الذي سيمرره المالك يدوياً للبوت لسحق الـ 403 للأبد
access_token = "eyJ0eXAiOiJKV1QiLC...pDdyQxfKUY"
user_steps = {}

def api_register_player(username, password):
    global access_token
    
    # الترويسات الرسمية المطابقة تماماً لملف عُمير صفحة 11 وصفحة 3
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json", 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": PANEL_BASE,
        "Referer": f"{PANEL_BASE}/"
    }
    
    time.sleep(random.uniform(1.5, 3.5))
    email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
    payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}
    
    try:
        print(f"[🚀] قذف حزمة الإنشاء للاعب الجديد: {username} عبر التوكن النشط", flush=True)
        res = requests.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, timeout=20)
        print(f"[🔬] رد اللوحة على حركة الإنشاء: الرمز {res.status_code} - المحتوى: {res.text[:150]}", flush=True)
        
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("result") == 1 or res_data.get("status") is True: 
                return True, "نجاح"
            if res_data.get("result") == "ex":
                return False, "التوكن ميت أو منتهي الصلاحية، يرجى تزويد البوت بتوكن جديد حياً."
            try: msg = res_data["notification"]["content"]
            except: msg = res_data.get("html", res.text)
            return False, msg
            
        return False, f"استجابة اللوحة: {res.status_code}"
    except Exception as e: 
        return False, str(e)

# ========================================== #
# 3. إعداد محرك تليجرام وقوائم التحكم الحية   #
# ========================================== #
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
global_bot.delete_webhook(drop_pending_updates=True)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    if message.from_user.id == OWNER_ID: 
        markup.add(telebot.types.KeyboardButton("⚙️ تحديث التوكن (للمالك)"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة الكاشير السحابية الموثقة بالـ API المباشر! 🎉\n\nتفضل بالاختيار من القائمة أدناه بحسب طلبك:", reply_markup=markup)

@global_bot.message_handler(func=lambda message: True)
def core_menu(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text
    
    if text == "⚙️ تحديث التوكن (للمالك)" and uid == OWNER_ID:
        global_bot.send_message(chat_id, f"🔑 **حالة التوكن الحالي بالذاكرة:**\n`{str(access_token)[:30]}...`\n\nتفضل بإرسال الـ AccessToken الجديد الصافي والمستخرج من متصفحك حياً لتنشيط البوت فوراً وبدون ريستارت:")
        global_bot.register_next_step_handler(message, save_live_token)
        return
        
    if text == "👤 حسابي":
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ اضغط على الزر لإنشاء حساب لاعب فوراً.", reply_markup=markup)
        return
        
    if text == "📥 إيداع / شحن رصيد": global_bot.send_message(chat_id, "📥 خيارات الشحن التلقائي قيد التفعيل بالـ API."); return
    if text == "📩 سحب رصيد": global_bot.send_message(chat_id, "📩 خيارات السحب قيد التفعيل بالـ API."); return
    if text == "📞 الدعم الفني": global_bot.send_message(chat_id, "📞 فريق الدعم متواجد لخدمتكم دائماً."); return

def save_live_token(message):
    global access_token
    token_input = message.text.strip()
    if "Bearer " in token_input:
        token_input = token_input.replace("Bearer ", "")
    access_token = token_input
    global_bot.send_message(message.chat.id, "✅ **تم حقن وتنشيط التوكن الحي بنجاح باهر بداخل ذاكرة السيرفر!**\n\nالبوت مستعد الآن لإنشاء الحسابات كالسهم وتخطي الـ 403 كلياً للأبد!")

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
        global_bot.send_message(chat_id, f"✅ **تم إنشاء حسابك بنجاح وبصلاحية المطورين المعتمدة!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
    else:
        global_bot.send_message(chat_id, f"⚠️ تعذر الإنشاء التلقائي:\n`{str(detail)[:150]}`", parse_mode="Markdown")
    if uid in user_steps: del user_steps[uid]

def run_bot_polling():
    print("[+] إطلاق قناة الاستماع الحية للبوت بنظام الإنعاش الآمن بالخلفية...", flush=True)
    while True:
        try:
            global_bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"[⚠️] تنبيه شبكي بالخلفية، إعادة اتصال آلي: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    print("[+] إطلاق نظام الأتمتة السحابي والـ Web Service على سيرفر Render...", flush=True)
    # 1. إقلاع محرك تليجرام في خيط مستقل بالخلفية بنظام الحماية الجديد لمنع قفل السيرفر
    t = threading.Thread(target=run_bot_polling)
    t.daemon = True
    t.start()
    # 2. تشغيل الـ Flask بالخيط الرئيسي ليرد فوراً على سيرفر ريندر بالرمز 200 وسحق الدائرة
    run_flask()
