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
PANEL_BASE = "https://agents.texas4win.com"
RENDER_URL = "https://bahr-bot-c3ac.onrender.com"

AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"
SHAM_CASH_WALLET = "a18758d5324eb7595d4463ca355ad221"
SYRIATEL_CASH_CODE = "48122120"

OWNERS_FILE = "owners.txt"
ADMINS_FILE = "admins.txt"
USERS_FILE = "users.txt"
PLAYERS_DB_FILE = "players_db.json"

owners_list = []
admins_list = []
users_list = []

session = tls_client.Session(
    client_identifier="chrome_120",
    random_tls_extension_order=True
)
access_token = None
refresh_token = None
agent_affiliate_id = None

user_states = {}
state_data = {}
pending_deposits = {}
pending_withdrawals = {}
support_tickets = {}          # {msg_id_in_group: user_id}
active_support_replies = {}   # {admin_id: user_id}

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# =============================================================================
# File I/O
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
    logger.info(f"Owners loaded: {owners_list}")


def load_admins():
    global admins_list
    admins_list = load_list_from_file(ADMINS_FILE)
    logger.info(f"Admins loaded: {admins_list}")


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
    logger.info(f"API REQUEST: {method} {url} | auth={auth} | payload={json.dumps(payload, ensure_ascii=False)[:500]}")
    try:
        if method.upper() == "GET":
            response = session.get(url, headers=headers)
        else:
            response = session.post(url, headers=headers, json=payload)
        logger.info(f"API RESPONSE status: {response.status_code}")
        logger.info(f"API RESPONSE text: {response.text[:2000]}")
        try:
            data = response.json()
            logger.info(f"API RESPONSE json: {json.dumps(data, ensure_ascii=False)[:1000]}")
            return data
        except Exception as e:
            logger.error(f"Non-JSON response: {e}")
            return {"__raw__": response.text}
    except Exception as e:
        logger.error(f"API request error: {e}")
        return None


def do_signin():
    global access_token, refresh_token
    payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
    logger.info(f"Signing in with username: {AGENT_USERNAME}")
    result = api_request("POST", "global/api/UserApi/signIn", payload)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        access_token = result["result"].get("accessToken")
        refresh_token = result["result"].get("refreshToken")
        logger.info(f"Sign in OK. Token prefix: {access_token[:30] if access_token else 'None'}...")
        return True
    logger.error(f"Sign in failed: {result}")
    return False


def get_agent_affiliate_id():
    global agent_affiliate_id
    if not access_token:
        logger.warning("No access token, attempting signin first")
        if not do_signin():
            return None
    if access_token:
        jwt_data = decode_jwt_payload(access_token)
        logger.info(f"JWT keys: {list(jwt_data.keys())}")
        for key in ["affiliateId", "userId", "id", "sub", "affiliate_id"]:
            if key in jwt_data and jwt_data[key]:
                agent_affiliate_id = str(jwt_data[key])
                logger.info(f"Agent affiliateId from JWT ({key}): {agent_affiliate_id}")
                return agent_affiliate_id
    # Fallback: try to get from API
    result = api_request("POST", "global/api/UserApi/getChildren", {}, auth=True)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        agent_affiliate_id = str(result["result"].get("parentId", "0"))
        logger.info(f"Agent affiliateId from getChildren: {agent_affiliate_id}")
        return agent_affiliate_id
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
                logger.info("Token refreshed")
            else:
                logger.warning("Refresh failed, signing in again")
                do_signin()
        else:
            do_signin()

# =============================================================================
# Keyboard Markups
# =============================================================================
def main_menu_markup(user_id):
    is_owner = str(user_id) in owners_list
    logger.info(f"main_menu_markup user_id={user_id} is_owner={is_owner} owners={owners_list}")
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("👤 حسابي"),
        KeyboardButton("📥 إيداع / شحن رصيد"),
        KeyboardButton("📩 سحب رصيد"),
        KeyboardButton("📞 الدعم الفني")
    )
    if is_owner:
        markup.add(KeyboardButton("⚙️ لوحة التحكم"))
    return markup


