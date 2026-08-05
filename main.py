import os
import json
import time
import threading
import logging
import base64
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import tls_client

# =============================================================================
# Logging Setup
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Base Configuration
# =============================================================================
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
ADMIN_GROUP_ID = -1003983996094
PANEL_BASE = "https://texas4win.com"
RENDER_URL = "https://onrender.com"

# Dynamic credentials and payment details
AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"
SHAM_CASH_WALLET = "a18758d5324eb7595d4463ca355ad221"
SYRIATEL_CASH_CODE = "481 22120"

# File paths
OWNERS_FILE = "owners.txt"
ADMINS_FILE = "admins.txt"
USERS_FILE = "users.txt"
PLAYERS_DB_FILE = "players_db.json"

# In-memory lists
owners_list = []
admins_list = []
users_list = []

# API Session
session = tls_client.Session(
    client_identifier="chrome_120",
    random_tls_extension_order=True
)
access_token = None
refresh_token = None
agent_affiliate_id = None

# States & temporary data
user_states = {}
state_data = {}
pending_deposits = {}
pending_withdrawals = {}
support_tickets = {}

# Bot & Flask
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# =============================================================================
# Helper Functions - File I/O
# =============================================================================
def load_list_from_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_list_to_file(filepath, data_list):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data_list:
            f.write(str(item) + "\n")


def load_owners():
    global owners_list
    owners_list = load_list_from_file(OWNERS_FILE)
    uid = str(OWNER_ID)
    if uid not in owners_list:
        owners_list.append(uid)
        save_list_to_file(OWNERS_FILE, owners_list)


def load_admins():
    global admins_list
    admins_list = load_list_from_file(ADMINS_FILE)


def load_users_list():
    global users_list
    users_list = load_list_from_file(USERS_FILE)


def add_user(user_id):
    uid = str(user_id)
    if uid not in users_list:
        users_list.append(uid)
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(uid + "\n")


