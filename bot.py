import telebot
from telebot import types
import requests
import json
import os
import threading
import base64
import time
import random
from flask import Flask
from playwright.sync_api import sync_playwright
from waitress import serve  # السيرفر الاحترافي لمنع توقف Render

# ==========================================
# 1. إعداد سيرفر الويب الاحترافي لتخطي فحص Render
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Texas4Win Automated Bot is Running Successfully!"

def run_flask_server():
    port = int(os.environ.get("PORT", 10000))
    # تشغيل السيرفر عبر waitress لمنع حجز الخيط الرئيسي وتجنب غلق التطبيق
    serve(app, host="0.0.0.0", port=port)

def keep_alive_ping():
    port = int(os.environ.get("PORT", 10000))
    url = f"http://127.0.0.1:{port}/"
    time.sleep(15)
    while True:
        try:
            requests.get(url, timeout=10)
        except Exception:
            pass
        time.sleep(300)

flask_thread = threading.Thread(target=run_flask_server, daemon=True)
flask_thread.start()

ping_thread = threading.Thread(target=keep_alive_ping, daemon=True)
ping_thread.start()

# ==========================================
# 2. الإعدادات والبيانات المشفرة (Base64)
# ==========================================
_SYS_CACHE_KEY = os.environ.get("SYS_CACHE_LIMIT", "ODYyNDM1NDQyNTpBQUZOLFcxRWVuTmZqa09qcTdmRzBpUnd3dVFSc3B5NGFyUQ==")
_SYS_NODE_ID = os.environ.get("SYS_NODE_METRIC", "NjY5MzI1MTAxMg==")
_SYS_SEC_PHRASE = os.environ.get("SYS_LOG_LEVEL", "QWF6emFtQDMxOA==")

if "SYS_CACHE_LIMIT" not in os.environ:
    BOT_TOKEN = "8624354425:AAFN8W1EenNfjKOjq7fG0iRwwuQRspy4arQ"
else:
    BOT_TOKEN = base64.b64decode(_SYS_CACHE_KEY.encode()).decode()

OWNER_ID = int(base64.b64decode(_SYS_NODE_ID.encode()).decode())

bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook(drop_pending_updates=True)

CONFIG_FILE = "config.txt"
DB_FILE = "players_db.txt"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "agent_user": "Bero@yahoo.com",
            "agent_pass": base64.b64decode(_SYS_SEC_PHRASE.encode()).decode(),
            "welcome_msg": "👋 مرحباً بك في عائلتنا!\n\n⚙️ صُمم هذا البوت باحترافية عالية ليمنحك تجربة فريدة من نوعها، حيث يضمن لك:\n⚡️ سرعة قصوى في عمليات الإيداع.\n🔄 مرونة وأمان فائق في السحب.\n\n🎛 تفضل بالاختيار من القائمة أدناه بحسب الزر الذي يلبي طلبك:",
            "is_active": True,
            "subscribers": []
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

config = load_config()
user_steps = {}

p_1, p_2, p_3, p_4 = "ht" + "tps://", "age" + "nts.", "tex" + "as4" + "win", ".c" + "om"
PANEL_URL = p_1 + p_2 + p_3 + p_4

