import telebot
from telebot import types
import time

# ==========================================
# 1. الإعدادات الأساسية والمعرفات الحقيقية
# ==========================================
TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"
SUPPORT_USERNAME = "@azzaman92"                      # حساب الدعم الفني الخاص بك
CHANNEL_URL = "https://t.me"      # رابط قناتك الرسمية

# تم وضع المعرف الحقيقي لمجموعتك مباشرة في الكود ليعمل فوراً
GROUP_CHAT_ID = -1003983996094  

bot = telebot.TeleBot(TOKEN)
user_states = {}

# قائمة الملاك والمشرفين البرمجية (المعرف الخاص بك هو المالك الأساسي المدمج)
# المشرفون الجدد الذين ستقوم بإضافتهم عبر الأوامر سيتم حفظهم في ذاكرة السيرفر تلقائياً
ADMINS_LIST = [6693251012]

# ==========================================
# 2. دوال بناء القوائم والأزرار التفاعلية
# ==========================================

# دالة بناء القائمة الرئيسية الشفافة للبوت (الخاص بالعملاء)
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🎮 حساب BAHR", callback_data='account'))
    markup.add(types.InlineKeyboardButton("⬆️ شحن رصيد", callback_data='deposit_menu'), types.InlineKeyboardButton("⬇️ سحب رصيد", callback_data='withdraw'))
    markup.add(types.InlineKeyboardButton("🎁 إهداء", callback_data='gift'), types.InlineKeyboardButton("🔗 إحالات", callback_data='referrals'))
    markup.add(types.InlineKeyboardButton("📋 السجل", callback_data='history'), types.InlineKeyboardButton("🎉 جوائز", callback_data='rewards'))
    markup.add(types.InlineKeyboardButton("👤 معلوماتي", callback_data='my_info'))
    markup.add(types.InlineKeyboardButton("🆘 الدعم", callback_data='support'))
    markup.add(types.InlineKeyboardButton("🔱 VIP", callback_data='vip'))
    markup.add(types.InlineKeyboardButton("📺 Bahr TEAM ↗️", url=CHANNEL_URL))
    return markup

# دالة بناء قائمة خيارات الشحن
def deposit_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📱 شحن عبر شام كاش (بونص 5%)", callback_data='pay_cham'),
        types.InlineKeyboardButton("📞 شحن عبر سيرياتيل كاش", callback_data='pay_syriatel'),
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')
    )
    return markup

# دالة بناء أزرار التحكم بالموافقة والرفض المخصصة للمشرفين داخل المجموعة
def admin_action_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_approve = types.InlineKeyboardButton("✅ قبول الطلب", callback_data=f"app_{user_id}")
    btn_reject = types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"rej_{user_id}")
    markup.add(btn_approve, btn_reject)
    return markup

# ==========================================
# 3. نظام أوامر إدارة المشرفين والملاك من المجموعة
# ==========================================

# أمر إضافة مشرف جديد من داخل المجموعة: يكتب المالك (/add_admin ثم الـ ID)
@bot.message_handler(commands=['add_admin'])
def add_admin_command(message):
    if message.chat.id != GROUP_CHAT_ID: return
    sender_id = message.from_user.id
    
    # التحقق من أن المرسل هو المالك الأساسي للبوت
    if sender_id != 6693251012:
        bot.reply_to(message, "⚠️ هذا الأمر مخصص للمالك الأساسي للبوت فقط!")
        return
        
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "📝 الطريقة الصحيحة للأمر:\n`/add_admin وضع_رقم_الـID_هنا`", parse_mode="Markdown")
            return
            
        new_admin_id = int(parts[1])
        if new_admin_id not in ADMINS_LIST:
            ADMINS_LIST.append(new_admin_id)
            bot.reply_to(message, f"✅ تم بنجاح إضافة المشرف الجديد وتفعيل صلاحياته البرمجية في البوت!\n• الـ ID المضاف: `{new_admin_id}`", parse_mode="Markdown")
        else:
            bot.reply_to(message, "ℹ️ هذا المستخدم مضاف بالفعل كمشرف في النظام.")
    except ValueError:
        bot.reply_to(message, "❌ خطأ! يرجى إدخال رقم الـ ID بشكل صحيح (أرقام فقط).")

# أمر حذف مشرف من المجموعة: يكتب المالك (/del_admin ثم الـ ID)
@bot.message_handler(commands=['del_admin'])
def del_admin_command(message):
    if message.chat.id != GROUP_CHAT_ID: return
    sender_id = message.from_user.id
    
    if sender_id != 6693251012:
        bot.reply_to(message, "⚠️ هذا الأمر مخصص للمالك الأساسي للبوت فقط!")
        return
        
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "📝 الطريقة الصحيحة للأمر:\n`/del_admin وضع_رقم_الـID_هنا`", parse_mode="Markdown")
            return
            
        target_id = int(parts[1])
        if target_id == 6693251012:
            bot.reply_to(message, "❌ لا يمكنك حذف نفسك من الملكية الأساسية للبوت!")
            return
            
        if target_id in ADMINS_LIST:
            ADMINS_LIST.remove(target_id)
            bot.reply_to(message, f"🗑 تم إلغاء صلاحيات المشرف بنجاح وسحب ملكيته من البوت.\n• الـ ID المحذوف: `{target_id}`", parse_mode="Markdown")
        else:
            bot.reply_to(message, "ℹ️ هذا المستخدم ليس مشرفاً في البوت حالياً.")
    except ValueError:
        bot.reply_to(message, "❌ خطأ! يرجى إدخال رقم الـ ID بشكل صحيح (أرقام فقط).")