def load_players_db():
    if os.path.exists(PLAYERS_DB_FILE):
        with open(PLAYERS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_players_db(data):
    with open(PLAYERS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


players_db = load_players_db()

# =============================================================================
# API Helpers
# =============================================================================
def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            decoded = base64.b64decode(payload_b64)
            return json.loads(decoded)
    except Exception as e:
        logger.error(f"JWT decode error: {e}")
    return {}


def api_request(method, endpoint, payload=None, auth=False):
    url = f"{PANEL_BASE}/{endpoint}"
    headers = {"Content-Type": "application/json"}
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    try:
        if method.upper() == "GET":
            response = session.get(url, headers=headers, timeout=30)
        else:
            response = session.post(url, headers=headers, json=payload, timeout=30)
        try:
            return response.json()
        except Exception:
            logger.error(f"Non-JSON response from {endpoint}: {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"API request error to {endpoint}: {e}")
        return None


def do_signin():
    global access_token, refresh_token
    payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
    result = api_request("POST", "global/api/UserApi/signIn", payload)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        access_token = result["result"].get("accessToken")
        refresh_token = result["result"].get("refreshToken")
        logger.info("Sign in successful")
        return True
    logger.error(f"Sign in failed: {result}")
    return False


def get_agent_affiliate_id():
    global agent_affiliate_id
    payload = {
        "start": 0,
        "limit": 20,
        "filter": {
            "self": {"action": "=", "value": True, "valueLabel": "true"}
        },
        "isNextPage": False,
        "searchBy": {"agentChildrenList": ""}
    }
    result = api_request("POST", "global/api/UserApi/getChildren", payload, auth=True)
    if result and result.get("status") and result.get("result"):
        records = result["result"].get("records", [])
        if records:
            agent_affiliate_id = str(records[0].get("affiliateId"))
            logger.info(f"Agent affiliateId from getChildren: {agent_affiliate_id}")
            return agent_affiliate_id
    if access_token:
        jwt_data = decode_jwt_payload(access_token)
        for key in ["affiliateId", "userId", "id", "sub"]:
            if key in jwt_data:
                agent_affiliate_id = str(jwt_data[key])
                logger.info(f"Agent affiliateId from JWT ({key}): {agent_affiliate_id}")
                return agent_affiliate_id
    logger.warning("Could not determine agent affiliateId")
    return None


def token_refresh_loop():
    global access_token, refresh_token
    while True:
        time.sleep(45 * 60)
        if refresh_token:
            payload = {"refreshToken": refresh_token}
            result = api_request("POST", "global/api/UserApi/refreshToken", payload)
            if result and result.get("status") and isinstance(result.get("result"), dict):
                access_token = result["result"].get("accessToken")
                refresh_token = result["result"].get("refreshToken")
                logger.info("Token refreshed successfully")
            else:
                logger.warning("Token refresh failed, attempting sign in")
                do_signin()
        else:
            do_signin()

# =============================================================================
# Keyboard Markups
# =============================================================================
def main_menu_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("👤 حسابي"),
        KeyboardButton("📥 إيداع / شحن رصيد"),
        KeyboardButton("📩 سحب رصيد"),
        KeyboardButton("📞 الدعم الفني")
    )
    return markup


def back_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔙 رجوع"))
    return markup

# =============================================================================
# Admin Panel Helper
# =============================================================================
def show_admin_panel(chat_id, message_id=None):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💼 تعديل بيانات الوكيل", callback_data="admin_agent_data"),
        InlineKeyboardButton("💰 تعديل محفظة شام كاش", callback_data="admin_sham_wallet"),
        InlineKeyboardButton("📱 تعديل كود سيرياتيل", callback_data="admin_syriatel_code"),
        InlineKeyboardButton("📊 رصيد الخزنة الحالي", callback_data="admin_balance"),
        InlineKeyboardButton("📢 إذاعة عامة", callback_data="admin_broadcast"),
        InlineKeyboardButton("➕ إضافة مالكين", callback_data="admin_add_owner"),
        InlineKeyboardButton("➕ إضافة مشرفين", callback_data="admin_add_admin"),
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")
    )
    text = "⚙️ لوحة التحكم العليا:"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

# =============================================================================
# Command Handlers
# =============================================================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    add_user(message.chat.id)
    welcome = (
        "مرحباً بك في البوت الاحترافي ! 🎉\n"
        "⚡️ نظام معالجة المعاملات التلقائي مستقر ويعمل بأعلى كفاءة.\n"
        "📑 يمكنك الآن إدارة حسابك، شحن رصيدك، أو طلب السحب فوراً بضغطة زر.\n"
        "🔘 يرجى اختيار العملية المطلوبة من القائمة أدناه:"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu_markup())


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if str(message.chat.id) not in owners_list:
        return
    show_admin_panel(message.chat.id)

# =============================================================================
# Back Button Handler
# =============================================================================
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع")
def handle_back(message):
    user_states.pop(message.chat.id, None)
    state_data.pop(message.chat.id, None)
    bot.send_message(
        message.chat.id,
        "🔙 تم العودة للقائمة الرئيسية.",
        reply_markup=main_menu_markup()
    )

# =============================================================================
# Main Menu Button Handlers
# =============================================================================
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def menu_my_account(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🆕 إنشاء حساب جديد", callback_data="create_account"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    bot.send_message(message.chat.id, "👤 إدارة حسابك:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "📥 إيداع / شحن رصيد")
def menu_deposit(message):
    user_states[message.chat.id] = "WAITING_DEP_AMOUNT"
    bot.send_message(
        message.chat.id,
        "💰 يرجى كتابة المبلغ المراد شحنه واضغط إرسال:",
        reply_markup=back_markup()
    )


@bot.message_handler(func=lambda m: m.text == "📩 سحب رصيد")
def menu_withdraw(message):
    text = (
        "⚠️ <b>تنبيه شروط السحب الفوري:</b>\n"
        "• يرجى العلم أنه سيتم خصم عمولة بقيمة <b>10%</b> تلقائياً من المبلغ المسحوب.\n"
        "• الحد الأدنى للسحب هو: <b>200,000</b> ليرة.\n"
        "• الحد الأعلى للسحب هو: <b>1,000,000</b> ليرة."
    )
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💳 محفظة شام كاش", callback_data="wd_method:sham"),
        InlineKeyboardButton("📱 سيرياتيل كاش", callback_data="wd_method:syriatel"),
        InlineKeyboardButton("🔙 رجوع", callback_data="wd_back")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")


@bot.message_handler(func=lambda m: m.text == "📞 الدعم الفني")
def menu_support(message):
    user_states[message.chat.id] = "WAITING_SUPPORT_TICKET"
    bot.send_message(
        message.chat.id,
        "أنت بأمان، فريقنا موجود بجانبك على مدار الساعة فقط أخبرنا بمشكلتك:",
        reply_markup=back_markup()
    )

# =============================================================================
# State Handlers - Registration
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_REG_USERNAME")
def handle_reg_username(message):
    if message.text == "🔙 رجوع":
        return
    username = message.text.strip()
    if not username or len(username) < 3:
        bot.send_message(message.chat.id, "❌ اسم المستخدم قصير جداً.")
        return
    state_data[message.chat.id] = {"username": username}
    user_states[message.chat.id] = "WAITING_REG_PASSWORD"
    bot.send_message(message.chat.id, "🔒 يرجى إرسال كلمة المرور:", reply_markup=back_markup())


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_REG_PASSWORD")
def handle_reg_password(message):
    if message.text == "🔙 رجوع":
        return
    password = message.text.strip()
    if not password or len(password) < 4:
        bot.send_message(message.chat.id, "❌ كلمة المرور قصيرة جداً.")
        return

    username = state_data.get(message.chat.id, {}).get("username")
    if not username:
        bot.send_message(message.chat.id, "❌ خطأ في البيانات. أعد المحاولة.")
        return

    if not agent_affiliate_id:
        get_agent_affiliate_id()

    payload = {
        "player": {
            "email": f"{username}@player.bot",
            "password": password,
            "parentId": agent_affiliate_id or "0",
            "login": username
        }
    }

    result = api_request("POST", "global/api/UserApi/registerPlayer", payload, auth=True)

    if result and result.get("status") and result.get("result") is not False:
        search_payload = {
            "start": 0,
            "limit": 20,
            "filter": {
                "withoutTotalCount": {"action": "=", "value": True},
                "userName": {"action": "=", "value": username, "valueLabel": username}
            },
            "isNextPage": False
        }
        search_result = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", search_payload, auth=True)
        player_id = None
        currency = "EUR"
        if search_result and search_result.get("result") and search_result["result"].get("records"):
            player = search_result["result"]["records"][0]
            player_id = str(player.get("playerId"))
            currency = player.get("currency", "EUR")

        if player_id:
            players_db[str(message.chat.id)] = {
                "player_id": player_id,
                "username": username,
                "currency": currency
            }
            save_players_db(players_db)
            bot.send_message(
                message.chat.id,
                f"✅ تم إنشاء الحساب بنجاح!\n🆔 معرف اللاعب: {player_id}\n💰 العملة: {currency}",
                reply_markup=main_menu_markup()
            )
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ تم إنشاء الحساب لكن لم يتم العثور على المعرف. حاول لاحقاً.",
                reply_markup=main_menu_markup()
            )
    else:
        error_msg = "Unknown error"
        if result and result.get("notification"):
            error_msg = result["notification"][0].get("content", "Unknown error")
        bot.send_message(message.chat.id, f"❌ فشل في إنشاء الحساب: {error_msg}")

    user_states.pop(message.chat.id, None)
    state_data.pop(message.chat.id, None)

