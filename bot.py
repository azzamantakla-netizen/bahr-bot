import telebot
from telebot import types
import sqlite3
import os
from flask import Flask, request

# ------- 1. إعدادات البوت والروابط -------
BOT_TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"
GROUP_ID = -1002083906004
ADMIN_ID = 6003251012

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

# ------- 2. إعداد خادم Flask والـ Webhook لمنصة Render -------
app = Flask(__name__)

@app.route('/', methods=['POST'])
def getMessage():
    json_string = request.stream.read().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def home():
    return "Texas Bank Bot Webhook Server is Stable and Active!", 200

@app.route('/health')
def health():
    return "OK", 200

# ------- 3. قاعدة البيانات SQL -------
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

# ------- 4. القوائم والأزرار (Keyboards) -------
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_texas = types.InlineKeyboardButton("🏦 Texas", callback_data="menu_texas")
    btn_info = types.InlineKeyboardButton("📝 معلومات", callback_data="main_info")
    btn_support = types.InlineKeyboardButton("📞 الدعم", callback_data="main_support")
    markup.add(btn_texas, btn_info, btn_support)
    return markup

def get_texas_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_create = types.InlineKeyboardButton("👤 إنشاء حساب Texas", callback_data="texas_create")
    btn_deposit = types.InlineKeyboardButton("💳 شحن الحساب", callback_data="texas_deposit")
    btn_withdraw = types.InlineKeyboardButton("💰 سحب الرصيد", callback_data="texas_withdraw")
    btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
    markup.add(btn_create, btn_deposit, btn_withdraw, btn_back)
    return markup

def get_confirm_keyboard(callback_ok, callback_cancel):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_ok = types.InlineKeyboardButton("✅ موافق", callback_data=callback_ok)
    btn_cancel = types.InlineKeyboardButton("❌ إلغاء", callback_data=callback_cancel)
    markup.add(btn_ok, btn_cancel)
    return markup

# ------- 5. الأوامر والرسائل الرئيسية -------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "مرحباً بك ضمن عائلتنا، مسجل هنا لنهتم بكل احتياجاتك\n"
        "تجمع منصتنا طموح الفرد ومرونة عالية في النجاح"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

