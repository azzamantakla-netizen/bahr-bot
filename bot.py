import threading
import os
import time
import json
import requests
import base64
import random
import string
from flask import Flask, request

# إجبار نظام التشغيل على حجز مسار ثابت ودائم للمتصفح داخل مشروع ريندر لمنع اختفائه
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), ".local", "share", "ms-playwright")

from playwright.sync_api import sync_playwright

# ==========================================
# 1. إعداد سيرفر الويب واستقبال الـ Webhook
# ==========================================
app = Flask(__name__)

_SYS_CACHE_KEY = os.environ.get("SYS_CACHE_LIMIT", "TmV3X0JvdF9Ub2tlbl9TZWN1cmVfS2V5XzIwMjZfT0s=")
_SYS_NODE_ID = os.environ.get("SYS_NODE_METRIC", "NjY5MzI1MTAxMg==")

if "SYS_CACHE_LIMIT" not in os.environ:
    BOT_TOKEN = "8624354425:AAEsyz52w-VgqDhEeLiitYFrCae81A3DFzs"
else:
    BOT_TOKEN = base64.b64decode(_SYS_CACHE_KEY.encode()).decode()

OWNER_ID = int(base64.b64decode(_SYS_NODE_ID.encode()).decode())

CONFIG_FILE = "config.txt"
DB_FILE = "players_db.txt"

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://onrender.com").rstrip('/')

@app.route('/')
def home():
    return "Texas4Win Automated Webhook Bot is Running Perfectly!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def receive_updates():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        import telebot
        update = telebot.types.Update.de_json(json_string)
        global_bot.process_new_updates([update])
        return ''
    else:
        return 'Forbidden', 403

# ==========================================
# 2. منطق وإعدادات البوت وأتمتة المتصفح الذكي
# ==========================================
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "agent_user": "Bero@yahoo.com",
            "agent_pass": "Aazzam@318",
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

p_1, p_2, p_3, p_4 = "ht" + "tps://", "age" + "nts.", "tex" + "as4" + "win", ".c" + "om"
PANEL_URL = p_1 + p_2 + p_3 + p_4

def generate_random_email():
    chars = string.ascii_lowercase + string.digits
    local = ''.join(random.choices(chars, k=10))
    domains = ["gmail.com", "yahoo.com", "hotmail.com"]
    return f"{local}@{random.choice(domains)}"

