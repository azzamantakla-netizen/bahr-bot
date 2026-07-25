import telebot
from telebot import types
import time

# 1. بيانات البوت والمسؤول المباشرة (تم ربطها بمعرفاتك الرسمية)
TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"
ADMIN_ID = 6693251012
SUPPORT_USERNAME = "@azzaman92"  # حساب الدعم الفني الخاص بك
CHANNEL_URL = "https://t.me/+i3kkz_g256U1NGNk"  # رابط قناة Bahr TEAM الرسمية

bot = telebot.TeleBot(TOKEN)
user_states = {}

# دالة بناء القائمة الرئيسية بالأزرار الشفافة
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🎮 حساب BAHR", callback_data='account'))
    markup.add(types.InlineKeyboardButton("⬆️ شحن رصيد", callback_data='deposit_menu'), types.InlineKeyboardButton("⬇️ سحب رصيد", callback_data='withdraw'))
    markup.add(types.InlineKeyboardButton("🎁 إهداء", callback_data='gift'), types.InlineKeyboardButton("🔗 إحالات", callback_data='referrals'))
    markup.add(types.InlineKeyboardButton("📋 السجل", callback_data='history'), types.InlineKeyboardButton("🎉 جوائز", callback_data='rewards'))
    markup.add(types.InlineKeyboardButton("👤 معلوماتي", callback_data='my_info'))
    markup.add(types.InlineKeyboardButton("🆘 الدعم", callback_data='support'))
    markup.add(types.InlineKeyboardButton("🔱 VIP", callback_data='vip'))
    markup.add(types.InlineKeyboardButton("📺 Bahr TEAM ↗️", url=CHANNEL_URL)) # ربط الزر بقناتك الرسمية مباشرة
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

# معالج أمر البدء /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
        
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

# معالج الضغط على الأزرار الشفافة Inline
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    try:
        if call.data == 'main_menu':
            if user_id in user_states: del user_states[user_id]
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⚡ *ماذا تريد أن تفعل اليوم؟ اختر من القائمة أدناه:*", reply_markup=main_keyboard(), parse_mode="Markdown")
        elif call.data == 'deposit_menu':
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⬆️ *قسم شحن الرصيد:*\n\nيرجى اختيار وسيلة الشحن المناسبة لك لوضع الطلب واستلام البونص:", reply_markup=deposit_keyboard(), parse_mode="Markdown")
        elif call.data == 'pay_cham':
            user_states[user_id] = 'cham'
            bot.send_message(call.message.chat.id, "📱 *إيداع عبر شام كاش (بونص 5%):*\n\nيرجى كتابة أو إرسال *كود شام كاش* الخاص بك هنا في المحادثة مباشرة.\nسيتلقى المشرف الكود فوراً لتأكيده وشحن حسابك.", parse_mode="Markdown")
        elif call.data == 'pay_syriatel':
            user_states[user_id] = 'syriatel'
            bot.send_message(call.message.chat.id, "📞 *إيداع عبر سيرياتيل كاش:*\n\n1. قم بتحويل المبلغ المطلوب إلى رقم محفظتنا (يرجى مراجعة الدعم لمعرفة الرقم الحالي).\n2. بعد التحويل، يرجى كتابة *رقم عملية التحويل (الرقم المرجعي)* والمبلغ هنا مباشرة لتأكيد الطلب.", parse_mode="Markdown")
        elif call.data == 'account':
            bot.send_message(call.message.chat.id, "🎮 *تفاصيل حساب BAHR:* \n\nلا يوجد حساب مرتبط حالياً.", parse_mode="Markdown")
        elif call.data == 'withdraw':
            bot.send_message(call.message.chat.id, "⬇ *سحب رصيد:*\n\nأدخل المبلغ الذي ترغب في سحبه وطريقة المستلم وعنوان محفظتك.", parse_mode="Markdown")
        elif call.data == 'gift':
            bot.send_message(call.message.chat.id, "🎁 *نظام الإهداء:*\n\nيمكنك تحويل رصيد أو إرسال هدايا لأصدقائك داخل البوت.", parse_mode="Markdown")
        elif call.data == 'referrals':
            bot.send_message(call.message.chat.id, "🔗 *نظام الإحالات:*\n\nاربح مكافآت وعمولات إضافية عند دعوة أصدقائك للبوت.", parse_mode="Markdown")
        elif call.data == 'history':
            bot.send_message(call.message.chat.id, "📋 *السجل:*\n\nلم تقم بأي عمليات سحب أو إيداع مؤخراً.", parse_mode="Markdown")
        elif call.data == 'rewards':
            bot.send_message(call.message.chat.id, "🎉 *الجوائز:*\n\nتفقد قنواتنا للمشاركة في المسابقات اليومية والجوائز العشوائية.", parse_mode="Markdown")
        elif call.data == 'my_info':
            info = f"👤 *معلومات المستخدم:*\n\n• الاسم: {call.from_user.first_name}\n• الـ ID: `{user_id}`"
            bot.send_message(call.message.chat.id, info, parse_mode="Markdown")
        elif call.data == 'support':
            # تحديث نص الدعم الفني بالمعرف الخاص بك مباشرة
            support_text = f"🆘 *الدعم الفني لـ BAHR TEAM:*\n\nفريقنا جاهز لخدمتك على مدار الساعة بخصوص عمليات السحب والإيداع والتثبيت.\n\n💬 للتواصل المباشر مع الإدارة: {SUPPORT_USERNAME}"
            bot.send_message(call.message.chat.id, support_text, reply_markup=main_keyboard(), parse_mode="Markdown")
        elif call.data == 'vip':
            bot.send_message(call.message.chat.id, "🔱 *نظام VIP:*\n\nمميزات حصرية وعروض خاصة بالمستثمرين ذوي المبالغ العالية.", parse_mode="Markdown")
    except Exception as e:
        print(f"خطأ في معالجة الأزرار: {e}")

# معالج الرسائل النصية لاستلام طلبات الشحن
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    if user_id in user_states:
        method = user_states[user_id]
        method_name = "شام كاش 📱" if method == "cham" else "سيرياتيل كاش 📞"
        bot.send_message(message.chat.id, "✅ تم تلقي طلب الشحن بنجاح! جاري مراجعة البيانات من قبل الإدارة وسيتم الشحن فور التأكيد.")
        admin_alert = (
            f"🔔 *طلب شحن رصيد جديد!*\n\n"
            f"• *المستحدم:* {message.from_user.first_name} (@{message.from_user.username if message.from_user.username else 'لا يوجد'})\n"
            f"• *الـ ID:* `{user_id}`\n"
            f"• *الوسيلة:* {method_name}\n"
            f"• *البيانات المرسلة:* `{message.text}`"
        )
        try:
            bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown")
        except:
            pass
        del user_states[user_id]
    else:
        try:
            bot.send_message(message.chat.id, "يرجى استخدام القوائم والأزرار المتاحة لتوجيه طلبك بشكل صحيح.", reply_markup=main_keyboard(), parse_mode="Markdown")
        except:
            pass

print("🚀 تم تشغيل البوت بنجاح وبانتظار استقبال طلبات العمليات المنسقة...")
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        time.sleep(3)