# ------- 6. معالجة ضغطات الأزرار (CALLBACK QUERY) -------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    if call.data == "menu_texas":
        bot.edit_message_text("🤔 كيف يمكنني مساعدتك اليوم؟", chat_id, msg_id, reply_markup=get_texas_keyboard())

    elif call.data == "back_to_main":
        welcome_text = (
            "مرحباً بك ضمن عائلتنا، مسجل هنا لنهتم بكل احتياجاتك\n"
            "تجمع منصتنا طموح الفرد ومرونة عالية في النجاح"
        )
        bot.edit_message_text(welcome_text, chat_id, msg_id, reply_markup=get_main_keyboard())

    elif call.data == "main_info":
        bot.send_message(chat_id, "📝 جاري مراجعة طلبات شحن رصيد حسابك البرمجي، في حال توجيه البوت ميزة (Reply) يرجى معلومات حسابك السيادية ليتوفر الرد الفوري حل هذه الرسالة 📝")

    elif call.data == "main_support":
        user_states[user_id] = {"state": "waiting_support_text"}
        bot.send_message(chat_id, "📞 فريقنا في خدمتك على مدار الساعة، فقط ارسل مشكلتك ليقوم فريقنا بحلها", reply_markup=get_confirm_keyboard("confirm_support", "back_to_main"))

    elif call.data == "confirm_support":
        if user_id in user_states and "support_msg" in user_states[user_id]:
            support_text = user_states[user_id]["support_msg"]
            bot.send_message(chat_id, "⏳ جاري معالجة طلبك يرجى الانتظار...")
            bot.send_message(GROUP_ID, f"📥 نداء دعم جديد من ({user_id}):\n\n{support_text}")
            user_states.pop(user_id, None)
        else:
            bot.send_message(chat_id, "❌ لم تقم بكتابة أي رسالة دعم، يرجى المحاولة مجدداً.")

    elif call.data == "texas_create":
        user_states[user_id] = {"state": "create_username"}
        bot.send_message(chat_id, "👤 يرجى كتابة اسم المستخدم الذي تريد:")

    elif call.data == "confirm_create":
        if user_id in user_states and "reg_username" in user_states[user_id] and "reg_password" in user_states[user_id]:
            username = user_states[user_id]["reg_username"]
            password = user_states[user_id]["reg_password"]
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ قبول", callback_data=f"adm_acc_approve_{user_id}"),
                types.InlineKeyboardButton("❌ رفض", callback_data=f"adm_acc_reject_{user_id}")
            )
            admin_msg = f"🆕 طلب إنشاء حساب جديد من ({username}) المعرف الخاص به ({user_id}) معرف القاعدة 🗄️"
            bot.send_message(GROUP_ID, admin_msg, reply_markup=markup)
            
            db_query("INSERT OR REPLACE INTO accounts (user_id, username, password, balance, status) VALUES (?, ?, ?, ?, ?)", (user_id, username, password, 0.0, 'pending'), commit=True)
            bot.send_message(chat_id, "⏳ جاري معالجة طلبك يرجى الانتظار...")
            user_states.pop(user_id, None)

    elif call.data.startswith("adm_acc_approve_"):
        target_id = int(call.data.replace("adm_acc_approve_", ""))
        db_query("UPDATE accounts SET status='approved' WHERE user_id=?", (target_id,), commit=True)
        bot.edit_message_text(f"✅ تم قبول طلب الحساب لـ ({target_id})", chat_id, msg_id)
        bot.send_message(target_id, "🎉 تم إنشاء حسابك بنجاح! يمكنك الآن استخدام حسابك.")

    elif call.data.startswith("adm_acc_reject_"):
        target_id = int(call.data.replace("adm_acc_reject_", ""))
        # تم تصحيح الفاصلة هنا من (،) العربية إلى (,) الإنجليزية
        bot.edit_message_text(f"❌ تم رفض حساب ({target_id})", chat_id, msg_id)
        bot.send_message(target_id, "❌ عذراً، تم رفض الحساب مستخدم بالفعل، يرجى تغييرها وإعادة المحاولة ❌")
        user_states[target_id] = {"state": "create_username"}
        bot.send_message(target_id, "👤 يرجى كتابة اسم المستخدم الجديد الذي تريد:")

    elif call.data == "texas_deposit":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📱 Syriatel Cash", callback_data="dep_syriatel"),
            types.InlineKeyboardButton("📱 Sham Cash SYP", callback_data="dep_sham_syp"),
            types.InlineKeyboardButton("📱 Sham Cash Dollar", callback_data="dep_sham_usd"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_texas")
        )
        bot.edit_message_text("💳 اختر طريقة الدفع المناسبة لشحن حسابك:", chat_id, msg_id, reply_markup=markup)

    elif call.data in ["dep_syriatel", "dep_sham_syp", "dep_sham_usd"]:
        method = "Syriatel Cash" if call.data == "dep_syriatel" else ("Sham Cash SYP" if call.data == "dep_sham_syp" else "Sham Cash Dollar")
        user_states[user_id] = {"state": "dep_amount", "method": method}
        bot.send_message(chat_id, f"💵 تفادياً ستحصل على بونص مجاني 5% إضافي على عملية الشحن هذه بـ ({method})\n\n💵 يرجى كتابة المبلغ المراد شحنه بالأرقام:")

    elif call.data == "confirm_dep_amount":
        method = user_states[user_id]["method"]
        if method == "Syriatel Cash":
            bot.send_message(chat_id, "📌 يرجى إرسال الأموال الآن إلى الرقم التالي: '48122120'", reply_markup=get_confirm_keyboard("confirm_dep_sent", "back_to_main"))
        else:
            bot.send_message(chat_id, "📌 يرجى إرسال المبالغ إلى عنوان المحفظة التالي: 'a10750d533bfab7595dd9b3caa55a50221'", reply_markup=get_confirm_keyboard("confirm_dep_sent", "back_to_main"))

    elif call.data == "confirm_dep_sent":
        user_states[user_id] = {"state": "dep_proof", "method": user_states[user_id]["method"], "amount": user_states[user_id]["amount"]}
        bot.send_message(chat_id, "📸 يرجى إرسال صورة إيصال الدفع مع كتابة رقم المعاملة في نفس الرسالة:")

    elif call.data == "confirm_dep_final":
        if user_id in user_states and "proof_done" in user_states[user_id]:
            bot.send_message(chat_id, "⏳ جاري معالجة طلب شحن رصيدك يرجى الانتظار...")
            amount = user_states[user_id]["amount"]
            bonus_amount = amount * 1.05
            method = user_states[user_id]["method"]
            proof_text = user_states[user_id].get("proof_text", "لا يوجد نص")
            photo_id = user_states[user_id].get("photo_id")
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ شحن الرصيد", callback_data=f"adm_dep_ok_{user_id}_{bonus_amount}"))
            bot.send_message(GROUP_ID, f"💳 طلب شحن رصيد جديد عبر {method}\nالمبلغ المطلوب: {amount}\nالمبلغ مع البونص: {bonus_amount}\nنص المعاملة: {proof_text}")
            if photo_id:
                bot.send_photo(GROUP_ID, photo_id)

# ------- 7. تشغيل خادم الويب -------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