# =============================================================================
# State Handlers - Deposit
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_DEP_AMOUNT")
def handle_dep_amount(message):
    if message.text == "🔙 رجوع":
        return
    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount <= 0:
            raise ValueError
        state_data[message.chat.id] = {"amount": amount}
        user_states[message.chat.id] = "WAITING_DEP_RECEIPT"
        text = (
            f"💳 <b>خيارات الدفع المتاحة لشحن حسابك حياً:</b>\n"
            f"• <b>محفظة شام كاش</b>: {SHAM_CASH_WALLET}\n"
            f"• <b>كود سيرياتيل كاش</b>: {SYRIATEL_CASH_CODE}\n\n"
            f"⚠️ قم بتحويل المبلغ المطابق تماماً لطلبك، ثم <b>قم برفع وإرسال صورة إيصال التحويل (الوصل المالي)</b> هنا كصورة فوراً لتمريرها للإدارة والتدقيق:"
        )
        bot.send_message(message.chat.id, text, reply_markup=back_markup(), parse_mode="HTML")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح (رقم فقط).")


@bot.message_handler(content_types=["photo"], func=lambda m: user_states.get(m.chat.id) == "WAITING_DEP_RECEIPT")
def handle_dep_receipt_photo(message):
    amount = state_data.get(message.chat.id, {}).get("amount")
    if not amount:
        return

    photo_file_id = message.photo[-1].file_id
    caption = (
        f"📥 طلب إيداع جديد\n"
        f"👤 المستخدم: {message.from_user.id}\n"
        f"💰 المبلغ: {amount}\n"
        f"⏰ الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ اعتماد وشحن", callback_data="approve_dep"),
        InlineKeyboardButton("❌ رفض الإيصال", callback_data="reject_dep")
    )

    sent = bot.send_photo(ADMIN_GROUP_ID, photo_file_id, caption=caption, reply_markup=markup)
    pending_deposits[sent.message_id] = {
        "user_id": message.chat.id,
        "amount": amount
    }

    bot.send_message(
        message.chat.id,
        "⏳ تم إرسال طلبك للإدارة. سيتم مراجعته في أقرب وقت.",
        reply_markup=main_menu_markup()
    )
    user_states.pop(message.chat.id, None)
    state_data.pop(message.chat.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_DEP_RECEIPT")
def handle_dep_receipt_nonphoto(message):
    bot.send_message(message.chat.id, "❌ يرجى إرسال صورة الإيصال كصورة (ليس كملف أو نص).")

# =============================================================================
# State Handlers - Withdraw
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_WITHDRAW_AMOUNT")
def handle_wd_amount(message):
    if message.text == "🔙 رجوع":
        return
    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount < 200000 or amount > 1000000:
            bot.send_message(
                message.chat.id,
                "❌ المبلغ يجب أن يكون بين 200,000 و 1,000,000 ليرة."
            )
            return
        state_data[message.chat.id]["amount"] = amount
        method = state_data[message.chat.id]["method"]
        if method == "sham":
            bot.send_message(
                message.chat.id,
                "💳 يرجى إرسال عنوان محفظة شام كاش الخاصة بك:",
                reply_markup=back_markup()
            )
        else:
            bot.send_message(
                message.chat.id,
                "📱 يرجى إرسال رقم هاتفك المرتبط بسيرياتيل كاش:",
                reply_markup=back_markup()
            )
        user_states[message.chat.id] = "WAITING_WITHDRAW_ACCOUNT"
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح.")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_WITHDRAW_ACCOUNT")
def handle_wd_account(message):
    if message.text == "🔙 رجوع":
        return

    account = message.text.strip()
    data = state_data.get(message.chat.id, {})
    amount = data.get("amount", 0)
    method = data.get("method", "")

    net_amount = amount * 0.9
    data["account"] = account
    data["net_amount"] = net_amount
    state_data[message.chat.id] = data

    method_name = "محفظة شام كاش" if method == "sham" else "سيرياتيل كاش"

    bot.send_message(
        message.chat.id,
        "⏱️ تم تقديم طلب السحب بنجاح وجارٍ مراجعته وتحويل الأموال من قبل الإدارة...",
        reply_markup=main_menu_markup()
    )

    caption = (
        f"📩 طلب سحب جديد\n\n"
        f"👤 اللاعب: {message.from_user.first_name}\n"
        f"🆔 معرف التليجرام: {message.from_user.id}\n"
        f"💰 المبلغ المطلوب: {amount:,.0f} ليرة\n"
        f"📲 وسيلة الاستلام: {method_name}\n"
        f"🔢 تفاصيل الحساب: {account}\n"
        f"💵 المبلغ الصافي للتحويل: {net_amount:,.0f} ليرة"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ تم التحويل والخصم", callback_data="approve_wd"),
        InlineKeyboardButton("❌ رفض السحب", callback_data="reject_wd")
    )

    sent = bot.send_message(ADMIN_GROUP_ID, caption, reply_markup=markup)
    pending_withdrawals[sent.message_id] = {
        "user_id": message.chat.id,
        "amount": amount,
        "method": method,
        "account": account,
        "net_amount": net_amount
    }

    user_states.pop(message.chat.id, None)
    state_data.pop(message.chat.id, None)