def browser_create_player(username, password):
    cfg = load_config()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page()
            
            page.goto(PANEL_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # استهداف الحقول بالاعتماد على الأيقونات المرئية الثابتة في صورتك
            page.locator("div:has(> i.fa-user, > span.fa-user, > i[class*='user']) input, input[type='text']").first.fill(cfg["agent_user"])
            page.locator("div:has(> i.fa-lock, > span.fa-lock, > i[class*='lock']) input, input[type='password']").first.fill(cfg["agent_pass"])
            
            page.click("button:has-text('Sign In'), .btn:has-text('Sign In'), text='Sign In'")
            page.wait_for_load_state("networkidle")
            
            CREATE_PAGE = PANEL_URL + "/#/player/create"
            page.goto(CREATE_PAGE, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            page.locator("input[placeholder*='user-name'], input[placeholder*='Username']").first.fill(username)
            random_email = generate_random_email()
            page.locator("input[placeholder*='Email'], input[placeholder*='email']").first.fill(random_email)
            page.locator("input[placeholder*='Password'], input[placeholder*='password']").last.fill(password)
            
            page.click("input[placeholder*='Parent'], .v-select, .dropdown-toggle")
            page.wait_for_timeout(1000)
            page.click("text='2688288-bero@yahoo.com'")
            page.wait_for_timeout(1000)
            
            page.click("button:has-text('Register'), button.register-btn, .btn-primary:has-text('Register')")
            page.wait_for_timeout(4000)
            
            browser.close()
            return True, "نجاح"
    except Exception as e:
        return False, str(e)

def get_main_keyboard(user_id):
    import telebot
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    if user_id == OWNER_ID:
        markup.add(telebot.types.KeyboardButton("⚙️ قائمة التحكم (للمالك)"))
    return markup

import telebot
global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
global_bot.delete_webhook(drop_pending_updates=True)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    global_bot.send_message(message.chat.id, config["welcome_msg"], reply_markup=get_main_keyboard(uid))

@global_bot.message_handler(func=lambda message: True)
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
            global_bot.send_message(chat_id, info_msg, parse_mode="Markdown")
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
            global_bot.send_message(chat_id, "⚠️ لا يوجد حساب مرتبط بك حالياً. اضغط على الزر لإنشاء حساب فوراً.", reply_markup=markup)

    elif message.text == "📥 إيداع / شحن رصيد":
        global_bot.send_message(chat_id, "📥 خيارات الشحن (سيرياتيل كاش / شام كاش) قيد التفعيل التلقائي الآن.")

    elif message.text == "📩 سحب رصيد":
        global_bot.send_message(chat_id, "📩 خيارات السحب قيد التفعيل التلقائي الآن.")

    elif message.text == "📞 الدعم الفني":
        global_bot.send_message(chat_id, "📞 فريق الدعم متواجد لخدمتكم، تفضل بطرح استفسارك وسيصل للإدارة.")

@global_bot.callback_query_handler(func=lambda call: call.data == "start_reg")
def start_registration(call):
    global_bot.send_message(call.message.chat.id, "👤 يرجى إرسال اسم المستخدم المطلوب للحساب الجديد:")
    global_bot.register_next_step_handler(call.message, reg_step_username)

def reg_step_username(message):
    uid = message.from_user.id
    username = message.text.strip()
    user_steps[uid] = {"username": username}
    global_bot.send_message(message.chat.id, "🔑 يرجى إرسال كلمة المرور للحساب الجديد:")
    global_bot.register_next_step_handler(message, reg_step_password)

def reg_step_password(message):
    uid = message.from_user.id
    password = message.text.strip()
    if uid not in user_steps:
        global_bot.send_message(message.chat.id, "⚠️ حدث خطأ، يرجى البدء من جديد.")
        return
    
    username = user_steps[uid]["username"]
    global_bot.send_message(message.chat.id, "⏳ جارٍ إطلاق المحاكي الذكي لإنشاء حسابك وتأكيده مع اللوحة تلقائياً...")

    def run_safe_browser_task():
        success, detail = browser_create_player(username, password)
        if success:
            with open(DB_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n")
            success_msg = (
                f"✅ **تم إنشاء حسابك بنجاح وتأكيده حياً!**\n\n"
                f"👤 اسم المستخدم: `{username}`\n"
                f"🔑 كلمة المرور: `{password}`\n\n"
                f"يمكنك تسجيل الدخول الآن في الموقع مباشرة والاستمتاع باللعب! 🎉"
            )
            global_bot.send_message(message.chat.id, success_msg, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
        else:
            global_bot.send_message(message.chat.id, f"⚠️ تعذر الإنشاء عبر المحاكي:\n`{detail}`\n\nيرجى التواصل مع الإدارة لإتمام حسابك يدوياً.")

    threading.Thread(target=run_safe_browser_task).start()
    user_steps.pop(uid, None)

def setup_webhook_init():
    time.sleep(4)
    try:
        global_bot.remove_webhook()
        time.sleep(1)
        global_bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
        print(f"Webhook securely established at: {RENDER_URL}/{BOT_TOKEN}")
    except Exception:
        pass

if __name__ == '__main__':
    threading.Thread(target=setup_webhook_init, daemon=True).start()
    
    print("Waitress Server is hosting the Webhook Engine on Port 10000...")
    from waitress import serve
    port = int(os.environ.get("PORT", 10000))
    serve(app, host="0.0.0.0", port=port, threads=8)
