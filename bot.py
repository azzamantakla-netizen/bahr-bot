import telebot
from telebot import types
import sqlite3
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ----------------- 1. خادم ويب مدمج لحل مشكلة منصة Render -----------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Texas Bank Bot is running perfectly on Render!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# تشغيل خادم الويب في الخلفية بشكل منفصل لمنع خروج المنصة
threading.Thread(target=run_web_server, daemon=True).start()

# ----------------- 2. إعدادات البوت والبيانات العامة المعتمدة -----------------
BOT_TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"
GROUP_ID = -1003983996094
ADMIN_ID = 6693251012

bot = telebot.TeleBot(BOT_TOKEN)

# قاموس مؤقت لتخزين خطوات المستخدمين الحالية (State Management)
user_states = {}

# ----------------- 3. قاعدة البيانات SQL -----------------
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

# ----------------- 4. القوائم والأزرار (Keyboards) -----------------
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_texas = types.InlineKeyboardButton("🐂 حساب Texas", callback_data="menu_texas")
    btn_info = types.InlineKeyboardButton("ℹ️ معلومات", callback_data="main_info")
    btn_support = types.InlineKeyboardButton("📞 الدعم", callback_data="main_support")
    markup.add(btn_texas, btn_info, btn_support)
    return markup

def get_texas_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_create = types.InlineKeyboardButton("✨ إنشاء حساب Texas", callback_data="texas_create")
    btn_deposit = types.InlineKeyboardButton("💰 شحن الحساب", callback_data="texas_deposit")
    btn_withdraw = types.InlineKeyboardButton("💳 سحب رصيد", callback_data="texas_withdraw")
    btn_back = types.InlineKeyboardButton("↩️ رجوع", callback_data="back_to_main")
    markup.add(btn_create, btn_deposit, btn_withdraw, btn_back)
    return markup

def get_confirm_keyboard(callback_ok, callback_cancel):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_ok = types.InlineKeyboardButton("موافق", callback_data=callback_ok)
    btn_cancel = types.InlineKeyboardButton("رجوع", callback_data=callback_cancel)
    markup.add(btn_ok, btn_cancel)
    return markup

# ----------------- 5. الأوامر والرسالة الترحيبية -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "مرحبا بك ضمن عائلتنا صمم هذا البوت ليلبي جميع احتياجتك "
        "تمتع معنا بسرعة قصوى في السحب ومرونة عالية في الايداع"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