def back_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔙 رجوع"))
    return markup

# =============================================================================
# Admin Panel
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
# Admin Group Reply Handler (REGISTERED FIRST)
# =============================================================================
@bot.message_handler(content_types=["text"], func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message is not None)
def handle_admin_group_reply(message):
    original_msg_id = message.reply_to_message.message_id
    logger.info(f"Admin reply detected. original_msg_id={original_msg_id}, tickets={list(support_tickets.keys())}")
    if original_msg_id in support_tickets:
        user_id = support_tickets[original_msg_id]
        try:
            bot.send_message(user_id, f"📩 رد من الدعم الفني:\n\n{message.text}")
            bot.send_message(ADMIN_GROUP_ID, f"✅ تم إرسال الرد للمستخدم {user_id}")
        except Exception as e:
            logger.error(f"Failed to send reply to {user_id}: {e}")
            bot.send_message(ADMIN_GROUP_ID, f"❌ فشل إرسال الرد للمستخدم {user_id}: {e}")
    else:
        logger.info(f"Reply msg {original_msg_id} not in support_tickets. Ignoring.")


@bot.message_handler(content_types=["text"], func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.from_user.id in active_support_replies)
def handle_admin_active_reply(message):
    user_id = active_support_replies.get(message.from_user.id)
    if not user_id:
        return
    try:
        bot.send_message(user_id, f"📩 رد من الدعم الفني:\n\n{message.text}")
        bot.send_message(ADMIN_GROUP_ID, f"✅ تم إرسال الرد للمستخدم {user_id}")
    except Exception as e:
        logger.error(f"Failed to send active reply to {user_id}: {e}")
        bot.send_message(ADMIN_GROUP_ID, f"❌ فشل إرسال الرد للمستخدم {user_id}: {e}")


@bot.message_handler(content_types=["text"], func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.text.strip() in ["تم", "done", "انهاء", "إنهاء", "stop", "خروج"])
def handle_admin_exit_reply_mode(message):
    admin_id = message.from_user.id
    if admin_id in active_support_replies:
        del active_support_replies[admin_id]
        bot.send_message(ADMIN_GROUP_ID, f"🔚 تم إنهاء وضع الرد للمشرف {admin_id}.")
    else:
        bot.send_message(ADMIN_GROUP_ID, "ℹ️ أنت لست في وضع الرد.")

# =============================================================================
# Commands
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
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu_markup(message.chat.id))


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if str(message.chat.id) not in owners_list:
        bot.send_message(message.chat.id, "⛔️ ليس لديك صلاحية الوصول.")
        return
    show_admin_panel(message.chat.id)

# =============================================================================
# Back Handler
# =============================================================================
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع")
def handle_back(message):
    user_states.pop(message.chat.id, None)
    state_data.pop(message.chat.id, None)
    bot.send_message(
        message.chat.id,
        "🔙 تم العودة للقائمة الرئيسية.",
        reply_markup=main_menu_markup(message.chat.id)
    )

# =============================================================================
# Main Menu Handlers
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


@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة التحكم")
def menu_admin_panel(message):
    if str(message.chat.id) not in owners_list:
        bot.send_message(message.chat.id, "⛔️ ليس لديك صلاحية الوصول.")
        return
    show_admin_panel(message.chat.id)

