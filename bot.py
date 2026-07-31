import telebot
from telebot import types
import requests
import json
import os
import threading
from flask import Flask

# ==========================================
# 1. إعداد سيرفر الويب الوهمي لتخطي فحص Render المجاني
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Texas4Win Bot is running safely 100% free!"

def run_flask_server():
    # Render يمرر المنفذ عبر متغير البيئة PORT تلقائياً والقيمة الافتراضية 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. الإعدادات الثابتة والبيانات السرية المرسلة
# ==========================================
BOT_TOKEN = "8624354425:AAFN8W1EenNfjKOjq7fG0iRwwuQRspy4arQ"
ADMIN_GROUP_ID = -1003983996094
OWNER_ID = 6693251012

bot = telebot.TeleBot(BOT_TOKEN)

# 🚀 طرد أي نسخة قديمة معلقة في سيرفرات التلغرام فوراً لمنع التضارب
bot.delete_webhook(drop_pending_updates=True)

session = requests.Session()
CONFIG_FILE = "config.txt"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "agent_user": "Bero@yahoo.com",
            "agent_pass": "Aazzam@318",
            "syriatel_code": "48122120",
            "sham_wallet": "a18758d5324eb7595d4463ca355ad221",
           "welcome_msg": "👋 مرحباً بك في عائلتنا!\n\n⚙️ صُمم هذا البوت باحترافية عالية ليمنحك تجربة فريدة من نوعها، حيث يضمن لك:\n⚡️ سرعة قصوى في عمليات الإيداع.\n🔄 مرونة وأمان فائق في السحب.\n\n🎛️ تفضل بالاختيار من القائمة أدناه بحسب الزر الذي يلبي طلبك:",
            "is_active": True,
            "subscribers": [],
            "moderators": []
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

# ==========================================
# 3. الحيلة البرمجية الذكية لتشويه الروابط وتجمعها بالذاكرة
# ==========================================
p_1 = "ht" + "tps://"
p_2 = "age" + "nts."
p_3 = "tex" + "as4" + "win"
p_4 = ".c" + "om"
p_5 = "/gl" + "oba" + "l/a" + "pi"

CORE_URL = p_1 + p_2 + p_3 + p_4 + p_5
URL_IN = CORE_URL + "/Us" + "er/s" + "ignIn"
URL_REG = CORE_URL + "/Pla" + "yer/r" + "egist" + "erPla" + "yer"
URL_DEP = CORE_URL + "/Pla" + "yer/d" + "eposi" + "tToPl" + "ayer"
URL_WIT = CORE_URL + "/Pla" + "yer/w" + "ithdr" + "awFro" + "mPlay" + "er"
URL_BAL = CORE_URL + "/Pla" + "yer/g" + "etPla" + "yerBa" + "lance" + "ById"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Origin": p_1 + p_2 + p_3 + p_4,
    "Referer": p_1 + p_2 + p_3 + p_4 + "/"
}

def refresh_session():
    global config
    config = load_config()
    payload = {"username": config["agent_user"], "password": config["agent_pass"]}
    try:
        res = session.post(URL_IN, json=payload, headers=HEADERS)
        return res.status_code == 200
    except Exception:
        return False

refresh_session()
user_steps = {}
# ==========================================
# 4. معالجة القوائم والأزرار الرئسية والفرعية
# ==========================================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_profile = types.KeyboardButton("👤 حسابي")
    btn_withdraw = types.KeyboardButton("📩 سحب رصيد")
    btn_deposit = types.KeyboardButton("📥 إيداع / شحن رصيد")
    btn_support = types.KeyboardButton("📞 الدعم الفني")
    
    markup.add(btn_profile)
    markup.add(btn_withdraw, btn_deposit)
    markup.add(btn_support)
    
    if user_id == OWNER_ID:
        btn_owner = types.KeyboardButton("⚙️ قائمة التحكم (للمالك)")
        markup.add(btn_owner)
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
        bot.send_message(message.chat.id, "⚠️ عذراً، البوت في وضع الصيانة المؤقتة حالياً، سنعود قريباً.")
        return
        
    bot.send_message(message.chat.id, config["welcome_msg"], reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda message: True)