# =============================================================================
# State Handlers - Support
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_SUPPORT_TICKET")
def handle_support_ticket(message):
    if message.text == "🔙 رجوع":
        return

    user = message.from_user
    admin_msg = (
        f"📞 تذكرة دعم فني جديدة\n\n"
        f"👤 من: {user.first_name} (@{user.username or 'لا يوجد'})\n"
        f"🆔 المعرف: {user.id}\n"
        f"📝 المشكلة:\n{message.text}"
    )

    sent = bot.send_message(ADMIN_GROUP_ID, admin_msg)
    support_tickets[sent.message_id] = message.chat.id

    bot.send_message(
        message.chat.id,
        "✅ تم إرسال تذكرتك للدعم الفني. سنرد عليك في أقرب وقت.",
        reply_markup=main_menu_markup()
    )
    user_states.pop(message.chat.id, None)

# =============================================================================
# Admin State Handler
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) and str(m.chat.id) in owners_list and user_states.get(m.chat.id).startswith("WAITING_ADMIN_"))
def handle_admin_states(message):
    state = user_states.get(message.chat.id)

    if state == "WAITING_ADMIN_AGENT_USERNAME":
        global AGENT_USERNAME
        AGENT_USERNAME = message.text.strip()
        bot.send_message(message.chat.id, f"✅ تم تحديث اسم المستخدم: {AGENT_USERNAME}\nجاري إعادة تسجيل الدخول...")
        if do_signin():
            get_agent_affiliate_id()
            bot.send_message(message.chat.id, "✅ تم تسجيل الدخول بالبيانات الجديدة.")
        else:
            bot.send_message(message.chat.id, "❌ فشل تسجيل الدخول. تحقق من البيانات.")
        user_states.pop(message.chat.id, None)

    elif state == "WAITING_ADMIN_AGENT_PASSWORD":
        global AGENT_PASSWORD
        AGENT_PASSWORD = message.text.strip()
        bot.send_message(message.chat.id, "✅ تم تحديث كلمة المرور.\nجاري إعادة تسجيل الدخول...")
        if do_signin():
            bot.send_message(message.chat.id, "✅ تم تسجيل الدخول بالبيانات الجديدة.")
        else:
            bot.send_message(message.chat.id, "❌ فشل تسجيل الدخول.")
        user_states.pop(message.chat.id, None)

    elif state == "WAITING_ADMIN_SHAM_WALLET":
        global SHAM_CASH_WALLET
        SHAM_CASH_WALLET = message.text.strip()
        bot.send_message(message.chat.id, "✅ تم تحديث محفظة شام كاش.")
        user_states.pop(message.chat.id, None)

    elif state == "WAITING_ADMIN_SYRIATEL_CODE":
        global SYRIATEL_CASH_CODE
        SYRIATEL_CASH_CODE = message.text.strip()
        bot.send_message(message.chat.id, "✅ تم تحديث كود سيرياتيل كاش.")
        user_states.pop(message.chat.id, None)

    elif state == "WAITING_ADMIN_BROADCAST":
        text = message.text
        count = 0
        for uid in users_list:
            try:
                bot.send_message(int(uid), f"📢 إذاعة عامة:\n\n{text}")
                count += 1
            except Exception as e:
                logger.error(f"Broadcast failed to {uid}: {e}")
        bot.send_message(message.chat.id, f"✅ تم الإرسال لـ {count} مستخدم.")
        user_states.pop(message.chat.id, None)

    elif state == "WAITING_ADMIN_ADD_OWNER":
        try:
            new_owner = str(int(message.text.strip()))
            if new_owner not in owners_list:
                owners_list.append(new_owner)
                save_list_to_file(OWNERS_FILE, owners_list)
                bot.send_message(message.chat.id, f"✅ تم إضافة المالك: {new_owner}")
            else:
                bot.send_message(message.chat.id, "⚠️ المالك موجود مسبقاً.")
        except ValueError:
            bot.send_message(message.chat.id, "❌ معرف غير صالح.")
        user_states.pop(message.chat.id, None)

    elif state == "WAITING_ADMIN_ADD_ADMIN":
        try:
            new_admin = str(int(message.text.strip()))
            if new_admin not in admins_list:
                admins_list.append(new_admin)
                save_list_to_file(ADMINS_FILE, admins_list)
                bot.send_message(message.chat.id, f"✅ تم إضافة المشرف: {new_admin}")
            else:
                bot.send_message(message.chat.id, "⚠️ المشرف موجود مسبقاً.")
        except ValueError:
            bot.send_message(message.chat.id, "❌ معرف غير صالح.")
        user_states.pop(message.chat.id, None)

