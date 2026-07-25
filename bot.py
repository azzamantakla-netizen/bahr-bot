import subprocess
import sys
import logging

# كود إجباري لتثبيت مكتبة التيليجرام تلقائياً لمنع خطأ ModuleNotFoundError في السيرفر
try:
    import telegram
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot", "--upgrade"])
    import telegram

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ConversationHandler
)

# تفعيل سجل الأخطاء (Logging) لمراقبة عمل البوت
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# تعريف حالات المحادثة للتنقل بين القوائم
GET_USERNAME, GET_PASSWORD = range(2)
DEPOSIT_MENU, WITHDRAW_MENU = range(2, 4)

# إرسال الرسائل والتنبيهات إلى آيدي المجموعة الخاص بكم
GROUP_CHAT_ID = -1003983996094  

# دالة توليد القائمة الرئيسية للبوت
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("حساب Texas4win 🎮", callback_data="texas_account")],
        [InlineKeyboardButton("⬆️ شحن رصيد", callback_data="deposit"), InlineKeyboardButton("⬇️ سحب رصيد", callback_data="withdraw")],
        [InlineKeyboardButton("🎁 إهداء", callback_data="gift"), InlineKeyboardButton("🔗 إحالات", callback_data="referrals")],
        [InlineKeyboardButton("📋 السجل", callback_data="history"), InlineKeyboardButton("🎉 جوائز", callback_data="rewards")],
        [InlineKeyboardButton("👤 معلوماتي", callback_data="my_info")],
        [InlineKeyboardButton("🆘 الدعم", callback_data="support")],
        [InlineKeyboardButton("🔱 VIP", callback_data="vip")],
        [InlineKeyboardButton("🖥️ Bahr TEAM ↗️", url="https://t.me")]
    ]
    return InlineKeyboardMarkup(keyboard)

# 1. دالة البداية وعرض القائمة الرئيسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    welcome_message = (
        "مرحبا بكم في بوت **BAHR TEAM** 🌊\n"
        "فريقنا في خدمتكم على مدار الساعة، صمم هذا البوت بعناية لتعيش معنا مرونة السحب والايداع ⚡️\n\n"
        "اختر من القائمة أدناه لتنفيذ طلبك فوراً:"
    )
    if update.message:
        await update.message.reply_text(text=welcome_message, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    return ConversationHandler.END

# 2. نظام إنشاء حساب Texas4win
async def texas_account_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("👤 **خطوة 1 من 2:**\nالرجاء كتابة **اسم المستخدم (Username)** الذي ترغب به:")
    return GET_USERNAME

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['chosen_username'] = update.message.text
    await update.message.reply_text("🔑 **خطوة 2 من 2:**\nالرجاء كتابة **كلمة السر (Password)** التي ترغب بها:")
    return GET_PASSWORD

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['chosen_username']
    password = update.message.text
    client = update.effective_user
    
    await update.message.reply_text(
        f"✅ **تم استلام طلبك بنجاح!**\n\n"
        f"◽️ اسم المستخدم: `{username}`\n"
        f"◽️ كلمة السر: `{password}`\n\n"
        f"جاري مراجعة الطلب من قِبل إدارة **BahrTeam** لإنشاء حسابك وتفعيله في أقرب وقت."
    , parse_mode="Markdown")
    
    group_alert_text = (
        f"🚨 **طلب إنشاء حساب جديد في Texas4win!**\n\n"
        f"👤 **العميل:** {client.first_name}\n"
        f"🆔 **ID العميل:** `{client.id}`\n"
        f"🔗 **رابط الحساب:** [اضغط هنا](tg://user?id={client.id})\n\n"
        f"📌 **البيانات المطلوبة:**\n"
        f"🔹 اسم المستخدم: `{username}`\n"
        f"🔹 كلمة السر: `{password}`"
    )
    try:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=group_alert_text, parse_mode="Markdown")
    except Exception as e:
        print(f"فشل إرسال التنبيه إلى المجموعة: {e}")
    return ConversationHandler.END