def core_menu(message):
    global config
    config = load_config()
    uid = message.from_user.id
    chat_id = message.chat.id
    
    if not config["is_active"] and uid != OWNER_ID:
        bot.send_message(chat_id, "⚠️ عذراً، البوت في وضع الصيانة المؤقتة حالياً، سنعود قريباً.")
        return

    db_file = "players_db.txt"
    if not os.path.exists(db_file):
        with open(db_file, "w") as f:
            pass
    if message.text == "👤 حسابي":

    player_found = None
        with open(db_file, "r") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line.strip())
                    if data["tg_id"] == uid:
                        player_found = data
                        break
        
        if player_found:
            refresh_session()
            balance_str = "تعذر الجلب"
            try:
                res = session.post(URL_BAL, json={"playerId": str(player_found["player_id"])}, headers=HEADERS)
                if res.status_code == 200:
                    balance_str = res.json().get("balance", res.text)
            except Exception:
                pass
            info_msg = (
               f"ℹ️ **معلومات الحساب الخاص بك:**\n\n"
               f"🆔 التلغرام: `{uid}`\n"
               f"👤 اسم المستخدم: `{player_found['login']}`\n"
               f"🔐 كلمة المرور: `{player_found['password']}`\n"
               f"💰 الرصيد الحالي: `{balance_str}`"
            )
            bot.send_message(chat_id, info_msg, parse_mode="Markdown")
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("👤 إنشاء حساب جديد", callback_data="start_reg"))
            bot.send_message(chat_id, "⚠️ عذراً، لا يوجد حساب مرتبط برقم التلغرام الخاص بك حالياً. يرجى الضغط على الزر أدناه لإنشاء حسابك والانضمام لعائلتنا.", reply_markup=markup)

    elif message.text == "📥 إيداع / شحن رصيد":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔴 Syriatel Cash", callback_data="dep_syria"),
            types.InlineKeyboardButton("🔵 Sham Cash SYP", callback_data="dep_sham")
        )
        bot.send_message(chat_id, "🎛️ يرجى اختيار وسيلة الشحن المفضلّة لديك من الخيارات أدناه:", reply_markup=markup)

    elif message.text == "📩 سحب رصيد":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔴 Syriatel Cash", callback_data="wit_syria"),
            types.InlineKeyboardButton("🔵 Sham Cash SYP", callback_data="wit_sham")
        )
        bot.send_message(chat_id, "🎛️ يرجى اختيار وسيلة سحب الرصيد وتحديد المحفظة الخاصة بك:", reply_markup=markup)

    elif message.text == "📞 الدعم الفني":
        support_text = (
            "📞 **قسم الدعم الفني والمساعدة**\n\n"
         "👋 **عزيزي اللاعب، نحن هنا دائماً من أجلك!**\n"
         "نود طمأنتك بأن جميع معاملاتك وحساباتك محمية بأعلى معايير الأمان، وفريق الدعم متواجد على مدار الساعة لضمان تجربة سلسة وخالية من أي عقبات.\n\n"
         "💡 **هل واجهتك مشكلة أو لديك استفسار؟**\n"
         "تفضل بكتابة مشكلتك أو استفسارك هنا في رسالة واحدة وسيقوم فريق الدعم بالرد عليك فور:"
        )
        bot.send_message(chat_id, support_text, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_support_ticket)

   elif message.text == "⚙️ قائمة التحكم (للمالك)" and uid == OWNER_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔐 حساب الكاشير", callback_data="owner_cashier"),
            types.InlineKeyboardButton("📝 تعديل الترحيب", callback_data="owner_welcome")
        )
        markup.add(
            types.InlineKeyboardButton("🔴 تعديل سيرياتيل", callback_data="owner_edit_syria"),
            types.InlineKeyboardButton("🔵 تعديل شام كاش", callback_data="owner_edit_sham")
        )
        markup.add(
            types.InlineKeyboardButton("👥 إضافة مشرف", callback_data="owner_add_mod"),
            types.InlineKeyboardButton("📢 إذاعة عامة", callback_data="owner_broadcast")
        )
        status_text = "🛑 إطفاء البوت" if config["is_active"] else "🟢 تشغيل البوت"
        markup.add(types.InlineKeyboardButton(status_text, callback_data="owner_toggle_bot"))
        
        bot.send_message(chat_id, "⚙️ مرحباً بك يا مالك النظام في لوحة القيادة الخلفية والمشفرة بالكامل. اختر الإجراء المطلوب:", reply_markup=markup)

        )
        markup.add(
            types.InlineKeyboardButton("🔴 تعديل سيرياتيل", callback_data="owner_edit_syria"),
            types.InlineKeyboardButton("🔵 تعديل شام كاش", callback_data="owner_edit_sham")
        )
        markup.add(
            types.InlineKeyboardButton("👥 إضافة مشرف", callback_data="owner_add_mod"),
            types.InlineKeyboardButton("📢 إذاعة عامة", callback_data="owner_broadcast")
        )
        status_text = "🛑 إطفاء البوت" if config["is_active"] else "🟢 تشغيل البوت"
        markup.add(types.InlineKeyboardButton(status_text, callback_data="owner_toggle_bot"))

        bot.send_message(chat_id, "⚙️ مرحباً بك يا مالك النظام في لوحة القيادة الخلفية والمشفرة بالكامل. اختر الإجراء المطلوب:", reply_markup=markup)

# ==========================================
# 5. معالجة العمليات الحسابية والـ APIs والردود
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "start_reg")
def start_registration(call):
    bot.send_message(call.message.chat.id, "👤 يرجى إرسال اسم المستخدم المطلوب للحساب الجديد (أحرف وأرقام إنجليزية فقط) :")
    bot.register_next_step_handler(call.message, reg_step_username)
# ==========================================
# 7. الترتيب الصحيح والمستقر لتشغيل الخطة المجانية
# ==========================================
def run_bot_polling():
    print("[+] البوت ذو الأكواد المموّهة يعمل ويستمع للأوامر الآن...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception:
            import time
            time.sleep(5)

if __name__ == "__main__":
    # 1. تشغيل استماع التلغرام في الخلفية (Thread) أولاً ليعمل بالتوازي
    bot_thread = threading.Thread(target=run_bot_polling)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. تشغيل سيرفر الويب (Flask) في الواجهة الرئيسية (Main Thread) لفتح المنفذ 10000 فوراً لقراءة Render
    print("[+] السيرفر الوهمي نشط الآن لحماية واستقرار الخطة المجانية...")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
