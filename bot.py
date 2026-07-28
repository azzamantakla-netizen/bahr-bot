import os
import sys
import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# 1. إعداد سجل الأخطاء
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 2. البيانات الخاصة بك المعتمدة والمثبتة (مع التوكن الأخير)
BOT_TOKEN = "8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8"
GROUP_ID = -1003983996094
OWNER_ID = 6693251012

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 3. إعداد قاعدة البيانات ونظام طابور الأدوار والصالحيات
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        balance REAL DEFAULT 0.0,
        site_username TEXT DEFAULT NULL,
        site_password TEXT DEFAULT NULL
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdraw_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method TEXT,
        wallet_code TEXT DEFAULT NULL,
        status TEXT DEFAULT 'PENDING'
    )""")
    cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, ?)", (OWNER_ID, "Owner"))
    conn.commit()
    conn.close()

init_db()

# دالات التحقق والمساعدات المبرمجة لقاعدة البيانات
def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID: return True
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def get_user_data(user_id: int):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, site_username, site_password FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res if res else (0.0, None, None)

def get_queue_position(user_id: int) -> int:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM withdraw_queue WHERE status = 'PENDING' ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    for index, row in enumerate(rows):
        if row == user_id:
            return index + 1
    return 1

# 4. لعدم تداخل البيانات والأزرار (FSM حالات الإدخال)
class Form(StatesGroup):
    register_username = State()
    register_password = State()
    charge_site_amount = State()
    deposit_scash_code = State()
    deposit_sham_syp_code = State()
    deposit_sham_usd_code = State()
    admin_deposit_approve_amount = State()
    withdraw_site_amount = State()
    withdraw_cash_amount = State()
    withdraw_cash_wallet = State()
    admin_broadcast_msg = State()
    promote_admin_id = State()

# 5. لوحات التحكم وبناء الأزرار المدمجة (Inline Keyboards)
def main_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 حساب Texas", callback_data="menu_texas")
    builder.button(text="⬆️ شحن رصيد", callback_data="menu_deposit")
    builder.button(text="⬇️ سحب رصيد", callback_data="menu_withdraw_main")
    builder.button(text="🎁 إهداء (إذاعة)", callback_data="menu_broadcast")
    builder.button(text="🔗 إحالات", callback_data="under_dev")
    builder.button(text="📄 السجل", callback_data="under_dev")
    builder.button(text="👤 معلوماتي", callback_data="menu_my_info")
    builder.button(text="🚨 الدعم", callback_data="menu_support_info")
    if is_admin(user_id):
        builder.button(text="⚙️ لوحة التحكم للإدارة", callback_data="admin_panel")
    builder.adjust(1, 2, 2, 2, 1, 1 if is_admin(user_id) else 0)
    return builder.as_markup()

def texas_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 رابط الموقع", url="https://texas4win200.com")
    _, site_user, _ = get_user_data(user_id)
    account_text = "👤 حسابي" if site_user else "🆕 إنشاء حساب"
    builder.button(text=account_text, callback_data="texas_account_action")
    builder.button(text="💰 شحن الحساب", callback_data="under_dev")
    builder.button(text="💳 سحب رصيد من الـ...", callback_data="under_dev")
    builder.button(text="↩️ رجوع", callback_data="back_to_main")
    builder.adjust(1, 1, 2, 1)
    return builder.as_markup()

def deposit_methods_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Syriatel Cash 💳", callback_data="dep_syriatel")
    builder.button(text="🔴 شام كاش ليرة سورية", callback_data="dep_sham_syp")
    builder.button(text="🔵 شام كاش دولار امريكي", callback_data="dep_sham_usd")
    builder.button(text="↩️ رجوع", callback_data="back_to_main")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def withdraw_methods_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Syriatel Cash 💳", callback_data="wit_method_scash")
    builder.button(text="ShamCash SYP", callback_data="wit_method_sham")
    builder.button(text="↩️ رجوع", callback_data="back_to_main")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ تعيين أدمن جديد", callback_data="admin_promote")
    builder.button(text="🔄 إعادة تشغيل البوت", callback_data="admin_restart")
    builder.adjust(1)
    return builder.as_markup()

# 6. معالجات الأوامر والرسائل التفاعلية
@dp.message(CommandStart())
@dp.message(Command("start"))
async def cmd_start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "لا يوجد"
    full_name = message.from_user.full_name
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
    conn.commit()
    conn.close()
    welcome_msg = (
        "👋 أهلاً بك ضمن عائلتنا لقد صممنا هذا البوت خصيصاً لك\n\n"
        "✨ رصيدك في أمان يتيح لك هذا البوت سرعة قصوى في الإيداع ومرونة عالية في السحب\n\n"
        "👉 اختر أحد الخيارات بالأسفل"
    )
    force_remove = types.ReplyKeyboardRemove()
    await message.answer("🔄 جاري تحديث واجهة البوت وتجهيز الأزرار...", reply_markup=force_remove)
    await message.answer(welcome_msg, reply_markup=main_keyboard(user_id))

@dp.message(Command("balance"))
async def cmd_balance_handler(message: types.Message):
    bal, _, _ = get_user_data(message.from_user.id)
    await message.answer(f"💰 رصيدك الحالي في محفظة البوت المتاحة: {bal:,.2f} ل.س")

@dp.message(Command("support"))
async def cmd_support_handler(message: types.Message):
    await message.answer("📞 للدعم الفني والاستفسارات يرجى التواصل مع الإدارة مباشرة عبر المجموعة الخاصة بك.")

@dp.callback_query(F.data == "under_dev")
async def process_under_development(callback: types.CallbackQuery):
    await callback.answer("❌ هذا القسم قيد التطوير والصيانة حالياً، سيتم تفعيله قريباً!", show_alert=True)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    welcome_msg = "👋 أهلاً بك ضمن عائلتنا لقد صممنا هذا البوت خصيصاً لك\n\n✨ رصيدك في أمان يتيح لك هذا البوت سرعة قصوى في الإيداع ومرونة عالية في السحب"
    await callback.message.edit_text(welcome_msg, reply_markup=main_keyboard(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "menu_my_info")
async def process_my_info(callback: types.CallbackQuery):
    bal, site_user, _ = get_user_data(callback.from_user.id)
    status = "مسجل ومربوط" if site_user else "❌ غير مسجل"
    text = f"📊 **معلومات حسابك الحالية:**\n\n🆔 معرف التليجرام: `{callback.from_user.id}`\n💰 رصيد محفظتك: {bal:,.2f} ل.س\n⚙️ حالة ربط اللعبة: {status}"
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ رجوع", callback_data="back_to_main")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "menu_support_info")
async def process_support_info(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ رجوع", callback_data="back_to_main")
    await callback.message.edit_text("📞 للدعم الفني والاستفسارات يرجى التواصل مع الإدارة مباشرة عبر المجموعة الخاصة بك.", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "menu_texas")
async def process_menu_texas(callback: types.CallbackQuery):
    await callback.message.edit_text("⚙️ **إدارة حساب Texas بك الخاص:**", reply_markup=texas_keyboard(callback.from_user.id), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "texas_account_action")
async def process_texas_account(callback: types.CallbackQuery, state: FSMContext):
    bal, site_user, site_pass = get_user_data(callback.from_user.id)
    if site_user:
        text = f"---------------------------\n🆔 **المعرف:** `{callback.from_user.id}`\n👤 **اسم المستخدم:** `{site_user}`\n🔑 **كلمة المرور:** `{site_pass}`\n💰 **الرصيد الفعلي:** {bal:,.2f} ل.س\n---------------------------"
        builder = InlineKeyboardBuilder()
        builder.button(text="↩️ رجوع", callback_data="menu_texas")
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await state.set_state(Form.register_username)
        await callback.message.answer("🆕 إنشاء حساب جديد | يرجى إرسال اسم المستخدم الذي ترغب به:")
    await callback.answer()

# إعادة صياغة دالة الويب بشكل آمن لمنع تعليق المسافات (Indentation Error)
async def check_server_status(request):
    return web.Response(text="Server Active")

