import os
import sys
import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# 1. إعداد سجل الأخطاء
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 2. البيانات الخاصة بك الممررة مسبقاً
BOT_TOKEN = "8624354425:AAHozeXZgVkYS2njISkMA6IMEuCbyMno7Lg"
GROUP_ID = -1003983996094
OWNER_ID = 6693251012

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 3. إعداد قاعدة بيانات المشرفين والمشتركين تلقائياً
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT
    )""")
    cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, ?)", (OWNER_ID, "Owner"))
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_all_users():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# 4. حالات الإدخال (FSM) لمنع التداخل
class Form(StatesGroup):
    deposit_amount = State()
    withdraw_amount = State()
    support_msg = State()
    broadcast_msg = State()
    promote_admin = State()

# 5. كيبورد الأزرار الاحترافية
def main_keyboard(user_id: int):
    builder = ReplyKeyboardBuilder()
    builder.button(text="💰 إيداع")
    builder.button(text="💸 سحب")
    builder.button(text="📞 الدعم الفني")
    if is_admin(user_id):
        builder.button(text="⚙️ لوحة التحكم")
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 إذاعة للمشتركين", callback_data="admin_broadcast")
    builder.button(text="➕ تعيين أدمن جديد", callback_data="admin_promote")
    builder.button(text="🔄 إعادة تشغيل البوت", callback_data="admin_restart")
    builder.adjust(1)
    return builder.as_markup()

# 6. معالجة الرسائل والأوامر
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "لا يوجد"
    full_name = message.from_user.full_name
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", 
                   (user_id, username, full_name))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"مرحباً بك {full_name} في البوت المالي الاحترافي! 🚀\n\nاختر الخدمة المطلوبة من الأزرار بالأسفل:",
        reply_markup=main_keyboard(user_id)
    )

# أزرار العمليات (إيداع وسحب ودعم)
@dp.message(F.text == "💰 إيداع")
async def process_deposit(message: types.Message, state: FSMContext):
    await state.set_state(Form.deposit_amount)
    await message.answer("من فضلك، أرسل قيمة المبلغ الذي ترغب في إيداعه:")

@dp.message(Form.deposit_amount)
async def deposit_entered(message: types.Message, state: FSMContext):
    amount = message.text
    await state.clear()
    await message.answer(f"✅ تم تسجيل طلب الإيداع بقيمة: {amount}\nانتظر موافقة الإدارة.")
    await bot.send_message(
        chat_id=GROUP_ID,
        text=f"🔔 **طلب إيداع جديد**\n\n👤 المستخدم: {message.from_user.full_name}\n🆔 الأيدي: `{message.from_user.id}`\n💰 المبلغ: {amount}",
        parse_mode="Markdown"
    )

@dp.message(F.text == "💸 سحب")
async def process_withdraw(message: types.Message, state: FSMContext):
    await state.set_state(Form.withdraw_amount)
    await message.answer("من فضلك، أرسل قيمة المبلغ الذي ترغب في سحبه:")

@dp.message(Form.withdraw_amount)
async def withdraw_entered(message: types.Message, state: FSMContext):
    amount = message.text
    await state.clear()
    await message.answer(f"✅ تم تسجيل طلب السحب بقيمة: {amount}\nسيتم مراجعته فوراً.")
    await bot.send_message(
        chat_id=GROUP_ID,
        text=f"🔔 **طلب سحب جديد**\n\n👤 المستخدم: {message.from_user.full_name}\n🆔 الأيدي: `{message.from_user.id}`\n💸 المبلغ: {amount}",
        parse_mode="Markdown"
    )

@dp.message(F.text == "📞 الدعم الفني")
async def process_support(message: types.Message, state: FSMContext):
    await state.set_state(Form.support_msg)
    await message.answer("اكتب رسالتك أو استفسارك الآن وسيتم توجيهها للدعم الفني مباشرة:")

@dp.message(Form.support_msg)
async def support_entered(message: types.Message, state: FSMContext):
    msg_text = message.text
    await state.clear()
    await message.answer("✅ تم إرسال رسالتك بنجاح للدعم الفني، سيتواصل معك أحد المشرفين قريباً.")
    await bot.send_message(
        chat_id=GROUP_ID,
        text=f"📩 **رسالة دعم فني جديدة**\n\n👤 من: {message.from_user.full_name}\n🆔 الأيدي: `{message.from_user.id}`\n💬 الرسالة: {msg_text}",
        parse_mode="Markdown"
    )

# لوحة تحكم الإدارة
@dp.message(F.text == "⚙️ لوحة التحكم")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("مرحباً بك في لوحة تحكم الإدارة. اختر الإجراء المطلوب:", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(Form.broadcast_msg)
    await callback.message.answer("أرسل الآن الرسالة التي تريد إذاعتها لجميع المشتركين:")
    await callback.answer()

@dp.message(Form.broadcast_msg)
async def dynamic_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    users = get_all_users()
    success_count = 0
    await message.answer(f"⏳ يتم الآن الإرسال إلى {len(users)} مشترك...")
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=message.text)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            continue
    await message.answer(f"✅ اكتملت الإذاعة بنجاح!\nتم الإرسال إلى {success_count} مستخدم.")

@dp.callback_query(F.data == "admin_promote")
async def start_promote(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("❌ هذا الإجراء متاح للمالك الأساسي فقط!", show_alert=True)
        return
    await state.set_state(Form.promote_admin)
    await callback.message.answer("أرسل الآن (أيدي Telegram ID) الخاص بالشخص الذي تريد منحه صلاحيات أدمن:")
    await callback.answer()

@dp.message(Form.promote_admin)
async def promote_entered(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        new_admin_id = int(message.text)
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, ?)", (new_admin_id, "Admin"))
        conn.commit()
        conn.close()
        await message.answer(f"✅ تم منح صلاحيات الأدمن بنجاح للحساب: `{new_admin_id}`", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ خطأ: يرجى إرسال أيدي رقمي صحيح فقط.")

@dp.callback_query(F.data == "admin_restart")
async def restart_bot(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("🔄 جاري إعادة تشغيل البوت وتحديث الأنظمة الآن...")
    await callback.answer()
    sys.exit(0)

# خادم ويب مصغر لمنع توقف البوت في Render ولتلبية متطلبات الـ Port
async def handle_web(request):
    return web.Response(text="Bot is Running Successfully!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    # جلب المنفذ التلقائي الذي يفرضه Render، الافتراضي 10000
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Web server started on port {port}")

async def main():
    # تشغيل خادم الويب والبوت معاً في نفس الوقت
    await start_web_server()
    print("🚀 البوت الاحترافي يعمل الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