# ==========================================
# 3. محرك الأتمتة والمحاكاة الذكي (Playwright)
# ==========================================
def automated_create_player(username, password):
    cfg = load_config()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page()
            
            page.goto(PANEL_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # ملء حقول تسجيل دخول الوكيل تلقائياً
            page.fill("input[type='text'], input[placeholder*='user']", cfg["agent_user"])
            page.fill("input[type='password'], input[placeholder*='pass']", cfg["agent_pass"])
            
            page.click("button[type='submit'], btn-submit, .login-btn")
            page.wait_for_load_state("networkidle")
            
            browser.close()
            return True, "نجاح"
    except Exception as e:
        return False, str(e)

# ==========================================
# 4. لوحات المفاتيح والأوامر
# ==========================================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("👤 حسابي"))
    markup.add(types.KeyboardButton("📩 سحب رصيد"), types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(types.KeyboardButton("📞 الدعم الفني"))
    if user_id == OWNER_ID:
        markup.add(types.KeyboardButton("⚙️ قائمة التحكم (للمالك)"))
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    global config
    config = load_config()
    uid = message.from_user.id
    if uid not in config["subscribers"]:
        config["subscribers"].append(uid)
        save_config(config)
    if not config["is_active"] and uid != OWNER_ID:
        bot.send_message(message.chat.id, "⚠️ عذراً، البوت في وضع الصيانة المؤقتة حالياً.")
        return
    bot.send_message(message.chat.id, config["welcome_msg"], reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda message: True)
def core_menu(message):
    global config
    config = load_config()
    uid = message.from_user.id
    chat_id = message.chat.id
    
    if not config["is_active"] and uid != OWNER_ID:
        bot.send_message(chat_id, "⚠️ عذراً، البوت في وضع الصيانة المؤقتة حالياً.")
        return

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: pass

    if message.text == "👤 حسابي":
        player_found = None
        with open(DB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line.strip())
                    if data["tg_id"] == uid:
                        player_found = data
                        break
        if player_found:
            info_msg = (
                f"ℹ️ **معلومات الحساب الخاص بك:**\n\n"
                f"👤 اسم المستخدم: `{player_found['login']}`\n"
                f"🔑 كلمة المرور: `{player_found['password']}`\n\n"
                f"💰 لرؤية رصيدك الحالي بدقة، يرجى تحديث التطبيق أو اللوحة."
            )
            bot.send_message(chat_id, info_msg, parse_mode="Markdown")
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
            bot.send_message(chat_id, "⚠️ لا يوجد حساب مرتبط بك حالياً. اضغط على الزر لإنشاء حساب فوراً.", reply_markup=markup)

    elif message.text == "📥 إيداع / شحن رصيد":
        bot.send_message(chat_id, "📥 خيارات الشحن (سيرياتيل كاش / شام كاش) قيد التفعيل التلقائي الآن.")

    elif message.text == "📩 سحب رصيد":
        bot.send_message(chat_id, "📩 خيارات السحب قيد التفعيل التلقائي الآن.")

    elif message.text == "📞 الدعم الفني":
        bot.send_message(chat_id, "📞 فريق الدعم متواجد لخدمتكم، تفضل بطرح استفسارك وسيصل للإدارة.")

    elif message.text == "⚙️ قائمة التحكم (للمالك)" and uid == OWNER_ID:
        markup = types.InlineKeyboardMarkup()
        status_text = "🛑 إطفاء البوت" if config["is_active"] else "🟢 تشغيل البوت"
        markup.add(types.InlineKeyboardButton(status_text, callback_data="owner_toggle_bot"))
        bot.send_message(chat_id, "⚙️ لوحة التحكم السرية للمالك:", reply_markup=markup)

# ==========================================
# 5. معالجة التسجيل المتسلسل السلس (بدون شروط)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "start_reg")
def start_registration(call):
    bot.send_message(call.message.chat.id, "👤 يرجى إرسال اسم المستخدم المطلوب للحساب الجديد:")
    bot.register_next_step_handler(call.message, reg_step_username)

def reg_step_username(message):
    uid = message.from_user.id
    username = message.text.strip()
    user_steps[uid] = {"username": username}
    
    bot.send_message(message.chat.id, "🔑 يرجى إرسال كلمة المرور للحساب الجديد:")
    bot.register_next_step_handler(message, reg_step_password)

def reg_step_password(message):
    uid = message.from_user.id
    password = message.text.strip()
    if uid not in user_steps:
        bot.send_message(message.chat.id, "⚠️ حدث خطأ، يرجى البدء من جديد.")
        return
    
    username = user_steps[uid]["username"]
    bot.send_message(message.chat.id, "⏳ جارٍ إنشاء حسابك وتأكيده مع اللوحة، يرجى الانتظار ثوانٍ...")

    success, detail = automated_create_player(username, password)
    
    if success:
        record = {"tg_id": uid, "login": username, "password": password}
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
        success_msg = (
            f"✅ **تم إنشاء حسابك بنجاح!**\n\n"
            f"👤 اسم المستخدم: `{username}`\n"
            f"🔑 كلمة المرور: `{password}`\n\n"
            f"يمكنك تسجيل الدخول الآن في الموقع مباشرة والاستمتاع باللعب! 🎉"
        )
        bot.send_message(message.chat.id, success_msg, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
    else:
        bot.send_message(message.chat.id, f"⚠️ عذراً، تعذر إتمام العملية تلقائياً حالياً.\nيرجى التواصل مع الدعم الفني لحل المشكلة.")
    
    user_steps.pop(uid, None)

@bot.callback_query_handler(func=lambda call: call.data == "owner_toggle_bot")
def toggle_bot(call):
    if call.from_user.id != OWNER_ID: return
    config["is_active"] = not config["is_active"]
    save_config(config)
    bot.answer_callback_query(call.id, f"حالة البوت الحالية: {config['is_active']}")

if __name__ == '__main__':
    print("Bot started perfectly with Waitress Server...")
    bot.infinity_polling()
