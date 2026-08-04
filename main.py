import os
import json
import time
import string
import random
import threading
import telebot
from flask import Flask, request

# 💡 تخطي حظر الـ 403 باستخدام محاكي بصمة المتصفح الموثق
import tls_client  

BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
DB_FILE = "players_db.txt"

# النطاق الرسمي للوحة
PANEL_BASE = "https://texas4win.com"
REGISTER_PLAYER_API_URL = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"

# الرابط السحابي الكامل والخاص بك على منصة Render لإصلاح التوجيه التلقائي
RENDER_URL = "https://onrender.com"

# متغير الكوكيز الافتراضي
user_cookies = "PHPSESSID=488a394c83f1f914e66ca4b00759bfa0d8497f6a3eb0036d5912048678335557; languageCode=ar; language=ar"

# هيكل حفظ الخطوات والحالات الصارم البديل لـ next_step_handler لضمان استقرار الـ Webhook
user_steps = {}

# تهيئة البوت (تعطيل الـ Threaded لضمان ثبات التوجيه عبر Flask)
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

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
    return "🚀 BOT IS LIVE AND RUNNING 24/7 (WEBHOOK STABLE MODE)"

# --- دالة الاتصال باللوحة عبر محاكي المتصفح لتخطي الـ 403 ---
def api_register_player(username, password):
    global user_cookies
    try:
        # 🌟 تم إصلاح الغلطة المطبعية هنا وحذف حرف الـ s الزائد بنجاح تام
        session = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True
        )
        
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

        time.sleep(random.uniform(0.5, 1.2))
        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}

        print(f"[🚀] قذف حزمة الإنشاء المشفرة للاعب الجديد: {username}", flush=True)
        res = session.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, cookies=cookie_dict, timeout_seconds=15)
        print(f"[🔬] استجابة اللوحة: الرمز {res.status_code}", flush=True)
        
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
            except:
                return False, "فشل فك حزمة الـ JSON العكسية من اللوحة."
        return False, f"رمز خطأ الاستجابة {res.status_code}"
    except Exception as e:
        return False, str(e)

# ========================================== #
# 3. محرك تليجرام وقوائم المعالجة والحالات #
# ========================================== #
@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in user_steps:
        del user_steps[uid]  # تصفير أي عمليات معلقة بالكامل
        
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    if uid == OWNER_ID:
        markup.add(telebot.types.KeyboardButton("⚙️ تحديث الكوكيز (للمالك)"))
    global_bot.send_message(message.chat.id, "👋 مرحباً بك في لوحة الكاشير السحابية المحدثة بالملي! 🎉\n\nتفضل بالاختيار من القائمة أدناه بحسب طلبك:", reply_markup=markup)

@global_bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    uid = call.from_user.id
    if call.data == "start_reg":
        user_steps[uid] = {"state": "WAITING_USERNAME"}
        global_bot.send_message(chat_id, "👤 يرجى إرسال اسم المستخدم المطلوب للحساب الجديد:")

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
            
            global_bot.send_message(chat_id, "⚡️ جارٍ إنشاء حسابك وتأكيده مع اللوحة عبر الكوكيز الموثقة...")
            threading.Thread(target=run_safe_api_task, args=(chat_id, uid, username, password), daemon=True).start()
            return
            
        elif current_state == "WAITING_COOKIES" and uid == OWNER_ID:
            global user_cookies
            user_cookies = text
            del user_steps[uid]
            global_bot.send_message(chat_id, "✅ **تم حقن الكوكيز الموزونة والمطابقة بنجاح!**")
            return

    if (text == "⚙️ تحديث الكوكيز (للمالك)" or "تحديث الكوكيز" in text) and uid == OWNER_ID:
        user_steps[uid] = {"state": "WAITING_COOKIES"}
        global_bot.send_message(chat_id, f"🔑 **حالة الكوكيز الحالية بالذاكرة:**\n`{str(user_cookies)[:40]}...`\n\nتفضل بلصق وإرسال سطر الـ Cookies الكامل المستخرج حياً لتنشيط البوت:")
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
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n")
        global_bot.send_message(chat_id, f"✅ **تم إنشاء الحساب بنجاح سحابي كاسح ومطابق 100%!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
    else:
        global_bot.send_message(chat_id, f"⚠️ تعذر الإنشاء التلقائي بسبب رد اللوحة العكسي:\n`{str(detail)[:150]}`", parse_mode="Markdown")

def start_webhook_setup():
    time.sleep(2)  
    try:
        print("[🔄] جاري تصفير اتصالات تليجرام السابقة...", flush=True)
        global_bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
        print(f"[🌐] ربط الـ Webhook بالمسار الآمن الجديد: {webhook_url}", flush=True)
        global_bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        print("[✅] تم تهيئة واستقرار النظام بالملي مع تليجرام!", flush=True)
    except Exception as e:
        print(f"[❌] فشل تهيئة الـ Webhook: {e}", flush=True)

if __name__ == "__main__":
    print("[+] إطلاق نظام الأتمتة السحابي والـ Web Service على سيرفر Render...", flush=True)
    threading.Thread(target=start_webhook_setup, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
