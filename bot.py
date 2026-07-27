import telebot
from telebot import types
import sqlite3
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ----------------- خادم ويب مدمج لحل مشكلة Render -----------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# تشغيل الخادم في الخلفية لإبقاء Render مستقراً ومستمراً بالعمل
threading.Thread(target=run_web_server, daemon=True).start()

# ----------------- إعدادات البوت والبيانات العامة -----------------
BOT_TOKEN = "8024354421:AAHozoXzgVkYS2njISHMA9XEuCoyMmmTLg"
GROUP_ID = -1002083996004
ADMIN_ID = 6503251012

bot = telebot.TeleBot(BOT_TOKEN)

# قاموس مؤقت لتخزين خطوات المستخدمين الحالية (State Management)
user_states = {}

# ----------------- قاعدة البيانات SQL -----------------
def init_db():
    conn = sqlite3.connect("texas_bank.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# دالة مساعدة للتعامل مع قاعدة البيانات
def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect("texas_bank.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetchone: res = cursor.fetchone()
    if fetchall: res = cursor.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# ----------------- القوائم والأزرار (Keyboards) -----------------
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_texas = types.InlineKeyboardButton("🏦 حساب Texas", callback_data="menu_texas")
    btn_info = types.InlineKeyboardButton("ℹ️ معلومات", callback_data="main_info")
    btn_support = types.InlineKeyboardButton("📞 الدعم", callback_data="main_support")
    markup.add(btn_texas)
    markup.row(btn_info)
    markup.row(btn_support)
    return markup

def get_texas_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_account = types.InlineKeyboardButton("👤 حسابي", callback_data="texas_account")
    btn_deposit = types.InlineKeyboardButton("💰 شحن الحساب", callback_data="texas_deposit")
    btn_withdraw = types.InlineKeyboardButton("💳 سحب رصيد", callback_data="texas_withdraw")
    btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
    markup.add(btn_account)
    markup.row(btn_deposit, btn_withdraw)
    markup.row(btn_back)
    return markup

# ----------------- التعامل مع الأوامر -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        f"مرحباً بك {message.from_user.first_name} في بوت بنك تكساس!\n\n"
        "هنا يمكنك إدارة حسابك البنكي وسحب وإيداع الأموال بكل سهولة والأمان.\n"
        "اختر من القائمة في الأسفل وسوف نكون في الخدمة."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

# ----------------- استقبال النصوص والردود (Messages Handler) -----------------
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def handle_all_messages(message):
    user_id = message.from_user.id
    
    rep = message.reply_to_message
    if rep and "طلب سحب من" in rep.text:
        try:
            target_id = int(rep.text.split("المعرف: ")[1].split("\n")[0].strip())
            if message.text:
                bot.send_message(target_id, f"**رد من الدعم الفني** 📩:\n\n{message.text}", parse_mode="Markdown")
                bot.reply_to(message, "✅ تم إرسال ردك إلى اللاعب بنجاح.")
        except Exception as e:
            bot.reply_to(message, f"❌ حدث خطأ أثناء توجيه الرد: {e}")
        return

    if user_id not in user_states:
        return

    state = user_states[user_id].get("state")

    # خطوات إنشاء الحساب
    if state == "create_step1":
        user_states[user_id]["reg_username"] = message.text
        user_states[user_id]["state"] = "create_step2"
        bot.send_message(message.chat.id, "🔐 يرجى إدخال كلمة المرور المطلوبة:")

    elif state == "create_step2":
        username = user_states[user_id]["reg_username"]
        password = message.text
        user_states.pop(user_id)

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ موافقة", callback_data=f"adm_acc_approve_{user_id}"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"adm_acc_reject_{user_id}")
        )
        admin_msg = (
            f"**🆕 طلب إنشاء حساب جديد**\n\n"
            f"👤 المستخدم: <{user_id}>\n"
            f"📝 اسم المستخدم: {username}\n"
            f"🔑 كلمة المرور: {password}"
        )
        bot.send_message(GROUP_ID, admin_msg, reply_markup=markup)

        db_query("INSERT OR REPLACE INTO accounts (user_id, username, password, balance, status) VALUES (?, ?, ?, 0.0, 'pending')", (user_id, username, password), commit=True)
        bot.send_message(message.chat.id, "...تم إرسال طلب إنشاء الحساب للإدارة، يرجى الانتظار⏳")

    # خطوات شحن الحساب
    elif state == "dep_step_amount":
        try:
            amount = float(message.text)
            if amount < 100000:
                bot.send_message(message.chat.id, "❌ عذراً، يجب إدخال مبلغ صحيح لا يقل عن 100,000.")
                return
            user_states[user_id]["amount"] = amount
            user_states[user_id]["state"] = "dep_step_method"

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📱 Syriatel Cash", callback_data="pay_syriatel"),
                types.InlineKeyboardButton("💬 Sham Cash", callback_data="pay_sham")
            )
            bot.send_message(message.chat.id, "قم باختيار أحد وسائل الشحن التالية للحصول على رقم تحويل ⬇️", reply_markup=markup)
        except ValueError:
            bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح بالأرقام فقط.")

    elif state == "dep_step_proof":
        amount = user_states[user_id]["amount"]
        method = user_states[user_id]["method"]
        acc_info = db_query("SELECT username, password FROM accounts WHERE user_id=?", (user_id,), fetchone=True)

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ موافقة وتعبئة", callback_data=f"adm_dep_approve_{user_id}"),
            types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"adm_dep_reject_{user_id}")
        )

        bonus_amount = amount * 1.05
        admin_msg = (
            f"**💰 طلب شحن حساب جديد**\n\n"
            f"👤 المستخدم: <{user_id}>\n"
            f"📝 اسم المستخدم: {acc_info[0] if acc_info else 'لا يوجد'}\n"
            f"🔑 كلمة المرور: {acc_info[1] if acc_info else 'لا يوجد'}\n"
            f"💵 المبلغ الأساسي: {amount}\n"
            f"🎁 المبلغ مع البونص (5%): {bonus_amount}\n"
            f"💳 وسيلة الشحن: {method}"
        )

        if message.content_type == 'photo':
            photo_id = message.photo[-1].file_id
            admin_msg += "\n\n📸 إثبات الدفع المرفق بالأسفل:"
            bot.send_photo(GROUP_ID, photo_id, caption=admin_msg, reply_markup=markup)
        else:
            admin_msg += f"\n\n📝 رقم العملية/الإثبات: {message.text}"
            bot.send_message(GROUP_ID, admin_msg, reply_markup=markup)

        user_states.pop(user_id)
        bot.send_message(message.chat.id, "⏳...تم إرسال إثبات الشحن إلى الإدارة وجاري معالجة كود التأكيد المالي")

    # خطوات سحب الرصيد
    elif state == "with_step_amount":
        try:
            amount = float(message.text)
            current_bal = db_query("SELECT balance FROM accounts WHERE user_id=?", (user_id,), fetchone=True)[0]
            if amount > current_bal or amount <= 0:
                bot.send_message(message.chat.id, f"❌ الرصيد غير كافٍ أو المبلغ غير صحيح. رصيدك الحالي: {current_bal}")
                return
            user_states[user_id]["amount"] = amount
            user_states[user_id]["state"] = "with_step_code"
            bot.send_message(message.chat.id, "📲 يرجى إرسال الكود أو رقم المحفظة المراد إرسال الأموال إليها:")
        except ValueError:
            bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح بالأرقام فقط.")

# ----------------- أمر تشغيل البوت النهائي المستمر -----------------
if __name__ == "__main__":
    print("Bot is starting...")
    bot.infinity_polling()