# =============================================================================
# State: Registration
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

    global agent_affiliate_id
    if not agent_affiliate_id:
        get_agent_affiliate_id()

    parent_id = agent_affiliate_id if agent_affiliate_id else "0"
    logger.info(f"Registering player. username={username}, parentId={parent_id}, token_exists={bool(access_token)}")

    payload = {
        "player": {
            "email": f"{username}@player.bot",
            "password": password,
            "parentId": parent_id,
            "login": username
        }
    }

    result = api_request("POST", "global/api/UserApi/registerPlayer", payload, auth=True)
    logger.info(f"registerPlayer result: {result}")

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
        logger.info(f"getPlayersForCurrentAgent result: {search_result}")

        player_id = None
        currency = "EUR"
        if search_result and search_result.get("result") and search_result["result"].get("records"):
            player = search_result["result"]["records"][0]
            player_id = str(player.get("playerId"))
            currency = player.get("currency", "EUR")
            logger.info(f"Player found: id={player_id}, currency={currency}")

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
                reply_markup=main_menu_markup(message.chat.id)
            )
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ تم إنشاء الحساب لكن لم يتم العثور على المعرف. حاول لاحقاً.",
                reply_markup=main_menu_markup(message.chat.id)
            )
    else:
        error_msg = "Unknown error"
        if result:
            notif = result.get("notification")
            if isinstance(notif, list) and len(notif) > 0:
                error_msg = notif[0].get("content", "Unknown error")
            elif isinstance(notif, dict):
                error_msg = notif.get("content", "Unknown error")
            if result.get("__raw__"):
                error_msg += f" | Raw: {result['__raw__'][:200]}"
        elif result is None:
            error_msg = "No response from server (network error)."
        logger.error(f"Registration failed for {username}: {result}")
        bot.send_message(message.chat.id, f"❌ فشل في إنشاء الحساب: {error_msg}")

    user_states.pop(message.chat.id, None)
    state_data.pop(message.chat.id, None)

# =============================================================================
# State: Deposit
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
            f"⚠️ قم بتحويل المبلغ المطابق تماماً لطلبك، ثم <b>قم برفع وإرسال صورة الإيصال هنا.</b>\n"
            f"✅ سيتم مراجعة إيصالك وشحن رصيدك خلال دقائق."
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=back_markup())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح.")


@bot.message_handler(content_types=["photo"], func=lambda m: user_states.get(m.chat.id) == "WAITING_DEP_RECEIPT")
def handle_dep_receipt(message):
    chat_id = message.chat.id
    amount = state_data.get(chat_id, {}).get("amount")
    if not amount:
        bot.send_message(chat_id, "❌ خطأ في البيانات. أعد المحاولة.")
        return

    file_id = message.photo[-1].file_id
    caption = (
        f"🔄 <b>طلب إيداع جديد</b>\n\n"
        f"👤 المستخدم: <code>{chat_id}</code>\n"
        f"💰 المبلغ: <b>{amount}</b>\n"
        f"📎 تم إرفاق إيصال الدفع."
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ موافقة", callback_data="approve_dep"),
        InlineKeyboardButton("❌ رفض", callback_data="reject_dep")
    )
    sent = bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
    pending_deposits[sent.message_id] = {"user_id": chat_id, "amount": amount}
    bot.send_message(chat_id, "📤 تم إرسال إيصالك للمراجعة. سيتم إشعارك بالنتيجة.", reply_markup=main_menu_markup(chat_id))
    user_states.pop(chat_id, None)
    state_data.pop(chat_id, None)

# =============================================================================
# State: Withdraw
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_WITHDRAW_AMOUNT")
def handle_wd_amount(message):
    if message.text == "🔙 رجوع":
        return
    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount < 200000:
            bot.send_message(message.chat.id, "❌ الحد الأدنى للسحب هو 200,000 ليرة.")
            return
        if amount > 1000000:
            bot.send_message(message.chat.id, "❌ الحد الأعلى للسحب هو 1,000,000 ليرة.")
            return
        state_data[message.chat.id]["amount"] = amount
        user_states[message.chat.id] = "WAITING_WITHDRAW_PHONE"
        bot.send_message(
            message.chat.id,
            "📱 يرجى إرسال رقم هاتفك (محفظة شام كاش أو سيرياتيل كاش):",
            reply_markup=back_markup()
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح.")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_WITHDRAW_PHONE")
def handle_wd_phone(message):
    if message.text == "🔙 رجوع":
        return
    phone = message.text.strip()
    if not phone:
        bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح.")
        return
    state_data[message.chat.id]["phone"] = phone
    user_states[message.chat.id] = "WAITING_WITHDRAW_CONFIRM"
    amount = state_data[message.chat.id].get("amount", 0)
    commission = amount * 0.10
    net = amount - commission
    text = (
        f"⚠️ <b>مراجعة طلب السحب:</b>\n\n"
        f"💰 المبلغ: {amount}\n"
        f"📉 العمولة (10%): {commission}\n"
        f"📨 الصافي: {net}\n"
        f"📱 الرقم: {phone}\n\n"
        f"✅ اضغط 'تأكيد' لإرسال الطلب."
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ تأكيد", callback_data="confirm_wd"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_wd")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")

