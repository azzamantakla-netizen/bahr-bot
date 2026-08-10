import os
import json
import time
import threading
import logging
import base64
import random
import urllib.parse
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# =============================================================================
# المكتبة الأساسية لتخطي الحماية (تغني عن كافة المكتبات الأخرى وتخترق كلافلير)
# =============================================================================
try:
    from curl_cffi import requests as curl_requests
except ImportError:
    import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# =============================================================================
# الإعدادات والتهيئة الأساسية
# =============================================================================
BOT_TOKEN = "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE"
OWNER_ID = 6693251012
ADMIN_GROUP_ID = -1003983996094
PANEL_BASE = "https://texas4win.com"
RENDER_URL = "https://onrender.com"
AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"
SHAM_CASH_WALLET = "a18758d5324eb7595d4463ca355ad221"
SYRIATEL_CASH_CODE = "481 22120"
OWNERS_FILE = "owners.txt"
ADMINS_FILE = "admins.txt"
USERS_FILE = "users.txt"
PLAYERS_DB_FILE = "players_db.json"

owners_list, admins_list, users_list = [], [], []
user_states, state_data = {}, {}
pending_deposits, pending_withdrawals, support_tickets = {}, {}, {}
active_support_replies = {}

access_token, refresh_token = None, None
agent_affiliate_id = "2688288"
_signin_lock = threading.Lock()

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# =============================================================================
# مجمع البروكسيات المجاني التلقائي والذكي لحل مشكلة الـ IP
# =============================================================================
RESIDENTIAL_PROXY = os.environ.get("RESIDENTIAL_PROXY", "").strip()
_proxy_pool = []
_proxy_pool_lock = threading.Lock()
_proxy_pool_index = 0

PROXY_SOURCES = [
    "https://proxyscrape.com",
    "https://githubusercontent.com"
]

def _refresh_proxy_pool():
    global _proxy_pool
    all_proxies = set()
    for url in PROXY_SOURCES:
        try:
            resp = curl_requests.get(url, timeout=8, impersonate="chrome120" if hasattr(curl_requests, "Session") else None)
            if resp.status_code == 200:
                all_proxies.update([p.strip() for p in resp.text.splitlines() if ":" in p])
        except Exception:
            continue
    with _proxy_pool_lock:
        _proxy_pool = [{"http": f"http://{p}", "https": f"http://{p}"} for p in random.sample(list(all_proxies), min(len(all_proxies), 30))]
    logger.info(f"تم تحديث مجمع البروكسيات بنجاح. عدد البروكسيات الشغالة: {len(_proxy_pool)}")

def _proxy_refresh_loop():
    while True:
        try:
            _refresh_proxy_pool()
        except Exception as e:
            logger.error(f"خطأ في حلقة البروكسي: {e}")
        time.sleep(60)

def get_effective_proxy():
    global _proxy_pool_index
    if RESIDENTIAL_PROXY:
        p = RESIDENTIAL_PROXY if RESIDENTIAL_PROXY.startswith("http") else "http://" + RESIDENTIAL_PROXY
        return {"http": p, "https": p}
    with _proxy_pool_lock:
        if _proxy_pool:
            proxy = _proxy_pool[_proxy_pool_index % len(_proxy_pool)]
            _proxy_pool_index += 1
            return proxy
    return None

# =============================================================================
# إدارة الملفات وقاعدة البيانات والـ JWT
# =============================================================================
def load_list_from_file(filepath):
    return [line.strip() for line in open(filepath, "r", encoding="utf-8") if line.strip()] if os.path.exists(filepath) else []

def save_list_to_file(filepath, data_list):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data_list: f.write(str(item) + "\n")

def add_user(user_id):
    uid = str(user_id)
    if uid not in users_list:
        users_list.append(uid)
        with open(USERS_FILE, "a", encoding="utf-8") as f: f.write(uid + "\n")

def load_players_db():
    return json.load(open(PLAYERS_DB_FILE, "r", encoding="utf-8")) if os.path.exists(PLAYERS_DB_FILE) else {}

