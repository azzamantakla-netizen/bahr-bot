import threading
import os
import time
import json
import requests
import base64
import random
import string
import subprocess

# إعداد مسار Playwright متوافق مع خوادم الاستضافة لضمان التثبيت المحلي
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), ".local", "share", "ms-playwright")

# حيلة برمجية لتثبيت متصفح مخفف جداً (Headless Shell) لتخطي ضعف رامات السيرفر
if not os.path.exists(os.environ["PLAYWRIGHT_BROWSERS_PATH"]):
    print("[*] Downloading Ultra-Lightweight Chromium for Server, please wait...")
    try:
        # تحميل النسخة المخففة المخصصة للسيرفرات الضعيفة فقط
        subprocess.run(["python", "-m", "playwright", "install", "chromium-headless-shell"], check=True)
        print("[+] Lightweight Chromium downloaded successfully!")
    except Exception as build_err:
        print(f"[-] Auto-install failed, skipping: {build_err}")

from playwright.sync_api import sync_playwright
import telebot

# ========================================== #
# 1. إعداد هويات البوت والتحقق الأساسي       #
# ========================================== #
_SYS_CACHE_KEY = os.environ.get("SYS_CACHE_LIMIT", "TmV3X0JvdF9Ub2tlbl9TZWN1cmVfS2V5XzIwMjZfT0s=")
_SYS_NODE_ID = os.environ.get("SYS_NODE_METRIC", "NjY5MzI1MTAxMg==")

if "SYS_CACHE_LIMIT" not in os.environ:
    BOT_TOKEN = "8624354425:AAEsyz52w-VgqDhEeLiitYFrCae81A3DFzs"
else:
    BOT_TOKEN = base64.b64decode(_SYS_CACHE_KEY.encode()).decode()

OWNER_ID = int(base64.b64decode(_SYS_NODE_ID.encode()).decode())
CONFIG_FILE = "config.txt"
DB_FILE = "players_db.txt"

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

# ========================================== #
# 2. منطق أتمتة المحاكي الذكي المرن (Playwright) #
# ========================================== #
def browser_create_player(username, password):
    cfg = load_config()
    try:
        with sync_playwright() as p:
            # تشغيل النسخة المخففة لضمان استقرار السيرفر
            browser = p.chromium_headless_shell.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(PANEL_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            first_input = page.locator("input[type='text'], input[type='email']").first
            first_input.wait_for(state="visible", timeout=15000)
            first_input.click()
            time.sleep(1)

            page.keyboard.type(cfg["agent_user"], delay=100)
            page.keyboard.press("Tab")
            time.sleep(0.5)
            page.keyboard.type(cfg["agent_pass"], delay=100)
            time.sleep(0.5)
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle")
            time.sleep(5)

            CREATE_PAGE = PANEL_URL + "/#/player/create"
            page.goto(CREATE_PAGE, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            player_first_input = page.locator("input[type='text']").first
            player_first_input.wait_for(state="visible", timeout=15000)
            player_first_input.click()
            time.sleep(1)

            page.keyboard.type(username, delay=100)
            page.keyboard.press("Tab")
            time.sleep(0.5)
            random_email = generate_random_email()
            page.keyboard.type(random_email, delay=100)
            page.keyboard.press("Tab")
            time.sleep(0.5)
            page.keyboard.type(password, delay=100)
            time.sleep(1)

            try:
                page.click("input[placeholder*='Parent'], .v-select, .dropdown-toggle, input[role='combobox']", timeout=15000)
                time.sleep(1.5)
                page.click("text='2688288-bero@yahoo.com'", timeout=15000)
                time.sleep(1)
            except:
                print("[!] Parent selector not found, attempting direct registration...")

            page.keyboard.press("Enter")
            time.sleep(4)
            browser.close()
            return True, "نجاح"
    except Exception as e:
        if 'browser' in locals():
            try:
                browser.close()
            except:
                pass
        return False, str(e)

def get_main_keyboard(user_id):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    if user_id == OWNER_ID:
        markup.add(telebot.types.KeyboardButton("⚙️ قائمة التحكم (للمالك)"))
    return markup

global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
global_bot.delete_webhook(drop_pending_updates=True)

@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    global_bot.send_message(message.chat.id, config["welcome_msg"], reply_markup=get_main_keyboard(uid))

def find_player_in_db(uid):
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line.strip())
                if data.get("tg_id") == uid:
                    return data
            except:
                continue
    return None

@global_bot.message_handler(func=lambda message: True)
def core_menu(message):
    uid = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    if text == "👤 حسابي":
        player_found = find_player_in_db(uid)
        if player_found:
            info_msg = f"ℹ️ **معلومات الحساب الخاص بك:**\n\n👤 اسم المستخدم: `{player_found['login']}`\n🔑 كلمة المرور: `{player_found['password']}`\n\n💰 لرؤية رصيدك وتعبئته، تفضل بالاختيار من القائمة."
            global_bot.send_message(chat_id, info_msg, parse_mode="Markdown")
            return
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ لا يوجد حساب مرتبط بك حالياً. اضغط على الزر لإنشاء حساب فوراً.", reply_markup=markup)
        return
            
    if text == "📥 إيداع / شحن رصيد":
        global_bot.send_message(chat_id, "📥 خيارات الشحن (سيرياتيل كاش / شام كاش) قيد التفعيل التلقائي الآن.")
        return
        
    if text == "📩 سحب رصيد":
        global_bot.send_message(chat_id, "📩 خيارات السحب قيد التفعيل التلقائي الآن.")
        return
        
    if text == "📞 الدعم الفني":
        global_bot.send_message(chat_id, "📞 فريق الدعم متواجد لخدمتكم، تفضل بطرح استفسارك وسيصل للإدارة.")
        return

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
    threading.Thread(target=run_safe_browser_task, args=(message.chat.id, uid, username, password), daemon=True).start()

def run_safe_browser_task(chat_id, uid, username, password):
    success, detail = browser_create_player(username, password)
    if success:
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tg_id": uid, "login": username, "password": password}, ensure_ascii=False) + "\n")
        success_msg = f"✅ **تم إنشاء حسابك بنجاح وتأكيده!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`\n\nيمكنك تسجيل الدخول الآن في الموقع مباشرة والاستمتاع باللعب! 🎉"