# =============================================================================
# State: Support
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_SUPPORT_TICKET")
def handle_support_ticket(message):
    if message.text == "🔙 رجوع":
        return
    ticket_text = message.text.strip()
    if not ticket_text:
        bot.send_message(message.chat.id, "❌ يرجى كتابة نص الرسالة.")
        return
    caption = (
        f"📩 <b>تذكرة دعم فني جديدة</b>\n\n"
        f"👤 المستخدم: <code>{message.chat.id}</code>\n"
        f"📝 الرسالة:\n{ticket_text}"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📝 رد على هذا المستخدم", callback_data=f"reply_support:{message.chat.id}"))
    sent = bot.send_message(ADMIN_GROUP_ID, caption, reply_markup=markup, parse_mode="HTML")
    support_tickets[sent.message_id] = message.chat.id
    bot.send_message(message.chat.id, "✅ تم إرسال تذكرتك. سيتم الرد عليك قريباً.", reply_markup=main_menu_markup(message.chat.id))
    user_states.pop(message.chat.id, None)

# =============================================================================
# State: Admin Panel States
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_ADMIN_AGENT_USERNAME")
def handle_admin_agent_username(message):
    global AGENT_USERNAME
    AGENT_USERNAME = message.text.strip()
    bot.send_message(message.chat.id, f"✅ تم تحديث اسم المستخدم: {AGENT_USERNAME}")
    user_states.pop(message.chat.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_ADMIN_AGENT_PASSWORD")
def handle_admin_agent_password(message):
    global AGENT_PASSWORD
    AGENT_PASSWORD = message.text.strip()
    bot.send_message(message.chat.id, "🔒 تم تحديث كلمة المرور. جاري إعادة تسجيل الدخول...")
    if do_signin():
        get_agent_affiliate_id()
        bot.send_message(message.chat.id, "✅ تم إعادة تسجيل الدخول بنجاح.")
    else:
        bot.send_message(message.chat.id, "❌ فشل إعادة تسجيل الدخول. تحقق من البيانات.")
    user_states.pop(message.chat.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_ADMIN_SHAM_WALLET")
def handle_admin_sham_wallet(message):
    global SHAM_CASH_WALLET
    SHAM_CASH_WALLET = message.text.strip()
    bot.send_message(message.chat.id, f"✅ تم تحديث محفظة شام كاش: {SHAM_CASH_WALLET}")
    user_states.pop(message.chat.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_ADMIN_SYRIATEL_CODE")
def handle_admin_syriatel_code(message):
    global SYRIATEL_CASH_CODE
    SYRIATEL_CASH_CODE = message.text.strip()
    bot.send_message(message.chat.id, f"✅ تم تحديث كود سيرياتيل: {SYRIATEL_CASH_CODE}")
    user_states.pop(message.chat.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_ADMIN_BROADCAST")
def handle_admin_broadcast(message):
    text = message.text
    success = 0
    failed = 0
    for uid in users_list:
        try:
            bot.send_message(int(uid), f"📢 إذاعة:\n\n{text}")
            success += 1
        except Exception as e:
            logger.error(f"Broadcast failed for {uid}: {e}")
            failed += 1
    bot.send_message(message.chat.id, f"✅ تم الإرسال: {success} | ❌ فشل: {failed}")
    user_states.pop(message.chat.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_ADMIN_ADD_OWNER")
def handle_admin_add_owner(message):
    uid = message.text.strip()
    if uid not in owners_list:
        owners_list.append(uid)
        save_list_to_file(OWNERS_FILE, owners_list)
    bot.send_message(message.chat.id, f"✅ تمت إضافة المالك: {uid}")
    user_states.pop(message.chat.id, None)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "WAITING_ADMIN_ADD_ADMIN")
def handle_admin_add_admin(message):
    uid = message.text.strip()
    if uid not in admins_list:
        admins_list.append(uid)
        save_list_to_file(ADMINS_FILE, admins_list)
    bot.send_message(message.chat.id, f"✅ تمت إضافة المشرف: {uid}")
    user_states.pop(message.chat.id, None)

# =============================================================================
# Callbacks - Main Menu / Back
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def cb_back_to_main(call):
    bot.send_message(call.from_user.id, "🔙 تم العودة للقائمة الرئيسية.", reply_markup=main_menu_markup(call.from_user.id))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data in ["wd_back", "cancel_wd"])
def cb_wd_back(call):
    bot.send_message(call.from_user.id, "🔙 تم العودة للقائمة الرئيسية.", reply_markup=main_menu_markup(call.from_user.id))
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


@bot.callback_query_handler(func=lambda call: call.data == "confirm_wd")
def cb_confirm_wd(call):
    chat_id = call.from_user.id
    data = state_data.get(chat_id, {})
    amount = data.get("amount", 0)
    phone = data.get("phone", "")
    method = data.get("method", "")
    method_name = "شام كاش" if method == "sham" else "سيرياتيل كاش"
    commission = amount * 0.10
    net = amount - commission
    caption = (
        f"📤 <b>طلب سحب جديد</b>\n\n"
        f"👤 المستخدم: <code>{chat_id}</code>\n"
        f"💰 المبلغ: {amount}\n"
        f"📉 العمولة: {commission}\n"
        f"📨 الصافي: {net}\n"
        f"📱 الرقم: {phone}\n"
        f"💳 الطريقة: {method_name}"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ موافقة", callback_data="approve_wd"),
        InlineKeyboardButton("❌ رفض", callback_data="reject_wd")
    )
    sent = bot.send_message(ADMIN_GROUP_ID, caption, reply_markup=markup, parse_mode="HTML")
    pending_withdrawals[sent.message_id] = {"user_id": chat_id, "amount": amount}
    bot.send_message(chat_id, "📤 تم إرسال طلب السحب للمراجعة.", reply_markup=main_menu_markup(chat_id))
    bot.answer_callback_query(call.id)
    user_states.pop(chat_id, None)
    state_data.pop(chat_id, None)

# =============================================================================
# Callbacks - Support Reply
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_support:"))
def cb_reply_support(call):
    user_id = int(call.data.split(":")[1])
    admin_id = call.from_user.id
    active_support_replies[admin_id] = user_id
    bot.send_message(
        ADMIN_GROUP_ID,
        f"📝 المشرف {admin_id} دخل وضع الرد على المستخدم {user_id}.\n"
        f"✍️ اكتب أي رسالة الآن وسيتم إرسالها مباشرة للمستخدم.\n"
        f"🔚 اكتب 'تم' أو 'done' أو 'إنهاء' للخروج من وضع الرد."
    )
    bot.answer_callback_query(call.id)

# =============================================================================
# Callbacks - Admin Panel
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
        bot.send_message(call.from_user.id, "🔙 تم إغلاق لوحة التحكم.", reply_markup=main_menu_markup(call.from_user.id))
        bot.answer_callback_query(call.id)

    elif data == "admin_back_to_menu":
        show_admin_panel(call.from_user.id, call.message.message_id)
        bot.answer_callback_query(call.id)

# =============================================================================
# Callbacks - Deposit Action
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
# Callbacks - Withdraw Action
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
# Flask Webhook
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
# Main
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
