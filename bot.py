import os
import sys
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# 1. إعداد سجل الأخطاء الاحترافي
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 2. البيانات الخاصة بك المعتمدة والمثبتة
BOT_TOKEN = "8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8"
GROUP_ID = -1003983996094
OWNER_ID = 6693251012

# تذكر وضع رابط تطبيق الويب الخاص بك على Render هنا (مثال: https://onrender.com)
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 3. إعداد قاعدة البيانات ونظام طابور الأدوار والصلاحيات
def init_db():
    try:
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
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                role TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                wallet_code TEXT DEFAULT NULL,
                status TEXT DEFAULT 'PENDING'
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, ?)", (OWNER_ID, "Owner"))
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")

# دالات التحقق والمساعدات لقاعدة البيانات
def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID: return True
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res is not None
    except Exception:
        return False

def get_user_data(user_id: int):
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT balance, site_username, site_password FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res if res else (0.0, None, None)
    except Exception:
        return (0.0, None, None)

# 4. حالات الإدخال FSM لنظام البيانات والأرقام
class Form(StatesGroup):
    register_username = State()
    register_password = State()
    charge_site_amount = State()
    deposit_syriatel_code = State()
    deposit_sham_syp_code = State()
    deposit_sham_usd_code = State()

# 5. لوحات التحكم وأزرار البوت (Inline Keyboards)
def main_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ حساب Texas", callback_data="menu_texas")
    builder.button(text="💵 شحن رصيد", callback_data="menu_deposit")
    builder.button(text="💸 سحب رصيد", callback_data="under_dev")
    builder.button(text="👤 معلوماتي", callback_data="menu_my_info")
    builder.button(text="📞 الدعم الفني", callback_data="menu_support_info")
    if is_admin(user_id):
        builder.button(text="👑 لوحة الإدارة", callback_data="under_dev")
    builder.adjust(1, 2, 2, 1 if is_admin(user_id) else 0)
    return builder.as_markup()

def texas_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 رابط الموقع", url="https://texasadmin200.com")
    _, site_user, _ = get_user_data(user_id)
    account_text = "🔄 تحديث بيانات حسابي" if site_user else "🔐 إنشاء حساب"
    builder.button(text=account_text, callback_data="texas_account_action")
    builder.button(text="🔙 رجوع", callback_data="back_to_main")
    builder.adjust(1, 1)
    return builder.as_markup()

# 6. معالجات الأوامر والرسائل التفاعلية
@dp.message(CommandStart())
@dp.message(Command("start"))
async def cmd_start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "لا يوجد"
    full_name = message.from_user.full_name
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                       (user_id, username, full_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Database error in start: {e}")
    
    welcome_msg = (
        "أهلاً بك في بوت شحن الرصيد الفوري آلياً\n"
        "رصيدك في أمان يتيح لك هذا البوت سرعة قصوى في الإيداع ومرونة عالية في السحب\n"
        "اختر أحد الخيارات في الأسفل 👇"
    )
    await message.answer(welcome_msg, reply_markup=main_keyboard(user_id))

@dp.callback_query(F.data == "under_dev")
async def process_under_development_callback(callback: types.CallbackQuery):
    await callback.answer("هذا القسم قيد التطوير والصيانة حالياً 🛠️", show_alert=True)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    welcome_msg = "رصيدك في أمان يتيح لك هذا البوت سرعة قصوى في الإيداع ومرونة عالية في السحب\nاختر من القائمة:"
    await callback.message.edit_text(welcome_msg, reply_markup=main_keyboard(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "menu_my_info")
async def process_my_info_callback(callback: types.CallbackQuery):
    bal, site_user, _ = get_user_data(callback.from_user.id)
    status = f"مربوط ({site_user})" if site_user else "غير مربوط ❌"
    text = f"👤 *معلومات حسابك الحالية:*\n\n💰 رصيد محفظتك: {bal:.2f} ليرة\n🔐 حالة ربط المنصة: {status}"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 رجوع", callback_data="back_to_main")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "menu_support_info")
async def process_support_info_callback(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 رجوع", callback_data="back_to_main")
    await callback.message.edit_text("الدعم الفني والاستفسارات يرجى التواصل مع الإدارة مباشرة عبر المجموعة الخاصة بك", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "menu_texas")
async def process_menu_texas_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("⚙️ إدارة حسابك وتفاصيل منصة Texas:", reply_markup=texas_keyboard(callback.from_user.id))
    await callback.answer()

# معالجة طلبات الويب الواردة من تليجرام (Webhook Handler)
async def handle_webhook(request):
    try:
        json_data = await request.json()
        update = types.Update.model_validate(json_data, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Error handling webhook update: {e}")
    return web.Response(text="OK")

async def main_response(request):
    return web.Response(text="Bot Web Server is Running via Webhook!")

# دوال بدء وإغلاق السيرفر والويب هوك بالتتابع الآمن
async def on_startup(app):
    init_db()
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        await bot.set_webhook(webhook_url)
        logging.info(f"Webhook successfully set to: {webhook_url}")
    else:
        logging.warning("RENDER_EXTERNAL_URL environment variable is missing!")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get('/', main_response)
    app.router.add_post('/webhook', handle_webhook)
    
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
