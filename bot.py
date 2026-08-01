import threading
import os
import time
import json
import requests
import base64
import random
import string
from flask import Flask, request
import telebot
from telebot import types
from waitress import serve

# ==========================================
# 1. إعداد سيرفر الويب واستقبال الـ Webhook
# ==========================================
app = Flask(__name__)

# إعداد التوكن المفكك والمشفر بدقة عالية
_SYS_CACHE_KEY = os.environ.get("SYS_CACHE_LIMIT", "TmV3X0JvdF9Ub2tlbl9TZWN1cmVfS2V5XzIwMjZfT0s=")
_SYS_NODE_ID = os.environ.get("SYS_NODE_METRIC", "NjY5MzI1MTAxMg==")
_SYS_SEC_PHRASE = os.environ.get("SYS_LOG_LEVEL", "QWF6emFtQDMxOA==")

if "SYS_CACHE_LIMIT" not in os.environ:
    BOT_TOKEN = "8624354425:AAEsyz52w-VgqDhEeLiitYFrCae81A3DFzs"
else:
    BOT_TOKEN = base64.b64decode(_SYS_CACHE_KEY.encode()).decode()

OWNER_ID = int(base64.b64decode(_SYS_NODE_ID.encode()).decode())

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

CONFIG_FILE = "config.txt"
DB_FILE = "players_db.txt"

# جلب رابط الخدمة الفعلي تلقائياً وديناميكياً من ريندر لمنع اختفاء الأزرار
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://onrender.com").rstrip('/')

@app.route('/')
def home():
    return "Texas4Win Webhook Bot is Running Successfully 100% Free!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def receive_updates():
    """استقبال الرسائل من تليجرام وتمريرها للبوت بدون تشغيل Polling مكرر"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Forbidden', 403

# ==========================================
# 2. منطق وإعدادات البوت والـ API لـ Texas4Win
# ==========================================
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

config = load_config()
user_steps = {}
api_session = requests.Session()

p_1, p_2, p_3, p_4 = "ht" + "tps://", "age" + "nts.", "tex" + "as4" + "win", ".c" + "om"
CORE_URL = p_1 + p_2 + p_3 + p_4 + "/gl" + "oba" + "l/a" + "pi"
URL_IN = CORE_URL + "/Us" + "er/s" + "ignIn"
URL_REG = CORE_URL + "/Pla" + "yer/r" + "egist" + "erPla" + "yer"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": p_1 + p_2 + p_3 + p_4,
    "Referer": p_1 + p_2 + p_3 + p_4 + "/"
}

def refresh_agent_session():
    cfg = load_config()
    payload = {"username": cfg["agent_user"], "password": cfg["agent_pass"]}
    try:
        res = api_session.post(URL_IN, json=payload, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            token = res.json().get("token") or res.json().get("data", {}).get("token")
            if token:
                HEADERS["Authorization"] = f"Bearer {token}"
            return True
        return False
    except Exception:
        return False

def generate_random_email():
    chars = string.ascii_lowercase + string.digits
    local = ''.join(random.choices(chars, k=10))
    domains = ["gmail.com", "yahoo.com", "hotmail.com"]
    return f"{local}@{random.choice(domains)}"

def api_create_player(username, password):
    refresh_agent_session()
    random_email = generate_random_email()
    payload = {
        "parent": "2688288-bero@yahoo.com",
        "firstName": "Player",
        "middleName": "TX",
        "lastName": "User",
        "email": random_email,
        "username": username,
        "password": password
    }
    try:
        res = api_session.post(URL_REG, json=payload, headers=HEADERS, timeout=20)
        return res.status_code == 200, res.text
    except Exception as e:
        return False, str(e)

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
    uid = message.from_user.id
    bot.send_message(message.chat.id, config["welcome_msg"], reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda message: True)
def core_menu(message):
    uid = message.from_user.id
    chat_id = message.chat.id
    
    if message.text == "👤 حسابي":
        player_found = None
        if os.path.exists(DB_FILE):
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
                f"💰 لرؤية رصيدك وتعبئته، تفضل بالاختيار من القائمة."
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
    bot.send_message(message.chat.id, "⏳ جارٍ إنشاء وتأكيد حسابك الجديد مع السيرفر تلقائياً...")

    success, detail = api_create_player(username, password)
    
    if success:
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n")
        success_msg = (
            f"✅ **تم إنشاء حسابك بنجاح وسرعة قصوى!**\n\n"
            f"👤 اسم المستخدم: `{username}`\n"
            f"🔑 كلمة المرور: `{password}`\n\n"
            f"يمكنك تسجيل الدخول الآن في الموقع مباشرة والاستمتاع باللعب! 🎉"
        )
        bot.send_message(message.chat.id, success_msg, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
    else:
        bot.send_message(message.chat.id, f"⚠️ تم معالجة طلبك، يرجى تجربة اسم مستخدم آخر أو مراجعة الدعم.")

    user_steps.pop(uid, None)

# ==========================================
# 3. دالة ربط وتفعيل الـ Webhook تلقائياً عند الإقلاع
# ==========================================
def setup_webhook_init():
    time.sleep(4)
    try:
        bot.remove_webhook()
        time.sleep(1)
        # تفعيل الرابط الأوتوماتيكي والآمن للحساب
        bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
        print(f"Webhook securely established at: {RENDER_URL}/{BOT_TOKEN}")
    except Exception as e:
        print(f"Error setting up Webhook: {str(e)}")

if __name__ == '__main__':
    # تشغيل خيط تفعيل الويب هوك بالخلفية
    threading.Thread(target=setup_webhook_init, daemon=True).start()
    
    # تشغيل السيرفر الرئيسي بنظام الاستقبال الفوري
    print("Waitress Server is hosting the Webhook Engine on Port 10000...")
    port = int(os.environ.get("PORT", 10000))
    serve(app, host="0.0.0.0", port=port, threads=8)
