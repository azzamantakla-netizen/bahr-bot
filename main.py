import os
import json
import time
import string
import random
import threading
import telebot
from flask import Flask, request
import tls_client

# ==================== الإعدادات الأساسية والبيانات السرية ====================
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
ADMIN_GROUP_ID = -1003983996094

AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"

PANEL_BASE = "https://texas4win.com"
RENDER_URL = "https://onrender.com"
DB_FILE = "players_db.txt"

SHAM_CASH_WALLET = "a18758d5324eb7595d4463ca355ad221"
SYRIATEL_CASH_CODE = "481 22120"

access_token = None
refresh_token = None
user_steps = {}
pending_deposits = {}

global_bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# ==================== إدارة توكينات الـ API وأتمتة الجلسة ====================
def api_sign_in():
    global access_token, refresh_token
    try:
        session = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        url = f"{PANEL_BASE}/global/api/UserApi/signIn"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
        
        res = session.post(url, json=payload, headers=headers, timeout_seconds=6)
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("status") is True and "result" in res_data:
                access_token = res_data["result"].get("accessToken")
                refresh_token = res_data["result"].get("refreshToken")
                print("[🔑] تم توليد توكن الوصول بنجاح حاسم!", flush=True)
                return True
        print(f"[❌] فشل تسجيل الدخول للـ API: الرمز {res.status_code}", flush=True)
    except Exception as e:
        print(f"[❌] خطأ غير متوقع أثناء تفويض الـ API: {e}", flush=True)
    return False

def api_refresh_token_loop():
    global access_token, refresh_token
    while True:
        time.sleep(2700)
        if refresh_token:
            try:
                session = tls_client.Session(client_identifier="chrome_120")
                url = f"{PANEL_BASE}/global/api/UserApi/refreshToken"
                payload = {"refreshToken": refresh_token}
                res = session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout_seconds=6)
                if res.status_code == 200:
                    res_data = res.json()
                    if res_data.get("status") is True and "result" in res_data:
                        access_token = res_data["result"].get("accessToken")
                        refresh_token = res_data["result"].get("refreshToken")
                        print("[🔄] تم تجديد الجلسة تلقائياً!", flush=True)
                        continue
            except Exception as e:
                print(f"[⚠️] فشل التجديد التلقائي للتوكن: {e}", flush=True)
        api_sign_in()

threading.Thread(target=api_refresh_token_loop, daemon=True).start()

# ==================== خدمات ربط وتواصل الـ API للاعبين ====================
def api_register_player(username, password):
    global access_token
    if not access_token and not api_sign_in():
        return False, "جلسة العمل الحية غير مفوضة حالياً بسيرفر اللوحة."
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"{PANEL_BASE}/global/api/UserApi/registerPlayer"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}
        
        res = session.post(url, json=payload, headers=headers, timeout_seconds=5)
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("status") is True or res_data.get("result") == 1:
                return True, "نجاح"
            return False, res_data.get("notification", {}).get("content", "الاسم مستخدم أو المدخلات مرفوضة باللوحة.")
        return False, f"جدار حماية اللوحة رد بالرمز {res.status_code}"
    except Exception as e:
        return False, f"فشل الاتصال الفوري بـ الـ API: {e}"

def api_deposit_to_player(player_id, amount):
    global access_token
    if not access_token and not api_sign_in():
        return False
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"{PANEL_BASE}/global/api/UserApi/depositToPlayer"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "amount": float(amount),
            "comment": "تم الشحن سحابياً عبر بوت التدقيق والمطابقة السريعة",
            "affiliateId": int(player_id),
            "moneyStatus": 3,
            "currencyCode": "AMD"
        }
        res = session.post(url, json=payload, headers=headers, timeout_seconds=5)
        if res.status_code == 200 and res.json().get("status") is True:
            return True
    except Exception as e:
        print(f"[❌] خطأ حرج أثناء ضخ رصيد الإيداع للـ API: {e}", flush=True)
    return False

# ==================== إدارة الـ Webhook الخاص بالسيرفر ====================
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        global_bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

@app.route('/')
def home():
    return "🚀 BOT IS LIVE AND RUNNING 24/7 (FULL AUTOMATION MODE)"

