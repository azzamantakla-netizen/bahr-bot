import telebot
from telebot import types
import sqlite3

# إعداد البيانات الثابتة والتوكن المستلم من المستخدم
BOT_TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"
GROUP_ID = -1003983996094  # آيدي مجموعة التدقيق
ADMIN_ID = 6693251012     # آيدي التلجرام الخاص بك

bot = telebot.TeleBot(BOT_TOKEN)

# ----------------- إعداد قاعدة البيانات (SQL) -----------------
def init_db():
    conn = sqlite3.connect("texas_wallet.db")
    cursor = conn.cursor()
    # جدول الحسابات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            balance REAL DEFAULT 0.0,
            approved INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# قاموس مؤقت لحفظ حالات المستخدمين أثناء كتابة البيانات (رصيد، حسابات، دعم)
user_states = {}

# ----------------- دالة المساعدة لقاعدة البيانات -----------------
def get_user(user_id):
    conn = sqlite3.connect("texas_wallet.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# ----------------- القوائم والأزرار (Keyboards) -----------------
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_texas = types.InlineKeyboardButton("🎮 حساب Texas", callback_data="menu_texas")
    btn_info = types.InlineKeyboardButton("👤 معلوماتي", callback_data="main_info")
    btn_support = types.InlineKeyboardButton("🆘 الدعم", callback_data="main_support")
    markup.add(btn_texas)
    markup.add(btn_info)
    markup.add(btn_support)
    return markup

def texas_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_acc = types.InlineKeyboardButton("👤 حسابي", callback_data="texas_account")
    btn_dep = types.InlineKeyboardButton("💰 شحن الحساب", callback_data="texas_deposit")
    btn_wit = types.InlineKeyboardButton("💳 سحب رصيد من الحساب", callback_data="texas_withdraw")
    btn_back = types.InlineKeyboardButton("↩️ رجوع", callback_data="back_to_main")
    markup.add(btn_acc)
    markup.add(btn_dep, btn_wit)
    markup.add(btn_back)
    return markup

# ----------------- أمر البداية /start -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "أهلاً بك ضمن عائلتنا 🎮\n"
        "هذا البوت صُمم خصيصاً لك، رصيدك بأمان معنا. "
        "تمتع بمرونة عالية في السحب وسرعة قصوى في الإيداع!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# ----------------- معالجة الضغط على الأزرار (Callback Queries) -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    if call.data == "back_to_main":
        bot.edit_message_text("أهلاً بك ضمن عائلتنا 🎮\nنحن في خدمتك دائماً.", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
        
    elif call.data == "menu_texas":
        bot.edit_message_text("مرحباً بك! 👋\nكيف يمكنني مساعدتك اليوم؟", call.message.chat.id, call.message.message_id, reply_markup=texas_menu())
        
    elif call.data == "main_info":
        user = get_user(user_id)
        if user and user[4] == 1: # إذا كان مسجلاً ومقبولاً
            info_text = f"📋 | معلومات حسابك |\n\n🆔 المعرف: `{user[0]}`\n👤 اسم المستخدم: {user[1]}\n🔑 كلمة المرور: {user[2]}\n💰 الرصيد: {user[3]:,} ل.س"
        else:
            info_text = "❌ أنت غير مسجل في خدمة Texas حتى الآن، يرجى الانتقال إلى (حساب Texas) ثم الضغط على (حسابي) للبدء."
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("↩️ رجوع", callback_data="back_to_main"))
        bot.edit_message_text(info_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "main_support":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "لا تقلق، فريقنا في خدمتكم على مدار الساعة. فقط أخبرنا بنوع المشكلة:")
        user_states[user_id] = {'action': 'writing_support'}

    elif call.data == "texas_account":
        user = get_user(user_id)
        if user and user[4] == 1: # مسجل ومفعل
            info_text = f"📋 | معلومات حسابك |\n\n🆔 المعرف: `{user[0]}`\n👤 اسم المستخدم: {user[1]}\n🔑 كلمة المرور: {user[2]}\n💰 الرصيد: {user[3]:,} ل.س"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("↩️ رجوع", callback_data="menu_texas"))
            bot.edit_message_text(info_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        elif user and user[4] == 0: # قيد الانتظار
            bot.answer_callback_query(call.id, "⚠️ حسابك قيد التدقيق والمراجعة حالياً من قبل الإدارة.", show_alert=True)
        else: # غير مسجل
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "أنت غير مسجل لدينا، يرجى إدخال اسم المستخدم المطلوب للحساب:")
            user_states[user_id] = {'action': 'register_username'}

    elif call.data == "texas_deposit":
        user = get_user(user_id)
        if not user or user[4] == 0:
            bot.answer_callback_query(call.id, "❌ يجب عليك إنشاء حساب وتفعيله أولاً من زر 'حسابي' قبل الشحن.", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "⚠️ تنبيه: أقل عملية شحن هي مبلغ 100 ألف", show_alert=True)
        bot.send_message(call.message.chat.id, "💰 شحن الحساب\n\n✍️ يرجى إرسال مبلغ الشحن:")
        user_states[user_id] = {'action': 'deposit_amount'}

    elif call.data.startswith("pay_"):
        # اختيار طريقة الشحن
        method = call.data.split("_")[1]
        amount = user_states[user_id]['amount']
        user_states[user_id]['method'] = method
        
        if method == "syriatel":
            bot.edit_message_text(f"🎉 تهانينا! ستحصل على بونص إضافي بقيمة 5% عند الشحن عبر Syriatel Cash.\n\n✍️ يرجى تحويل مبلغ {amount:,} إلى الكود التالي: `48122120`\n\nبعد التحويل، يرجى كتابة رقم العملية أو إرسال صورة إشعار التحويل هنا لتأكيد الطلب:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            user_states[user_id]['action'] = 'deposit_proof'
        elif method == "sham":
            bot.edit_message_text(f"🎉 تهانينا! ستحصل على بونص إضافي بقيمة 5% عند الشحن عبر Sham Cash.\n\n✍️ يرجى تحويل مبلغ {amount:,} إلى عنوان المحفظة التالي:\n`a18758d5324eb7595d4463ca355ad221`\n\nبعد التحويل، يرجى كتابة رقم العملية أو إرسال صورة إشعار التحويل هنا لتأكيد الطلب:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            user_states[user_id]['action'] = 'deposit_proof'

    elif call.data == "confirm_dep_player":
        # اللاعب أكد الفاتورة، هنا نفحص شرط الرصيد بالبوت
        user = get_user(user_id)
        if user[3] <= 0: # الرصيد في البوت الوهمي صفر
            bot.edit_message_text("❌ فشلت العملية، لا يمكنك تقديم طلب شحن ورصيدك الحالي في البوت هو صفر.", call.message.chat.id, call.message.message_id)
            user_states.pop(user_id, None)
        else:
            # لديه رصيد، يرسل الطلب للمجموعة
            data = user_states[user_id]
            bonus_amount = data['amount'] * 1.05
            method_name = "Syriatel Cash" if data['method'] == "syriatel" else "Sham Cash"
            
            group_msg = (
                f"📥 **طلب شحن حساب جديد**\n\n"
                f"👤 اسم المستخدم: {user[1]}\n"
                f"🆔 معرف التلجرام: `{user_id}`\n"
                f"💰 المبلغ الأساسي: {data['amount']:,}\n"
                f"🎁 المبلغ مع البونص (5%): {bonus_amount:,}\n"
                f"📱 وسيلة الشحن: {method_name}\n"
                f"🧾 الإثبات المقدم: {data['proof_text']}"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ موافقة وتعبئة وهمية", callback_data=f"adm_dep_apv_{user_id}_{bonus_amount}"),
                types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"adm_dep_ref_{user_id}")
            )
            
            if 'proof_photo' in data:
                bot.send_photo(GROUP_ID, data['proof_photo'