# أمر عرض قائمة المشرفين الحاليين في المجموعة
@bot.message_handler(commands=['list_admins'])
def list_admins_command(message):
    if message.chat.id != GROUP_CHAT_ID: return
    if message.from_user.id not in ADMINS_LIST: return
    
    admins_text = "👥 *قائمة المشرفين والملاك الحاليين في البوت:*\n\n"
    for idx, admin_id in enumerate(ADMINS_LIST, 1):
        role = "👑 المالك الأساسي" if admin_id == 6693251012 else "👤 مشرف مضاف"
        admins_text += f"{idx}. المعرف المالي: `{admin_id}` | الصلاحية: *{role}*\n"
        
    bot.reply_to(message, admins_text, parse_mode="Markdown")

# ==========================================
# 4. معالجة أوامر المستخدم العادية والرسائل
# ==========================================

# معالج أمر البدء /start في الخاص بالعملاء
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private': return 
    user_id = message.from_user.id
    if user_id in user_states: del user_states[user_id]
        
    welcome_text = (
        f"مرحباً بك يا {message.from_user.first_name} في بوت *BAHR TEAM* 🌊\n\n"
        "فريقنا في خدمتكم على مدار الساعة. لقد تم تصميم هذا البوت "
        "ليمنحك تحكماً كاملاً في رصيدك بسرعة وأمان. 🔒⚡\n\n"
        "🎁 *العروض الحالية:*\n"
        "• بونص ثابت 5% على أكواد شام كاش.\n"
        "• بونص 10% على مبالغ الإيداع العالية.\n\n"
        "⚡ *ماذا تريد أن تفعل اليوم؟ اختر من القائمة أدناه لتنفيذ طلبك فوراً:*"
    )
    try:
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(), parse_mode="Markdown")
    except Exception as e:
        print(f"خطأ إرسال الترحيب: {e}")

# معالج الضغط على الأزرار الشفافة التفاعلية (للمستخدمين والمشرفين)
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    # [أ] معالجة أزرار التحكم بالقبول والرفض داخل مجموعة الإدارة
    if call.data.startswith("app_") or call.data.startswith("rej_"):
        # التحقق من أن المستخدم الضاغط على الزر مسجل في قائمة المشرفين
        if user_id not in ADMINS_LIST:
            bot.answer_callback_query(call.id, "⚠️ عذراً، أنت لست مشرفاً أو مالكاً للبوت لتتخذ هذا الإجراء المالية!", show_alert=True)
            return
            
        target_user_id = int(call.data.split("_")[1])
        admin_name = call.from_user.first_name
        original_text = call.message.text
        
        if call.data.startswith("app_"):
            updated_text = f"{original_text}\n\n====================\n⚙️ *الإجراء:* ✅ تم قبول الطلب وشحن الحساب بواسطة المشرف: *{admin_name}*"
            bot.edit_message_text(chat_id=GROUP_CHAT_ID, message_id=call.message.message_id, text=updated_text, parse_mode="Markdown")
            bot.answer_callback_query(call.id, "✅ تم قبول العملية بنجاح!")
            try:
                bot.send_message(target_user_id, "🎉 *تحديث من الإدارة:*\n\n✅ تم التحقق من عملية الإيداع الخاصة بك بنجاح وتم شحن رصيدك في الحساب! شكراً لتعاملك معنا ومرحباً بك.", parse_mode="Markdown")
            except: pass
            
        elif call.data.startswith("rej_"):
            updated_text = f"{original_text}\n\n====================\n⚙️ *الإجراء:* ❌ تم رفض الطلب بواسطة المشرف: *{admin_name}*"
            bot.edit_message_text(chat_id=GROUP_CHAT_ID, message_id=call.message.message_id, text=updated_text, parse_mode="Markdown")
            bot.answer_callback_query(call.id, "❌ تم رفض العملية بنجاح!")
            try:
                bot.send_message(target_user_id, "⚠️ *تحديث من الإدارة:*\n\n❌ عذراً، تم رفض طلب الشحن الخاص بك نظراً لعدم صحة البيانات المرسلة أو عدم وصول التحويل. يرجى مراجعة الدعم الفني.", parse_mode="Markdown")
            except: pass
        return

    # [ب] معالجة خيارات أزرار المستخدم العادية في الخاص
    try:
        if call.data == 'main_menu':
            if user_id in user_states: del user_states[user_id]
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⚡ *ماذا تريد أن تفعل اليوم؟ اختر من القائمة أدناه:*", reply_markup=main_keyboard(), parse_mode="Markdown")
        elif call.data == 'deposit_menu':
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⬆️ *قسم شحن الرصيد:*\n\nيرجى اختيار وسيلة الشحن المناسبة لك لوضع الطلب واستلام البونص:", reply_markup=deposit_keyboard(), parse_mode="Markdown")
        elif call.data == 'pay_cham':
            user_states[user_id] = 'cham'
            bot.send_message(call.message.chat.id, "📱 *إيداع عبر شام كاش (بونص 5%):*\n\nيرجى كتابة أو إرسال *كود شام كاش* الخاص بك هنا في المحادثة مباشرة.\nسيتلقى فريق العمل الكود فوراً في المجموعة لتأكيده وشحن حسابك.", parse_mode="Markdown")
        elif call.data == 'pay_syriatel':