# ==================== إدارة أوامر ومعالجات تفاعل البوت ====================
@global_bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in user_steps:
        del user_steps[uid]
    
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("👤 حسابي"))
    markup.add(telebot.types.KeyboardButton("📩 سحب رصيد"), telebot.types.KeyboardButton("📥 إيداع / شحن رصيد"))
    markup.add(telebot.types.KeyboardButton("📞 الدعم الفني"))
    
    welcome_text = (
        "👋 مرحباً بك في لوحة الكاشير السحابية الفورية! 🎉\n\n"
        "⚡️ نظام معالجة المعاملات التلقائي مستقر ويعمل بأعلى كفاءة.\n"
        "📑 يمكنك الآن إدارة حسابك، شحن رصيدك، أو طلب السحب فوراً بضغطة زر.\n\n"
        "🔘 *يرجى اختيار العملية المطلوبة من القائمة أدناه:*"
    )
    global_bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# 🌟 1. معالج خاص فقط بخطوات إدخال البيانات الممتدة لضمان عدم حظر القائمة الرئيسية
@global_bot.message_handler(func=lambda message: message.from_user.id in user_steps)
def active_steps_handler(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text.strip()
    state = user_steps[uid].get("state")
    
    if state == "WAITING_USERNAME":
        user_steps[uid]["username"] = text
        user_steps[uid]["state"] = "WAITING_PASSWORD"
        global_bot.send_message(chat_id, "🔑 يرجى إرسال كلمة المرور المطلوبة للحساب الجديد:")
        return
        
    elif state == "WAITING_PASSWORD":
        username = user_steps[uid]["username"]
        password = text
        del user_steps[uid]
        global_bot.send_message(chat_id, "⚡️ ...جارٍ إنشاء حسابك وتأكيده مع اللوحة عبر الـ API الرسمي")
        success, detail = api_register_player(username, password)
        if success:
            try:
                with open(DB_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"login": username, "password": password}) + "\n")
            except:
                pass
            global_bot.send_message(chat_id, f"✅ **تم إنشاء الحساب بنجاح سحابي كاسح ومطابق 100%!**\n\n👤 اسم المستخدم: `{username}`\n🔑 كلمة المرور: `{password}`", parse_mode="Markdown")
        else:
            global_bot.send_message(chat_id, f"⚠️ **فشل إنشاء الحساب**: {detail}")
        return
        
    elif state == "WAITING_DEP_ID":
        user_steps[uid]["player_id"] = text
        user_steps[uid]["state"] = "WAITING_DEP_AMOUNT"
        global_bot.send_message(chat_id, "💰 يرجى كتابة المبلغ المراد شحنه (بالرقم):")
        return
        
    elif state == "WAITING_DEP_AMOUNT":
        user_steps[uid]["amount"] = text
        user_steps[uid]["state"] = "WAITING_DEP_RECEIPT"
        
        payment_info = (
            f"💳 **خيارات الدفع المتاحة للشحن الحقيقي:**\n\n"
            f"🏷️ **محفظة شام كاش**:\n`{SHAM_CASH_WALLET}`\n\n"
            f"📱 **كود سيرياتيل كاش**:\n`{SYRIATEL_CASH_CODE}`\n\n"
            f"⚠️ قم بتحويل المبلغ المطابق تماماً لطلبك، ثم **قم برفع وإرسال صورة إيصال التحويل (الوصل المالي)** هنا كصورة فوراً لتمريرها للإدارة والتدقيق:"
        )
        global_bot.send_message(chat_id, payment_info, parse_mode="Markdown")
        return

# 🌟 2. معالج الأزرار الرئيسية للقائمة (منسق بـ if/elif صارم لمنع أي تداخل للأوامر)
@global_bot.message_handler(func=lambda message: True)
def main_menu_buttons(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text.strip()
    
    if text == "👤 حسابي":
        markup_inline = telebot.types.InlineKeyboardMarkup()
        markup_inline.add(telebot.types.InlineKeyboardButton("🆕 إنشاء حساب جديد", callback_data="start_reg"))
        global_bot.send_message(chat_id, "⚠️ اضغط على الزر أدناه لإنشاء حساب لاعب فوراً برابط مباشر:", reply_markup=markup_inline)
        
    elif text == "📥 إيداع / شحن رصيد":
        user_steps[uid] = {"state": "WAITING_DEP_ID"}
        global_bot.send_message(chat_id, "👤 يرجى إرسال معرف اللاعب الخاص بك الرقمي (`Player ID`) في اللوحة:")
        
    elif text == "📩 سحب رصيد":
        global_bot.send_message(chat_id, "📩 خيارات سحب الرصيد وتدقيق حساب اللاعبين قيد المراجعة الفنية بالـ API.")
        