def save_players_db(data):
    json.dump(data, open(PLAYERS_DB_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

players_db = load_players_db()

def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
            return json.loads(base64.b64decode(payload))
    except Exception:
        pass
    return {}

# =============================================================================
# محرك الطلبات الموحد والفائق (خارج الصندوق لمواجهة Cloudflare)
# =============================================================================
def api_request(method, endpoint, payload=None, auth=False, add_delay=False):
    global access_token
    url = f"{PANEL_BASE}/{endpoint}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://texas4win.com",
        "Referer": "https://texas4win.com/"
    }
    
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
        
    if add_delay:
        time.sleep(random.uniform(2, 4)) # تأخير بشري تكيفي لمنع الحظر
        
    proxy = get_effective_proxy()
    
    # استخدام محاكاة المتصفح الفائقة ومقاومة الحظر عبر التراجع الذكي
    for attempt in range(3):
        try:
            # تدوير عشوائي لبيانات المتصفح لخداع كلافلير
            headers["User-Agent"] = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(118, 122)}.0.0.0 Safari/537.36"
            
            if hasattr(curl_requests, "Session"):
                sess = curl_requests.Session(impersonate="chrome120")
                req_func = sess.get if method.upper() == "GET" else sess.post
                resp = req_func(url, headers=headers, json=payload, timeout=20, proxies=proxy, verify=False)
                sess.close()
            else:
                req_func = curl_requests.get if method.upper() == "GET" else curl_requests.post
                resp = req_func(url, headers=headers, json=payload, timeout=20, proxies=proxy, verify=False)
                
            text = (resp.text or "").strip()
            if resp.status_code in (403, 429, 503) or "<html" in text.lower() or text.startswith("<"):
                logger.warning(f"تم رصد جدار حماية في المحاولة {attempt+1}، جاري تبديل الـ IP وإعادة المحاولة...")
                proxy = get_effective_proxy()
                time.sleep(2)
                continue
                
            if auth and resp.status_code in (401, 403):
                if do_signin():
                    headers["Authorization"] = f"Bearer {access_token}"
                    continue
                    
            return resp.json() if hasattr(resp, "json") else json.loads(text)
        except Exception as e:
            logger.error(f"خطأ في إرسال الطلب: {e}")
            proxy = get_effective_proxy()
            time.sleep(1)
            
    # الخيار السحابي الأخير عند تعطل كل شيء (AllOrigins Backup Gateway)
    try:
        encoded_url = urllib.parse.quote(url, safe='')
        gateway_url = f"https://allorigins.win{encoded_url}" if method.upper() == "GET" else f"https://allorigins.win{encoded_url}"
        r = curl_requests.post(gateway_url, headers=headers, json=payload, timeout=15, verify=False)
        return r.json()
    except Exception:
        return {"__raw__": "All layers failed"}

def do_signin():
    global access_token, refresh_token
    with _signin_lock:
        logger.info(f"جاري تسجيل دخول الوكيل بضمير: {AGENT_USERNAME}")
        res = api_request("POST", "global/api/UserApi/signIn", {"username": AGENT_USERNAME, "password": AGENT_PASSWORD})
        if res and isinstance(res, dict) and res.get("status") and isinstance(res.get("result"), dict):
            access_token = res["result"].get("accessToken")
            refresh_token = res["result"].get("refreshToken")
            return True
        logger.error("فشل تسجيل الدخول التلقائي للوكيل.")
        return False

def get_agent_affiliate_id():
    global agent_affiliate_id
    if not access_token and not do_signin(): return "2688288"
    jwt_data = decode_jwt_payload(access_token)
    for key in ["affiliateId", "userId", "id", "sub"]:
        if key in jwt_data and jwt_data[key]:
            agent_affiliate_id = str(jwt_data[key])
            return agent_affiliate_id
    return "2688288"

def token_refresh_loop():
    while True:
        time.sleep(30 * 60) # تحديث كل 30 دقيقة لضمان عدم الانقطاع
        do_signin()

# =============================================================================
# القوائم التفاعلية وأزرار البوت (تم تصحيح الترميز بالكامل)
# =============================================================================
def main_menu_markup(user_id):
    is_owner = str(user_id) == str(OWNER_ID) or str(user_id) in owners_list
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("👤 حسابي"), KeyboardButton("📥 إيداع / شحن رصيد"), KeyboardButton("📩 سحب رصيد"), KeyboardButton("📞 الدعم الفني"))
    if is_owner: markup.add(KeyboardButton("⚙️ لوحة التحكم"))
    return markup

def back_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔙 رجوع"))
    return markup