# ----------------- 6. معالجة ضغطات الأزرار (Callback Query) -----------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    # --- قائمة حساب تكساس الفرعية واختيار اللون الافتراضي مع شعار الثور ---
    if call.data == "menu_texas":
        bot.edit_message_text("مرحباً بك! 👋\n🔷 كيف يمكنني مساعدتك اليوم؟", chat_id, msg_id, reply_markup=get_texas_keyboard())
    
    elif call.data == "back_to_main":
        welcome_text = "مرحبا بك ضمن عائلتنا صمم هذا البوت ليلبي جميع احتياجتك تمتع معنا بسرعة قصوى في السحب ومرونة عالية في الايداع"
        bot.edit_message_text(welcome_text, chat_id, msg_id, reply_markup=get_main_keyboard())

    # --- سيناريو زر معلومات المتكامل ---
    elif call.data == "main_info":
        bot.send_message(chat_id, "⏳ جاري معالجة طلبك، يرجى الانتظار...")
        bot.send_message(GROUP_ID, f"⚠️ اللاعب `{user_id}` يطلب معلومات حسابه.\nيرجى الرد على هذه الرسالة (Reply) وكتابة المعلومات بالترتيب (اسم المستخدم، كلمة المرور، الرصيد) ليرسلها البوت منسقة.")

    # --- سيناريو زر الدعم المتكامل ---
    elif call.data == "main_support":
        user_states[user_id] = {"state": "waiting_support_text"}
        bot.send_message(chat_id, "فريقنا في خدمتك على مدار الساعة فقط ارسل مشكلتك لنقوم بحلها", reply_markup=get_confirm_keyboard("confirm_support", "back_to_main"))

    elif call.data == "confirm_support":
        if user_id in user_states and "support_msg" in user_states[user_id]:
            support_text = user_states[user_id]["support_msg"]
            bot.send_message(chat_id, "⏳ جاري معالجة طلبك، يرجى الانتظار...")
            
            # إرسال للمشرفين مع أيدي اللاعب
            bot.send_message(GROUP_ID, f"📩 **رسالة دعم جديدة من اللاعب:** `{user_id}`\n\n📝 المشكلة:\n{support_text}\n\n* للرد على اللاعب، قم بعمل (Reply) على هذه الرسالة مباشرة واكتب ردك.")
            user_states.pop(user_id, None)
        else:
            bot.send_message(chat_id, "❌ لم تقم بكتابة أي رسالة دعم، يرجى المحاولة مجدداً.")

    # --- سيناريو إنشاء حساب تكساس المفصل ---
    elif call.data == "texas_create":
        user_states[user_id] = {"state": "create_username"}
        bot.send_message(chat_id, "يرجى كتابة اسم المستخدم الذي تريده:")

    elif call.data == "confirm_create":
        if user_id in user_states and "reg_username" in user_states[user_id] and "reg_password" in user_states[user_id]:
            username = user_states[user_id]["reg_username"]
            password = user_states[user_id]["reg_password"]
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ قبول", callback_data=f"adm_acc_approve_{user_id}"),
                types.InlineKeyboardButton("❌ رفض", callback_data=f"adm_acc_reject_{user_id}")
            )
            admin_msg = f"🆕 **طلب إنشاء حساب جديد**\n\n👤 معرف اللاعب: `{user_id}`\n📝 الاسم المقترح: {username}\n🔑 كلمة السر: {password}"
            bot.send_message(GROUP_ID, admin_msg, reply_markup=markup)
            
            db_query("INSERT OR REPLACE INTO accounts (user_id, username, password, balance, status) VALUES (?, ?, ?, 0.0, 'pending')", (user_id, username, password), commit=True)
            bot.send_message(chat_id, "⏳ جاري معالجة طلبك، يرجى الانتظار...")
            user_states.pop(user_id, None)

    elif call.data.startswith("adm_acc_approve_"):
        target_id = int(call.data.split("_")[-1])
        db_query("UPDATE accounts SET status='approved' WHERE user_id=?", (target_id,), commit=True)
        bot.edit_message_text(f"✅ تم قبول حساب اللاعب {target_id}", chat_id, msg_id)
        bot.send_message(target_id, "🎉 تم إنشاء حسابك بنجاح! يمكنك الآن استخدام حسابك.")

    elif call.data.startswith("adm_acc_reject_"):
        target_id = int(call.data.split("_")[-1])
        bot.edit_message_text(f"❌ تم رفض حساب اللاعب {target_id}", chat_id, msg_id)
        bot.send_message(target_id, "❌ عذراً، اسم المستخدم أو كلمة السر مستخدمة بالفعل. يرجى تغييرها وإعادة المحاولة.")
        # إعادة المحاولة التلقائية للاعب فوراً
        user_states[target_id] = {"state": "create_username"}
        bot.send_message(target_id, "يرجى كتابة اسم المستخدم الجديد الذي تريده:")

    # --- سيناريو شحن الحساب وإضافة البونص 5% ---
    elif call.data == "texas_deposit":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📱 Syriatel Cash", callback_data="dep_syriatel"),
            types.InlineKeyboardButton("💬 Sham Cash SYP", callback_data="dep_sham_syp"),
            types.InlineKeyboardButton("💵 Sham Cash Dollar", callback_data="dep_sham_usd"),
            types.InlineKeyboardButton("↩️ رجوع", callback_data="menu_texas")
        )
        bot.edit_message_text("💰 اختر طريقة الدفع المناسبة لشحن حسابك:", chat_id, msg_id, reply_markup=markup)

    elif call.data in ["dep_syriatel", "dep_sham_syp", "dep_sham_usd"]:
        method = "Syriatel Cash" if call.data == "dep_syriatel" else ("Sham Cash SYP" if call.data == "dep_sham_syp" else "Sham Cash Dollar")
        user_states[user_id] = {"state": "dep_amount", "method": method}
        bot.send_message(chat_id, "🎁 تهانينا! ستحصل على بونص مجاني 5% إضافي على عملية التعبئة هذه.")
        bot.send_message(chat_id, "يرجى كتابة المبلغ المراد شحنه بالأرقام:")

    elif call.data == "confirm_dep_amount":
        method = user_states[user_id]["method"]
        if method == "Syriatel Cash":
            bot.send_message(chat_id, "يرجى إرسال الأموال الآن إلى الكود التالي: 48122120", reply_markup=get_confirm_keyboard("confirm_dep_sent", "texas_deposit"))
        else:
            bot.send_message(chat_id, "يرجى ارسال المبلغ الى عنوان المحفظة التالي a18758d5324eb7595d4463ca355ad221", reply_markup=get_confirm_keyboard("confirm_dep_sent", "texas_deposit"))

    elif call.data == "confirm_dep_sent":
        user_states[user_id]["state"] = "dep_proof"
        bot.send_message(chat_id, "يرجى إرسال صورة إيصال الدفع مع كتابة رقم العملية في نفس الرسالة:")

    elif call.data == "confirm_dep_final":
        if user_id in user_states and "proof_done" in user_states[user_id]:
            bot.send_message(chat_id, "⏳ جاري معالجة طلبك، يرجى الانتظار...")
            
            amount = user_states[user_id]["amount"]
 
