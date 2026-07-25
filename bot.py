import telebot
from telebot import types
import time

# ==========================================
# 1. إعدادات البوت والروابط الرسمية والمجموعة
# ==========================================
TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"
SUPPORT_USERNAME = "@azzaman92"                      # حساب الدعم الفني الخاص بك
CHANNEL_URL = "https://t.me"      # رابط قناتك الرسمية الحقيقية

# ⚠️ هام جداً: ضع هنا الـ ID الخاص بالمجموعة (الغروب) لترسل العمليات إليها مباشرة
# تذكر أن معرف المجموعات يجب أن يبدأ دائماً بإشارة سالب (-) مثل: 1001234567890-
GROUP_CHAT_ID = -1001234567890  

bot = telebot.TeleBot(TOKEN)
user_states = {}

# ==========================================
# 2. دوال بناء القوائم والأزرار التفاعلية
# ==========================================

# دالة بناء القائمة الرئيسية الشفافة للبوت
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

# دالة بناء قائمة خيارات الشحن (شام كاش وسيرياتيل كاش)
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
    btn_approve = types.InlineKeyboardButton("✅ موافقة", callback_data=f"app_{user_id}")
    btn_reject = types.InlineKeyboardButton("❌ رفض", callback_data=f"rej_{user_id}")
    markup.add(btn_approve, btn_reject)
    return markup

# ==========================================
# 3. معالجة أوامر البوت وضغطات الأزرار
# ==========================================

# معالج أمر البدء /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private': return # تجاهل الأمر إذا أُرسل علناً داخل المجموعة
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

# معالج الضغط على الأزرار الشفافة التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    # [أ] معالجة أزرار التحكم بالموافقة والرفض داخل مجموعة الإدارة
    if call.data.startswith("app_") or call.data.startswith("rej_"):
        if call.message.chat.id != GROUP_CHAT_ID:
            bot.answer_callback_query(call.id, "⚠️ هذه الأزرار مخصصة للاستخدام داخل مجموعة الإدارة فقط!", show_alert=True)
            return
            
        target_user_id = int(call.data.split("_")[1])
        admin_name = call.from_user.first_name
        original_text = call.message.text
        
        if call.data.startswith("app_"):
            updated_text = f"{original_text}\n\n====================\n⚙️ *الحالة:* ✅ تم قبول الطلب وشحن الحساب بواسطة المشرف: {admin_name}"
            bot.edit_message_text(chat_id=GROUP_CHAT_ID, message_id=call.message.message_id, text=updated_text, parse_mode="Markdown")
            bot.answer_callback_query(call.id, "✅ تم شحن حساب العميل وإرسال إشعار له بنجاح!")
            try:
                bot.send_message(target_user_id, "🎉 *تحديث من الإدارة:*\n\n✅ تم التحقق من عملية الإيداع الخاصة بك بنجاح وتم شحن رصيدك في الحساب! شكراً لتعاملك معنا ومرحباً بك.", parse_mode="Markdown")
            except: pass
            
        elif call.data.startswith("rej_"):
            updated_text = f"{original_text}\n\n====================\n⚙️ *الحالة:* ❌ تم رفض الطلب بواسطة المشرف: {admin_name}"
            bot.edit_message_text(chat_id=GROUP_CHAT_ID, message_id=call.message.message_id, text=updated_text, parse_mode="Markdown")
            bot.answer_callback_query(call.id, "❌ تم رفض الطلب وإرسال التنبيه للمستخدم")
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
            user_states[user_id] = 'syriatel'
            bot.send_message(call.message.chat.id, "📞 *إيداع عبر سيرياتيل كاش:*\n\n1. قم بتحويل المبلغ المطلوب إلى رقم محفظتنا الإدارية.\n2. بعد التحويل، يرجى كتابة *رقم عملية التحويل (الرقم المرجعي)* والمبلغ هنا مباشرة لتأكيد الطلب.", parse_mode="Markdown")
        elif call.data == 'account':
            bot.send_message(call.message.chat.id, "🎮 *تفاصيل حساب BAHR:* \n\nلا يوجد حساب مرتبط حالياً.", parse_mode="Markdown")
        elif call.data == 'withdraw':
            bot.send_message(call.message.chat.id, "⬇️ *سحب رصيد:*\n\nأدخل المبلغ الذي ترغب في سحبه وطريقة المستلم وعنوان محفظتك للتنفيذ.", parse_mode="Markdown")
        elif call.data == 'gift':
            bot.send_message(call.message.chat.id, "🎁 *نظام الإهداء:*\n\nيمكنك تحويل رصيد أو إرسال هدايا لأصدقائك داخل البوت.", parse_mode="Markdown")
        elif call.data == 'referrals':
            bot.send_message(call.message.chat.id, "🔗 *نظام الإحالات:*\n\nاربح مكافآت وعمولات إضافية عند دعوة أصدقائك للبوت عبر الرابط الخاص بك.", parse_mode="Markdown")
        elif call.data == 'history':
            bot.send_message(call.message.chat.id, "📋 *السجل:*\n\nلم تقم بأي عمليات سحب أو إيداع مؤخراً.", parse_mode="Markdown")
        elif call.data == 'rewards':
            bot.send_message(call.message.chat.id, "🎉 *الجوائز:*\n\nتفقد قنواتنا للمشاركة في المسابقات اليومية والجوائز العشوائية العظمى.", parse_mode="Markdown")
        elif call.data == 'my_info':
            info = f"👤 *معلومات المستخدم:*\n\n• الاسم: {call.from_user.first_name}\n• الـ ID الخاص بك: `{user_id}`"
            bot.send_message(call.message.chat.id, info, parse_mode="Markdown")
        elif call.data == 'support':
            support_text = f"🆘 *الدعم الفني لـ BAHR TEAM:*\n\nفريقنا جاهز لخدمتك على مدار الساعة بخصوص عمليات السحب والإيداع والتثبيت.\n\n💬 للتواصل المباشر مع الإدارة والتحقق: {SUPPORT_USERNAME}"
            bot.send_message(call.message.chat.id, support_text, reply_markup=main_keyboard(), parse_mode="Markdown")
        elif call.data == 'vip':
            bot.send_message(call.message.chat.id, "🔱 *نظام VIP:*\n\nمميزات حصرية وعروض خاصة بالمستثمرين ذوي المبالغ العالية.", parse_mode="Markdown")
    except Exception as e:
        print(f"خطأ في معالجة الأزرار: {e}")

# معالج الرسائل النصية لاستلام البيانات وتمريرها للمجموعة المحددة
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.chat.type != 'private': return # حظر البوت من معالجة نصوص الدردشة العامة داخل المجموعة
    user_id = message.from_user.id
    
    if user_id in user_states:
        method = user_states[user_id]
        method_name = "شام كاش 📱" if method == "cham" else "سيرياتيل كاش 📞"
        
        bot.send_message(message.chat.id, "✅ *تم تلقي طلب الشحن بنجاح!*\n\nجاري مراجعة البيانات وفحصها من قبل الإدارة في المجموعة وسيتم إخطارك بالنتيجة فوراً هنا.", parse_mode="Markdown")
        
        # صياغة الرسالة الإدارية الاحترافية التي تُعرض للمشرفين في المجموعة
        group_alert = (
            f"🔔 *طلب شحن رصيد جديد جاري الفحص!*\n\n"
            f"• *العميل:* {message.from_user.first_name} (@{message.from_user.username if message.from_user.username else 'لا يوجد'})\n"