# =============================================================================
# Admin Group Reply Handler (Support)
# =============================================================================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message)
def handle_admin_group_reply(message):
    original_msg_id = message.reply_to_message.message_id
    if original_msg_id in support_tickets:
        user_id = support_tickets[original_msg_id]
        try:
            bot.send_message(user_id, f"📩 رد من الدعم الفني:\n\n{message.text}")
        except Exception as e:
            logger.error(f"Failed to send support reply to {user_id}: {e}")

# =============================================================================
# Callback Handlers - General Navigation
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def cb_back_to_main(call):
    bot.send_message(call.from_user.id, "🔙 تم العودة للقائمة الرئيسية.", reply_markup=main_menu_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "wd_back")
def cb_wd_back(call):
    bot.send_message(call.from_user.id, "🔙 تم العودة للقائمة الرئيسية.", reply_markup=main_menu_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "create_account")
def cb_create_account(call):
    user_states[call.from_user.id] = "WAITING_REG_USERNAME"
    bot.send_message(call.from_user.id, "📝 يرجى إرسال اسم المستخدم المطلوب:", reply_markup=back_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_method:"))
def cb_wd_method(call):
    method = call.data.split(":")[1]
    state_data[call.from_user.id] = {"method": method}
    user_states[call.from_user.id] = "WAITING_WITHDRAW_AMOUNT"
    bot.edit_message_text("💰 يرجى كتابة المبلغ المراد سحبه:", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# =============================================================================
# Callback Handlers - Admin Panel
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_") or call.data.startswith("edit_"))
def cb_admin_panel(call):
    if str(call.from_user.id) not in owners_list:
        bot.answer_callback_query(call.id, "⛔️ ليس لديك صلاحية!")
        return

    data = call.data

    if data == "admin_agent_data":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("تعديل اسم المستخدم", callback_data="edit_agent_username"),
            InlineKeyboardButton("تعديل كلمة المرور", callback_data="edit_agent_password"),
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_back_to_menu")
        )
        bot.edit_message_text("💼 اختر ما تريد تعديله:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif data == "edit_agent_username":
        user_states[call.from_user.id] = "WAITING_ADMIN_AGENT_USERNAME"
        bot.send_message(call.from_user.id, "📝 أرسل اسم المستخدم الجديد للوكيل:")
        bot.answer_callback_query(call.id)

    elif data == "edit_agent_password":
        user_states[call.from_user.id] = "WAITING_ADMIN_AGENT_PASSWORD"
        bot.send_message(call.from_user.id, "🔒 أرسل كلمة المرور الجديدة للوكيل:")
        bot.answer_callback_query(call.id)

    elif data == "admin_sham_wallet":
        user_states[call.from_user.id] = "WAITING_ADMIN_SHAM_WALLET"
        bot.send_message(call.from_user.id, "💰 أرسل عنوان محفظة شام كاش الجديد:")
        bot.answer_callback_query(call.id)

    elif data == "admin_syriatel_code":
        user_states[call.from_user.id] = "WAITING_ADMIN_SYRIATEL_CODE"
        bot.send_message(call.from_user.id, "📱 أرسل كود سيرياتيل كاش الجديد:")
        bot.answer_callback_query(call.id)

    elif data == "admin_balance":
        result = api_request("POST", "global/api/UserApi/getAgentAllWallets", {}, auth=True)
        if result and result.get("status") and result.get("result"):
            balances = result["result"]
            text = "📊 أرصدة الخزنة الحالية:\n\n"
            for bal in balances:
                text += f"💵 {bal.get('currencyName', 'Unknown')} ({bal.get('currencyCode', 'N/A')}):\n"
                text += f"   الرصيد: {bal.get('balance', 0)}\n"
                text += f"   المتاح: {bal.get('availability', 0)}\n"
                text += f"   البونص: {bal.get('bonus', 0)}\n\n"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("❌ فشل في جلب الأرصدة.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif data == "admin_broadcast":
        user_states[call.from_user.id] = "WAITING_ADMIN_BROADCAST"
        bot.send_message(call.from_user.id, "📢 أرسل الرسالة التي تريد بثها للجميع:")
        bot.answer_callback_query(call.id)

    elif data == "admin_add_owner":
        user_states[call.from_user.id] = "WAITING_ADMIN_ADD_OWNER"
        bot.send_message(call.from_user.id, "➕ أرسل معرف المستخدم (User ID) للمالك الجديد:")
        bot.answer_callback_query(call.id)

    elif data == "admin_add_admin":
        user_states[call.from_user.id] = "WAITING_ADMIN_ADD_ADMIN"
        bot.send_message(call.from_user.id, "➕ أرسل معرف المستخدم (User ID) للمشرف الجديد:")
        bot.answer_callback_query(call.id)

    elif data == "admin_back":
        bot.send_message(call.from_user.id, "🔙 تم إغلاق لوحة التحكم.", reply_markup=main_menu_markup())
        bot.answer_callback_query(call.id)

    elif data == "admin_back_to_menu":
        show_admin_panel(call.from_user.id, call.message.message_id)
        bot.answer_callback_query(call.id)

# =============================================================================
# Callback Handlers - Deposit Approval / Rejection
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data in ["approve_dep", "reject_dep"])
def cb_deposit_action(call):
    msg_id = call.message.message_id
    if msg_id not in pending_deposits:
        bot.answer_callback_query(call.id, "❌ طلب غير موجود أو تم معالجته.")
        return

    dep = pending_deposits.pop(msg_id)
    user_id = dep["user_id"]
    amount = dep["amount"]

    if call.data == "approve_dep":
        player_info = players_db.get(str(user_id))
        if not player_info:
            bot.send_message(call.message.chat.id, f"❌ لم يتم العثور على ربط حساب اللاعب للمستخدم {user_id}")
            bot.answer_callback_query(call.id)
            return

        player_id = player_info["player_id"]
        currency = player_info.get("currency", "EUR")

        payload = {
            "amount": float(amount),
            "comment": f"Deposit via bot for user {user_id}",
            "playerId": player_id,
            "currencyCode": currency,
            "currency": currency,
            "moneyStatus": 5
        }

        if not access_token:
            do_signin()

        result = api_request("POST", "global/api/UserApi/depositToPlayer", payload, auth=True)
        if result and result.get("status"):
            try:
                bot.send_message(user_id, f"✅ تم اعتماد إيصالك وشحن رصيدك بمبلغ {amount} {currency} بنجاح!")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                new_caption = call.message.caption + "\n\n✅ تمت المعالجة: معتمد وشحن."
                bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"Failed to edit deposit message: {e}")
        else:
            error_msg = "Unknown error"
            if result and result.get("notification"):
                error_msg = result["notification"][0].get("content", "Unknown error")
            bot.send_message(call.message.chat.id, f"❌ فشل في الشحن: {error_msg}")
    else:
        try:
            bot.send_message(user_id, "❌ تم رفض إيصال الإيداع. يرجى التواصل مع الدعم الفني.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            new_caption = call.message.caption + "\n\n❌ تمت المعالجة: مرفوض."
            bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"Failed to edit deposit message: {e}")

    bot.answer_callback_query(call.id)

# =============================================================================
# Callback Handlers - Withdraw Approval / Rejection
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data in ["approve_wd", "reject_wd"])
def cb_withdraw_action(call):
    msg_id = call.message.message_id
    if msg_id not in pending_withdrawals:
        bot.answer_callback_query(call.id, "❌ طلب غير موجود أو تم معالجته.")
        return

    wd = pending_withdrawals.pop(msg_id)
    user_id = wd["user_id"]
    amount = wd["amount"]

    if call.data == "approve_wd":
        player_info = players_db.get(str(user_id))
        if not player_info:
            bot.send_message(call.message.chat.id, f"❌ لم يتم العثور على ربط حساب اللاعب للمستخدم {user_id}")
            bot.answer_callback_query(call.id)
            return

        player_id = player_info["player_id"]
        currency = player_info.get("currency", "EUR")

        payload = {
            "amount": -float(amount),
            "comment": f"Withdraw via bot for user {user_id}",
            "playerId": player_id,
            "currencyCode": currency,
            "currency": currency,
            "moneyStatus": 5
        }

        if not access_token:
            do_signin()

        result = api_request("POST", "global/api/UserApi/withdrawFromPlayer", payload, auth=True)
        if result and result.get("status"):
            try:
                bot.send_message(user_id, "✅ تمت عملية السحب بنجاح! تم خصم المبلغ من رصيدك.")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                new_text = call.message.text + "\n\n✅ تمت المعالجة: تم التحويل والخصم."
                bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
            except Exception as e:
                logger.error(f"Failed to edit withdraw message: {e}")
        else:
            error_msg = "Unknown error"
            if result and result.get("notification"):
                error_msg = result["notification"][0].get("content", "Unknown error")
            bot.send_message(call.message.chat.id, f"❌ فشل في الخصم: {error_msg}")
    else:
        try:
            bot.send_message(user_id, "❌ تم رفض طلب السحب. يرجى التواصل مع الدعم الفني.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            new_text = call.message.text + "\n\n❌ تمت المعالجة: مرفوض."
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"Failed to edit withdraw message: {e}")

    bot.answer_callback_query(call.id)

# =============================================================================
# Flask Webhook Routes
# =============================================================================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        abort(403)


@app.route("/")
def index():
    return "Bot is running!", 200


def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

# =============================================================================
# Main Entry Point
# =============================================================================
if __name__ == "__main__":
    load_owners()
    load_admins()
    load_users_list()

    if do_signin():
        get_agent_affiliate_id()

    refresh_thread = threading.Thread(target=token_refresh_loop, daemon=True)
    refresh_thread.start()

    set_webhook()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