# 3. واجهة شحن الرصيد
async def deposit_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current_balance = 0 
    
    deposit_text = f"UserID : `{user_id}`\n\nالرصيد : {current_balance}\nيرجى اختيار طريقة الشحن المناسبة :"
    deposit_keyboard = [
        [InlineKeyboardButton("Syriatel Cash 💳", callback_data="pay_syriatel")],
        [InlineKeyboardButton("🔴 شام كاش ليرة سورية", callback_data="pay_sham_syr")],
        [InlineKeyboardButton("🔵 شام كاش دولار امريكي", callback_data="pay_sham_usd")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_to_main")]
    ]
    await query.message.edit_text(text=deposit_text, reply_markup=InlineKeyboardMarkup(deposit_keyboard), parse_mode="Markdown")
    return DEPOSIT_MENU

# 4. واجهة سحب الرصيد
async def withdraw_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current_balance = 0  
    
    withdraw_text = f"UserID : `{user_id}`\n\nالرصيد : {current_balance}\nيرجى اختيار طريقة السحب المناسبة :"
    withdraw_keyboard = [
        [InlineKeyboardButton("Syriatel Cash 💳", callback_data="wd_syriatel")],
        [InlineKeyboardButton("ShamCash SYP", callback_data="wd_sham_syp")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_to_main")]
    ]
    await query.message.edit_text(text=withdraw_text, reply_markup=InlineKeyboardMarkup(withdraw_keyboard), parse_mode="Markdown")
    return WITHDRAW_MENU

# دالة التحكم بالرجوع لقوائم الإيداع والسحب
async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "back_to_main":
        welcome_message = (
            "مرحبا بكم في بوت **BAHR TEAM** 🌊\n"
            "فريقنا في خدمتكم على مدار الساعة، صمم هذا البوت بعناية لتعيش معنا مرونة السحب والايداع ⚡️\n\n"
            "اختر من القائمة أدناه لتنفيذ طلبك فوراً:"
        )
        await query.message.edit_text(text=welcome_message, reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return ConversationHandler.END
    return ConversationHandler.END

# 5. معالجة بقية أزرار القائمة الرئيسية (الردود السريعة)
async def general_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if query.data == "gift":
        await query.message.reply_text("🎁 **قسم الإهداء:**\nهذه الميزة تمكنك من تحويل الرصيد إلى أصدقائك داخل البوت فوراً. (قيد الصيانة حالياً) 🛠️", parse_mode="Markdown")
    elif query.data == "referrals":
        referral_link = f"https://t.me{user.id}"
        await query.message.reply_text(f"🔗 **نظام الإحالات لـ BAHR TEAM:**\n\nشارك رابط الإحالة الخاص بك مع أصدقائك واحصل على مكافآت مجزية عند شحنهم!\n\nرابطك: {referral_link}", parse_mode="Markdown")
    elif query.data == "history":
        await query.message.reply_text("📋 **سجل العمليات:**\nلا توجد عمليات سحب أو إيداع مسجلة في حسابك حتى الآن.", parse_mode="Markdown")
    elif query.data == "rewards":
        await query.message.reply_text("🎉 **قسم الجوائز والمسابقات:**\nتابع قنواتنا الرسمية لمعرفة أكواد الخصم والمسابقات اليومية المخصصة لأعضاء الفريق!", parse_mode="Markdown")
    elif query.data == "my_info":
        info_text = (
            f"👤 **ملف معلوماتك الشخصية:**\n\n"
            f"▫️ الاسم: {user.first_name}\n"
            f"▫️ المعرف الذاتي (ID): `{user.id}`\n"
            f"▫️ الرصيد الحالي: `0.00$`\n"
            f"▫️ مستوى الحساب: لاعب عادي"
        )
        await query.message.reply_text(text=info_text, parse_mode="Markdown")
    elif query.data == "support":
        await query.message.reply_text("🆘 **الدعم الفني والشكاوى:**\nإذا واجهتك أي مشكلة في السحب أو الإيداع، يرجى التواصل مع إدارة العمليات مباشرة: @YourAdminUsername", parse_mode="Markdown")
    elif query.data == "vip":
        await query.message.reply_text("🔱 **مميزات عضوية VIP:**\nاحصل على سرعة فائقة في معالجة عمليات السحب والإيداع، ونسب كاش باك حصرية للاعبي النخبة. للتفعيل تواصل مع الإدارة.", parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ تم إلغاء العملية. يمكنك العودة للقائمة بكتابة /start")
    return ConversationHandler.END

def main() -> None:
    # 📌 التحديث: تم وضع التوكن الخاص بك بنجاح ومباشرة هنا لحماية عمل البوت
    TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"  
    
    application = Application.builder().token(TOKEN).build()
    
    main_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(texas_account_clicked, pattern="^texas_account$"),
            CallbackQueryHandler(deposit_clicked, pattern="^deposit$"),
            CallbackQueryHandler(withdraw_clicked, pattern="^withdraw$")
        ],
        states={
            GET_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username)],
            GET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
            DEPOSIT_MENU: [CallbackQueryHandler(back_handler)],
            WITHDRAW_MENU: [CallbackQueryHandler(back_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(main_conv)
    application.add_handler(CallbackQueryHandler(general_buttons_handler, pattern="^(gift|referrals|history|rewards|my_info|support|vip)$"))
    
    print("البوت يعمل بالتوكن الرسمي لـ BAHR TEAM...")
    application.run_polling()

if __name__ == '__main__':
    main()
