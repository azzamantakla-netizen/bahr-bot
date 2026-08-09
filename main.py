import os
import json
import time
import threading
import logging
import base64
import random
import string
import asyncio
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# =============================================================================
# HTTP Clients (loaded gracefully)
# =============================================================================
try:
    import tls_client
except Exception:
    tls_client = None

try:
    import requests
except Exception:
    requests = None

try:
    from curl_cffi import requests as curl_cffi_requests
except Exception:
    curl_cffi_requests = None

try:
    import cloudscraper
except Exception:
    cloudscraper = None

try:
    import nodriver as uc
except Exception:
    uc = None

try:
    from seleniumbase import SB
except Exception:
    SB = None

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
SYRIATEL_CASH_CODE = "481 22120"

OWNERS_FILE = "owners.txt"
ADMINS_FILE = "admins.txt"
USERS_FILE = "users.txt"
PLAYERS_DB_FILE = "players_db.json"

owners_list = []
admins_list = []
users_list = []

# Lock to serialize signin attempts across threads
_signin_lock = threading.Lock()

# =============================================================================
# Dynamic Free Proxy Pool (auto-rotating, continuously refreshed)
# =============================================================================
RESIDENTIAL_PROXY = os.environ.get("RESIDENTIAL_PROXY", "").strip()

# ---- Proxy pool globals ----
_proxy_pool = []
_proxy_pool_lock = threading.Lock()
_proxy_pool_index = 0
_proxy_last_refresh = 0
_proxy_refresh_thread = None
_proxy_refresh_interval = 45  # seconds between refreshes

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]


def _fetch_proxy_sources():
    """Fetch fresh proxies from multiple free sources."""
    all_proxies = set()
    if not requests:
        logger.warning("requests module not available, cannot fetch proxies")
        return []
    for url in PROXY_SOURCES:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                lines = [p.strip() for p in resp.text.strip().splitlines() if p.strip() and ":" in p]
                all_proxies.update(lines)
                logger.info(f"Fetched {len(lines)} proxies from {url[:60]}...")
        except Exception as e:
            logger.warning(f"Proxy source failed {url[:60]}: {e}")
    proxies = list(all_proxies)
    logger.info(f"Total unique proxies fetched: {len(proxies)}")
    return proxies


def _test_proxy(proxy_str):
    """Quick health check: can the proxy reach the internet and the panel?"""
    if not requests:
        return False
    proxy_dict = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
    try:
        # Test 1: basic internet connectivity (very fast)
        r = requests.get(
            "http://httpbin.org/ip",
            proxies=proxy_dict,
            timeout=2,
            verify=False
        )
        if r.status_code != 200:
            return False
    except Exception:
        return False

    # Test 2: can it touch the panel without being blocked?
    try:
        r2 = requests.get(
            PANEL_BASE,
            proxies=proxy_dict,
            timeout=3,
            verify=False,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        if r2.status_code in (403, 429, 503):
            return False
        if "Cloudflare" in r2.text or "blocked" in r2.text.lower():
            return False
        return True
    except Exception:
        return False


def _refresh_proxy_pool():
    """Refresh the working proxy pool in background."""
    global _proxy_pool, _proxy_last_refresh
    proxies = _fetch_proxy_sources()
    if not proxies:
        logger.warning("No proxies fetched from any source")
        with _proxy_pool_lock:
            _proxy_pool = []
        return
    # Test a random sample (max 10 to keep it fast)
    test_candidates = random.sample(proxies, min(len(proxies), 10))
    working = []
    for proxy_str in test_candidates:
        if _test_proxy(proxy_str):
            working.append({"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"})
    with _proxy_pool_lock:
        _proxy_pool = working
        _proxy_last_refresh = time.time()
    logger.info(f"Proxy pool refreshed: {len(working)} working proxies out of {len(test_candidates)} tested")


def _proxy_refresh_loop():
    """Daemon thread that keeps the proxy pool hot and auto-updated."""
    while True:
        try:
            _refresh_proxy_pool()
        except Exception as e:
            logger.error(f"Proxy refresh loop error: {e}")
        time.sleep(_proxy_refresh_interval)


def _init_proxy_pool():
    """Start the background proxy refresh thread."""
    global _proxy_refresh_thread
    if _proxy_refresh_thread is None or not _proxy_refresh_thread.is_alive():
        _proxy_refresh_thread = threading.Thread(target=_proxy_refresh_loop, daemon=True)
        _proxy_refresh_thread.start()
        logger.info("Dynamic proxy refresh thread started (interval: 45s)")


def get_next_proxy():
    """Get next working proxy from the pool (round-robin)."""
    global _proxy_pool_index
    with _proxy_pool_lock:
        if not _proxy_pool:
            return None
        proxy = _proxy_pool[_proxy_pool_index % len(_proxy_pool)]
        _proxy_pool_index += 1
        return proxy


def get_effective_proxy():
    """
    Returns proxy dict for requests/curl_cffi.
    Priority: RESIDENTIAL_PROXY env var -> dynamic proxy pool -> direct connection.
    """
    if RESIDENTIAL_PROXY:
        proxy_url = RESIDENTIAL_PROXY
        if not proxy_url.startswith("http"):
            proxy_url = "http://" + proxy_url
        return {"http": proxy_url, "https": proxy_url}
    proxy = get_next_proxy()
    if proxy:
        return proxy
    return None


def get_working_proxy():
    """Legacy alias for get_effective_proxy."""
    return get_effective_proxy()

# =============================================================================
# curl_cffi Session (strongest for bypassing Cloudflare)
# =============================================================================
curl_session = None
if curl_cffi_requests:
    try:
        curl_session = curl_cffi_requests.Session(impersonate="chrome120")
        logger.info("curl_cffi session created successfully")
    except Exception as e:
        logger.warning(f"curl_cffi Session failed: {e}")
        curl_session = None

# =============================================================================
# cloudscraper fallback
# =============================================================================
cloud_scraper = None
if cloudscraper:
    try:
        cloud_scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        logger.info("cloudscraper created successfully")
    except Exception as e:
        logger.warning(f"cloudscraper failed: {e}")
        cloud_scraper = None

# =============================================================================
# tls_client fallback
# =============================================================================
session = None
if tls_client:
    try:
        session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"tls_client Session failed: {e}")
        session = None

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
    logger.info(f"Users list loaded: {len(users_list)} users")


def add_user(user_id):
    uid = str(user_id)
    if uid not in users_list:
        users_list.append(uid)
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(uid + "\n")
        logger.info(f"New user added: {uid}")


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


# =============================================================================
# HTTP Request Layers (ordered by strength)
# =============================================================================
class FakeResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def _request_with_curl_cffi(url, headers, payload, method):
    """Layer 1: curl_cffi with JA3 fingerprint + auto-rotating free proxy"""
    if not curl_cffi_requests:
        return None
    proxy = get_effective_proxy()
    try:
        sess = curl_cffi_requests.Session(impersonate="chrome120")
        proxies = proxy
        if proxy:
            logger.info(f"curl_cffi using proxy: {proxy}")
        if method.upper() == "GET":
            resp = sess.get(url, headers=headers, json=payload, timeout=45, verify=False, proxies=proxies)
        else:
            resp = sess.post(url, headers=headers, json=payload, timeout=45, verify=False, proxies=proxies)
        sess.close()
        return resp
    except Exception as e:
        logger.warning(f"curl_cffi request failed: {e}")
        return None


async def _request_with_nodriver_async(url, headers, payload, method):
    """Layer 2: Nodriver — real Chrome via CDP, executes fetch() in a blank page"""
    if not uc:
        return None
    try:
        browser = await uc.start()
        page = await browser.get('about:blank')
        header_json = json.dumps(headers)
        payload_json = json.dumps(payload) if payload else "null"
        script = f'''
            fetch("{url}", {{
                method: "{method}",
                headers: {header_json},
                body: {payload_json} ? JSON.stringify({payload_json}) : undefined
            }}).then(r => r.text())
        '''
        result = await page.evaluate(script)
        await browser.stop()
        return FakeResponse(result, 200)
    except Exception as e:
        logger.warning(f"nodriver request failed: {e}")
        return None


def _request_with_nodriver(url, headers, payload, method):
    try:
        return asyncio.run(_request_with_nodriver_async(url, headers, payload, method))
    except Exception as e:
        logger.warning(f"nodriver sync wrapper failed: {e}")
        return None


def _request_with_seleniumbase(url, headers, payload, method):
    """Layer 3: SeleniumBase UC Mode — undetected Chrome with fetch() execution"""
    if not SB:
        return None
    try:
        header_json = json.dumps(headers)
        payload_json = json.dumps(payload) if payload else "null"
        script = f'''
            return fetch("{url}", {{
                method: "{method}",
                headers: {header_json},
                body: {payload_json} ? JSON.stringify({payload_json}) : undefined
            }}).then(r => r.text())
        '''
        with SB(uc=True, headless=True, demo=False) as sb:
            sb.open("about:blank")
            result = sb.execute_script(script)
            return FakeResponse(result, 200)
    except Exception as e:
        logger.warning(f"seleniumbase request failed: {e}")
        return None


def _request_with_cloudscraper(url, headers, payload, method):
    """Layer 4: cloudscraper"""
    if not cloud_scraper:
        return None
    proxy = get_effective_proxy()
    try:
        proxies = proxy if proxy else None
        if method.upper() == "GET":
            return cloud_scraper.get(url, headers=headers, json=payload, timeout=15, verify=False, proxies=proxies)
        else:
            return cloud_scraper.post(url, headers=headers, json=payload, timeout=15, verify=False, proxies=proxies)
    except Exception as e:
        logger.warning(f"cloudscraper request failed: {e}")
        return None


def _request_with_requests(url, headers, payload, method):
    """Layer 5: standard requests"""
    if not requests:
        return None
    proxy = get_effective_proxy()
    try:
        proxies = proxy if proxy else None
        if method.upper() == "GET":
            return requests.get(url, headers=headers, json=payload, timeout=15, verify=False, proxies=proxies)
        else:
            return requests.post(url, headers=headers, json=payload, timeout=15, verify=False, proxies=proxies)
    except Exception as e:
        logger.warning(f"requests fallback failed: {e}")
        return None


def _request_with_tls(url, headers, payload, method):
    """Layer 6: tls_client"""
    if not session:
        return None
    try:
        if method.upper() == "GET":
            return session.get(url, headers=headers, timeout_seconds=15)
        else:
            return session.post(url, headers=headers, json=payload, timeout_seconds=15)
    except Exception as e:
        logger.warning(f"tls_client request failed: {e}")
        return None


def _is_html_response(response):
    """Detect if a response body is HTML instead of expected JSON."""
    if not response:
        return False
    if isinstance(response, str):
        text = response.strip()
    elif hasattr(response, "text"):
        text = (response.text or "").strip()
    else:
        return False
    return (
        text.startswith("<")
        or "<html" in text.lower()
        or "<!doctype" in text.lower()
        or "<head" in text.lower()
    )


def _is_bad_response(response):
    """Detect if a response is unusable (HTML, empty body, or server error)."""
    if response is None:
        return True
    # Check for server errors (5xx) or empty body
    if hasattr(response, "status_code") and response.status_code >= 500:
        return True
    if hasattr(response, "text") and not (response.text or "").strip():
        return True
    return _is_html_response(response)


# =============================================================================
# Unified API Request
# =============================================================================
def api_request(method, endpoint, payload=None, auth=False, add_delay=False):
    url = f"{PANEL_BASE}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://agents.texas4win.com",
        "Referer": "https://agents.texas4win.com/"
    }
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    # Random delay to avoid bot detection (2-5 seconds)
    if add_delay:
        delay = random.uniform(2, 5)
        logger.info(f"Random delay: {delay:.2f}s before API request")
        time.sleep(delay)

    logger.info(f"API REQUEST: {method} {url} | auth={auth} | payload={json.dumps(payload, ensure_ascii=False)[:500]}")
    logger.info(f"RESIDENTIAL_PROXY set: {bool(RESIDENTIAL_PROXY)}")

    try:
        # Priority order:
        # 1. curl_cffi (JA3 fingerprint) + proxy
        # 2. nodriver (real Chrome CDP)
        # 3. seleniumbase UC Mode (undetected Chrome)
        # 4. cloudscraper
        # 5. requests
        # 6. tls_client
        response = _request_with_curl_cffi(url, headers, payload, method)
        if _is_bad_response(response):
            response = _request_with_nodriver(url, headers, payload, method)
        if _is_bad_response(response):
            response = _request_with_seleniumbase(url, headers, payload, method)
        if _is_bad_response(response):
            response = _request_with_cloudscraper(url, headers, payload, method)
        if _is_bad_response(response):
            response = _request_with_requests(url, headers, payload, method)
        if _is_bad_response(response):
            response = _request_with_tls(url, headers, payload, method)
        if _is_bad_response(response):
            raise Exception("All request methods failed (None, HTML, empty body, or server error)")

        # Auto-retry on auth failure
        if auth and response.status_code in (401, 403):
            logger.warning(f"Auth failed ({response.status_code}), attempting re-signin...")
            if do_signin():
                headers["Authorization"] = f"Bearer {access_token}"
                response = _request_with_curl_cffi(url, headers, payload, method)
                if _is_bad_response(response):
                    response = _request_with_nodriver(url, headers, payload, method)
                if _is_bad_response(response):
                    response = _request_with_seleniumbase(url, headers, payload, method)
                if _is_bad_response(response):
                    response = _request_with_cloudscraper(url, headers, payload, method)
                if _is_bad_response(response):
                    response = _request_with_requests(url, headers, payload, method)
                if _is_bad_response(response):
                    response = _request_with_tls(url, headers, payload, method)
                if _is_bad_response(response):
                    raise Exception("All request methods failed on retry (None, HTML, empty body, or server error)")
            else:
                logger.error("Re-signin failed after auth error.")

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
    with _signin_lock:
        payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
        logger.info(f"Signing in with username: {AGENT_USERNAME}")
        result = api_request("POST", "global/api/UserApi/signIn", payload)
        if result is None:
            logger.error("Sign in failed: API returned None (all clients failed or returned HTML)")
            return False
        if isinstance(result, dict) and result.get("__raw__"):
            raw_text = result["__raw__"]
            if _is_html_response(raw_text):
                logger.error(f"Sign in failed: API returned HTML instead of JSON (WAF/Cloudflare block detected). First 500 chars: {raw_text[:500]}")
            else:
                logger.error(f"Sign in failed: API returned non-JSON response: {raw_text[:500]}")
            return False
        if result and result.get("status") and isinstance(result.get("result"), dict):
            access_token = result["result"].get("accessToken")
            refresh_token = result["result"].get("refreshToken")
            logger.info(f"Sign in OK. Token prefix: {access_token[:30] if access_token else 'None'}...")
            return True
        logger.error(f"Sign in failed: unexpected result: {result}")
        return False


def get_agent_affiliate_id():
    global agent_affiliate_id
    # Hardcoded confirmed parentId
    HARDCODED_AFFILIATE_ID = "2688288"
    if not access_token:
        logger.warning("No access token, attempting signin first")
        if not do_signin():
            agent_affiliate_id = HARDCODED_AFFILIATE_ID
            return agent_affiliate_id
    if access_token:
        jwt_data = decode_jwt_payload(access_token)
        logger.info(f"JWT keys: {list(jwt_data.keys())}")
        for key in ["affiliateId", "userId", "id", "sub", "affiliate_id"]:
            if key in jwt_data and jwt_data[key]:
                val = str(jwt_data[key])
                if val == HARDCODED_AFFILIATE_ID:
                    agent_affiliate_id = val
                    logger.info(f"Agent affiliateId from JWT ({key}): {agent_affiliate_id}")
                    return agent_affiliate_id
    # Fallback 1: try to get from getChildren
    try:
        result = api_request("POST", "global/api/UserApi/getChildren", {}, auth=True)
        if result and result.get("status") and isinstance(result.get("result"), dict):
            val = str(result["result"].get("parentId", ""))
            if val and val != "0":
                agent_affiliate_id = val
                logger.info(f"Agent affiliateId from getChildren: {agent_affiliate_id}")
                return agent_affiliate_id
    except Exception as e:
        logger.error(f"getChildren error: {e}")
    # Fallback 2: try to get from first player in getPlayersForCurrentAgent
    try:
        search_payload = {
            "start": 0,
            "limit": 1,
            "filter": {},
            "isNextPage": False
        }
        players_result = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", search_payload, auth=True)
        logger.info(f"getPlayersForCurrentAgent affiliate fetch: {players_result}")
        if players_result and players_result.get("status") and isinstance(players_result.get("result"), dict):
            records = players_result["result"].get("records", [])
            if records and isinstance(records, list) and len(records) > 0:
                first_player = records[0]
                parent_id = first_player.get("parentId")
                if parent_id:
                    agent_affiliate_id = str(parent_id)
                    logger.info(f"Agent affiliateId from first player parentId: {agent_affiliate_id}")
                    return agent_affiliate_id
    except Exception as e:
        logger.error(f"Error fetching affiliate from players: {e}")
    # Final fallback: use hardcoded confirmed value
    agent_affiliate_id = HARDCODED_AFFILIATE_ID
    logger.info(f"Using hardcoded affiliateId: {agent_affiliate_id}")
    return agent_affiliate_id


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
    is_owner = str(user_id) == str(OWNER_ID) or str(user_id) in owners_list
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
        InlineKeyboardButton("📢 إذاعة للجميع", callback_data="admin_broadcast"),
        InlineKeyboardButton("➕ إضافة مالك", callback_data="admin_add_owner"),
        InlineKeyboardButton("➕ إضافة مشرف", callback_data="admin_add_admin"),
        InlineKeyboardButton("➖ إزالة مالك", callback_data="admin_remove_owner"),
        InlineKeyboardButton("➖ إزالة مشرف", callback_data="admin_remove_admin"),
        InlineKeyboardButton("🔙 إغلاق", callback_data="admin_back")
    )
    text = "⚙️ لوحة التحكم - اختر الإجراء:"
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        except Exception as e:
            logger.error(f"Failed to edit admin panel message: {e}")
    else:
        bot.send_message(chat_id, text, reply_markup=markup)


# =============================================================================
# Bot Handlers
# =============================================================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    add_user(uid)
    bot.send_message(
        uid,
        "🎰 مرحباً بك في بوت الكازينو!\n\n"
        "الرجاء اختيار أحد الخيارات من القائمة أدناه.",
        reply_markup=main_menu_markup(uid)
    )


@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def handle_account(message):
    uid = str(message.from_user.id)
    player = players_db.get(uid)
    if player:
        text = (
            f"👤 بيانات حسابك:\n\n"
            f"🆔 معرف اللاعب: {player.get('player_id')}\n"
            f"👤 اسم المستخدم: {player.get('username')}\n"
            f"📧 البريد: {player.get('email')}\n"
            f"💰 العملة: {player.get('currency', 'EUR')}\n\n"
            f"للتحقق من رصيدك، تواصل مع الدعم الفني."
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🗑️ حذف الحساب", callback_data="delete_account"))
        bot.send_message(message.from_user.id, text, reply_markup=markup)
    else:
        text = (
            "📝 ليس لديك حساب مسجل بعد.\n\n"
            "هل تريد إنشاء حساب جديد الآن؟"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ نعم، إنشاء حساب", callback_data="register_now"))
        bot.send_message(message.from_user.id, text, reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "📥 إيداع / شحن رصيد")
def handle_deposit(message):
    uid = message.from_user.id
    user_states[uid] = "WAITING_DEPOSIT_AMOUNT"
    state_data[uid] = {}
    text = (
        "💰 لإيداع رصيد، أرسل المبلغ المطلوب (رقماً فقط).\n\n"
        "مثال: 50"
    )
    bot.send_message(uid, text, reply_markup=back_markup())


@bot.message_handler(func=lambda m: m.text == "📩 سحب رصيد")
def handle_withdraw(message):
    uid = message.from_user.id
    user_states[uid] = "WAITING_WITHDRAW_AMOUNT"
    state_data[uid] = {}
    text = (
        "💸 لسحب رصيد، أرسل المبلغ المطلوب (رقماً فقط).\n\n"
        "مثال: 30"
    )
    bot.send_message(uid, text, reply_markup=back_markup())


@bot.message_handler(func=lambda m: m.text == "📞 الدعم الفني")
def handle_support(message):
    uid = message.from_user.id
    user_states[uid] = "WAITING_SUPPORT_MESSAGE"
    text = (
        "📞 الدعم الفني:\n\n"
        "أرسل رسالتك الآن وسيقوم فريق الدعم بالرد عليك في أقرب وقت."
    )
    bot.send_message(uid, text, reply_markup=back_markup())


@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة التحكم")
def handle_admin_panel(message):
    uid = str(message.from_user.id)
    if uid not in owners_list and uid != str(OWNER_ID):
        bot.send_message(message.from_user.id, "⛔️ ليس لديك صلاحية الوصول للوحة التحكم.")
        return
    show_admin_panel(message.from_user.id)


@bot.message_handler(func=lambda m: m.text == "🔙 رجوع")
def handle_back(message):
    uid = message.from_user.id
    user_states.pop(uid, None)
    state_data.pop(uid, None)
    bot.send_message(uid, "🔙 تم العودة للقائمة الرئيسية.", reply_markup=main_menu_markup(uid))


# =============================================================================
# State Handlers
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REGISTER_USERNAME")
def state_register_username(message):
    uid = message.from_user.id
    username = message.text.strip()
    if not username:
        bot.send_message(uid, "❌ اسم المستخدم فارغ. أرسل اسم مستخدم صالح:")
        return
    state_data[uid]["reg_username"] = username
    user_states[uid] = "WAITING_REGISTER_PASSWORD"
    bot.send_message(uid, "🔒 أرسل كلمة المرور الآن (أي طول مقبول):")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_REGISTER_PASSWORD")
def state_register_password(message):
    uid = message.from_user.id
    password = message.text.strip()
    if not password:
        bot.send_message(uid, "❌ كلمة المرور فارغة. أرسل كلمة مرور صالحة:")
        return

    username = state_data[uid].get("reg_username", "")
    if not username:
        bot.send_message(uid, "❌ حدث خطأ. ابدأ التسجيل من جديد.")
        user_states.pop(uid, None)
        return

    # Generate random email
    email = f"{username.lower()}{random.randint(1000,9999)}@gmail.com"
    first_name = username
    last_name = "Player"
    # Use agent affiliate id as integer parentId
    parent_id_val = int(agent_affiliate_id) if agent_affiliate_id else 2688288

    bot.send_message(uid, "⏳ جاري معالجة التسجيل...")

    payload = {
        "login": username,
        "email": email,
        "password": password,
        "parentId": parent_id_val,
        "firstName": first_name,
        "lastName": last_name
    }

    logger.info(f"REGISTER PAYLOAD: {json.dumps(payload, ensure_ascii=False)}")

    # auth=True is required so the player is created under the logged-in agent
    result = api_request("POST", "global/api/UserApi/registerPlayer", payload, auth=True, add_delay=True)

    logger.info(f"REGISTER RESULT type={type(result)} | content={json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)[:2000]}")

    if result is None:
        bot.send_message(uid, "❌ فشل الاتصال بالخادم. حاول مرة أخرى لاحقاً.")
        user_states.pop(uid, None)
        return

    # Check for Cloudflare/WAF HTML block
    raw_text = result.get("__raw__", "")
    if raw_text and (raw_text.strip().startswith("<") or "<html" in raw_text.lower()):
        logger.warning(f"Cloudflare/WAF HTML block detected during registration for user {uid}")
        bot.send_message(
            uid,
            "⚠️ تم حظر الطلب بواسطة جدار الحماية (Cloudflare).\n"
            "الحساب قد لا يكون قد تم إنشاؤه فعلياً.\n\n"
            "يرجى الانتظار قليلاً ثم المحاولة مرة أخرى."
        )
        user_states.pop(uid, None)
        return

    # Check for duplicate username
    if "DuplicateUserName" in raw_text or "already exists" in raw_text.lower() or "اسم المستخدم موجود" in raw_text:
        bot.send_message(uid, "❌ اسم المستخدم مستخدم بالفعل. ابدأ التسجيل باسم مختلف.")
        user_states.pop(uid, None)
        return

    # Check for empty or failed response (non-JSON, server error, etc.)
    if isinstance(result, dict) and "__raw__" in result:
        if not raw_text.strip():
            bot.send_message(
                uid,
                "❌ فشل في التسجيل: الخادم رد بخطأ داخلي (500) أو الرد فارغ.\n"
                "قد تكون المشكلة مؤقتة من طرف الخادم. يرجى المحاولة بعد قليل."
            )
        else:
            bot.send_message(
                uid,
                f"❌ فشل في التسجيل: رد غير متوقع من الخادم.\n\n"
                f"{raw_text[:800]}"
            )
        user_states.pop(uid, None)
        return

    if isinstance(result, dict) and result.get("status"):
        player_id = None
        result_data = result.get("result")
        if isinstance(result_data, dict):
            player_id = result_data.get("playerId") or result_data.get("id")
        elif isinstance(result_data, (int, str)):
            player_id = result_data

        if not player_id or str(player_id) in ("", "0", "None", "null"):
            bot.send_message(
                uid,
                f"❌ فشل في التسجيل: الرد لا يحتوي على معرف لاعب صالح.\n\n"
                f"رد الخادم: {json.dumps(result, ensure_ascii=False)[:800]}"
            )
            user_states.pop(uid, None)
            return

        # Verify player actually exists in agent panel
        bot.send_message(uid, "🔍 جاري التحقق من إنشاء الحساب في لوحة التحكم...")
        verify_payload = {
            "start": 0,
            "limit": 10,
            "filter": {"login": username},
            "isNextPage": False
        }
        verify_result = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", verify_payload, auth=True)
        logger.info(f"VERIFY RESULT for user {uid}: {json.dumps(verify_result, ensure_ascii=False) if isinstance(verify_result, dict) else str(verify_result)[:1000]}")

        verified = False
        if isinstance(verify_result, dict) and verify_result.get("status"):
            v_data = verify_result.get("result", {})
            if isinstance(v_data, dict):
                records = v_data.get("records", [])
                if isinstance(records, list):
                    for rec in records:
                        if isinstance(rec, dict) and rec.get("login") == username:
                            verified = True
                            break

        if not verified:
            bot.send_message(
                uid,
                "⚠️ تم استلام تأكيد من الخادم، لكن لم يتم العثور على الحساب في لوحة التحكم.\n"
                "قد يكون هناك مشكلة مؤقتة أو تأخير في التحديث.\n\n"
                "يرجى المحاولة مرة أخرى بعد بضع دقائق."
            )
            user_states.pop(uid, None)
            return

        players_db[str(uid)] = {
            "player_id": str(player_id),
            "username": username,
            "email": email,
            "currency": "EUR"
        }
        save_players_db(players_db)
        bot.send_message(
            uid,
            f"✅ تم إنشاء الحساب بنجاح!\n\n"
            f"👤 اسم المستخدم: {username}\n"
            f"📧 البريد: {email}\n"
            f"🆔 معرف اللاعب: {player_id}\n\n"
            f"يمكنك الآن الإيداع واللعب!",
            reply_markup=main_menu_markup(uid)
        )
    else:
        error_msg = "Unknown error"
        if result and isinstance(result, dict) and result.get("notification"):
            notif = result["notification"]
            if isinstance(notif, list) and len(notif) > 0:
                error_msg = notif[0].get("content", "Unknown error")
            elif isinstance(notif, dict):
                error_msg = notif.get("content", "Unknown error")
        elif raw_text:
            error_msg = raw_text[:800]
        bot.send_message(uid, f"❌ فشل في التسجيل: {error_msg}")

    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_DEPOSIT_AMOUNT")
def state_deposit_amount(message):
    uid = message.from_user.id
    text = message.text.strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        bot.send_message(uid, "❌ أرسل مبلغاً صالحاً (رقم فقط).")
        return

    state_data[uid]["deposit_amount"] = amount
    user_states[uid] = "WAITING_DEPOSIT_RECEIPT"
    bot.send_message(
        uid,
        f"💰 المبلغ: {amount}\n\n"
        f"📸 أرسل صورة الإيصال الآن (أو اضغط 🔙 للإلغاء).",
        reply_markup=back_markup()
    )


@bot.message_handler(content_types=["photo"], func=lambda m: user_states.get(m.from_user.id) == "WAITING_DEPOSIT_RECEIPT")
def state_deposit_receipt(message):
    uid = message.from_user.id
    amount = state_data[uid].get("deposit_amount", 0)
    file_id = message.photo[-1].file_id
    caption = (
        f"📥 طلب إيداع جديد\n\n"
        f"👤 المستخدم: {uid}\n"
        f"💰 المبلغ: {amount}\n\n"
        f"أوافق / أرفض؟"
    )
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ موافق", callback_data="approve_dep"),
        InlineKeyboardButton("❌ رفض", callback_data="reject_dep")
    )
    sent = bot.send_photo(ADMIN_GROUP_ID, file_id, caption=caption, reply_markup=markup)
    pending_deposits[sent.message_id] = {"user_id": uid, "amount": amount}
    bot.send_message(uid, "✅ تم إرسال الإيصال للمراجعة. سيتم إشعارك بالنتيجة.", reply_markup=main_menu_markup(uid))
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_WITHDRAW_AMOUNT")
def state_withdraw_amount(message):
    uid = message.from_user.id
    text = message.text.strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        bot.send_message(uid, "❌ أرسل مبلغاً صالحاً (رقم فقط).")
        return

    state_data[uid]["withdraw_amount"] = amount
    user_states[uid] = "WAITING_WITHDRAW_METHOD"
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💳 شام كاش", callback_data="wd_sham"),
        InlineKeyboardButton("📱 سيرياتيل كاش", callback_data="wd_syriatel")
    )
    bot.send_message(uid, "اختر طريقة السحب:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["wd_sham", "wd_syriatel"])
def cb_withdraw_method(call):
    uid = call.from_user.id
    method = "sham" if call.data == "wd_sham" else "syriatel"
    state_data[uid]["withdraw_method"] = method
    user_states[uid] = "WAITING_WITHDRAW_ACCOUNT"
    if method == "sham":
        bot.send_message(uid, "💳 أرسل رقم محفظة شام كاش:")
    else:
        bot.send_message(uid, "📱 أرسل رقم حساب سيرياتيل كاش:")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_WITHDRAW_ACCOUNT")
def state_withdraw_account(message):
    uid = message.from_user.id
    account = message.text.strip()
    if not account:
        bot.send_message(uid, "❌ الحساب فارغ. أرسل رقم صالح:")
        return

    amount = state_data[uid].get("withdraw_amount", 0)
    method = state_data[uid].get("withdraw_method", "")
    method_name = "شام كاش" if method == "sham" else "سيرياتيل كاش"

    text = (
        f"📩 طلب سحب جديد\n\n"
        f"👤 المستخدم: {uid}\n"
        f"💰 المبلغ: {amount}\n"
        f"💳 الطريقة: {method_name}\n"
        f"🔢 الحساب: {account}\n\n"
        f"أوافق / أرفض؟"
    )
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ موافق", callback_data="approve_wd"),
        InlineKeyboardButton("❌ رفض", callback_data="reject_wd")
    )
    sent = bot.send_message(ADMIN_GROUP_ID, text, reply_markup=markup)
    pending_withdrawals[sent.message_id] = {"user_id": uid, "amount": amount}
    bot.send_message(uid, "✅ تم إرسال طلب السحب للمراجعة.", reply_markup=main_menu_markup(uid))
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_SUPPORT_MESSAGE")
def state_support_message(message):
    uid = message.from_user.id
    text = message.text.strip()
    if not text:
        bot.send_message(uid, "❌ الرسالة فارغة. أرسل رسالة صالحة:")
        return

    # Forward to admin group
    forward_text = (
        f"📞 رسالة دعم فني جديدة\n\n"
        f"👤 من المستخدم: {uid}\n"
        f"💬 الرسالة:\n{text}\n\n"
        f"اضغط على الزر أدناه للرد."
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✍️ رد على المستخدم", callback_data=f"reply_support_{uid}"))
    sent = bot.send_message(ADMIN_GROUP_ID, forward_text, reply_markup=markup)
    support_tickets[sent.message_id] = uid
    bot.send_message(uid, "✅ تم إرسال رسالتك لفريق الدعم. سيتم الرد عليك قريباً.", reply_markup=main_menu_markup(uid))
    user_states.pop(uid, None)


# =============================================================================
# Admin State Handlers
# =============================================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_AGENT_USERNAME")
def state_admin_agent_username(message):
    uid = message.from_user.id
    global AGENT_USERNAME
    AGENT_USERNAME = message.text.strip()
    bot.send_message(uid, f"✅ تم تحديث اسم المستخدم للوكيل: {AGENT_USERNAME}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_AGENT_PASSWORD")
def state_admin_agent_password(message):
    uid = message.from_user.id
    global AGENT_PASSWORD
    AGENT_PASSWORD = message.text.strip()
    bot.send_message(uid, "✅ تم تحديث كلمة المرور للوكيل.")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_SHAM_WALLET")
def state_admin_sham_wallet(message):
    uid = message.from_user.id
    global SHAM_CASH_WALLET
    SHAM_CASH_WALLET = message.text.strip()
    bot.send_message(uid, f"✅ تم تحديث محفظة شام كاش: {SHAM_CASH_WALLET}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_SYRIATEL_CODE")
def state_admin_syriatel_code(message):
    uid = message.from_user.id
    global SYRIATEL_CASH_CODE
    SYRIATEL_CASH_CODE = message.text.strip()
    bot.send_message(uid, f"✅ تم تحديث كود سيرياتيل كاش: {SYRIATEL_CASH_CODE}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_BROADCAST")
def state_admin_broadcast(message):
    uid = message.from_user.id
    text = message.text.strip()
    if not text:
        bot.send_message(uid, "❌ الرسالة فارغة.")
        return
    count = 0
    for user_id in users_list:
        try:
            bot.send_message(int(user_id), f"📢 إذاعة:\n\n{text}")
            count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {user_id}: {e}")
    bot.send_message(uid, f"✅ تم إرسال الإذاعة إلى {count} مستخدم.")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_ADD_OWNER")
def state_admin_add_owner(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target in owners_list:
        bot.send_message(uid, "❌ المستخدم مالك بالفعل.")
    else:
        owners_list.append(target)
        save_list_to_file(OWNERS_FILE, owners_list)
        bot.send_message(uid, f"✅ تم إضافة المالك: {target}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_ADD_ADMIN")
def state_admin_add_admin(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target in admins_list:
        bot.send_message(uid, "❌ المستخدم مشرف بالفعل.")
    else:
        admins_list.append(target)
        save_list_to_file(ADMINS_FILE, admins_list)
        bot.send_message(uid, f"✅ تم إضافة المشرف: {target}")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_REMOVE_OWNER")
def state_admin_remove_owner(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target == str(OWNER_ID):
        bot.send_message(uid, "❌ لا يمكن إزالة المالك الأساسي.")
    elif target in owners_list:
        owners_list.remove(target)
        save_list_to_file(OWNERS_FILE, owners_list)
        bot.send_message(uid, f"✅ تم إزالة المالك: {target}")
    else:
        bot.send_message(uid, "❌ المستخدم ليس مالكاً.")
    user_states.pop(uid, None)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "WAITING_ADMIN_REMOVE_ADMIN")
def state_admin_remove_admin(message):
    uid = message.from_user.id
    target = message.text.strip()
    if target in admins_list:
        admins_list.remove(target)
        save_list_to_file(ADMINS_FILE, admins_list)
        bot.send_message(uid, f"✅ تم إزالة المشرف: {target}")
    else:
        bot.send_message(uid, "❌ المستخدم ليس مشرفاً.")
    user_states.pop(uid, None)


# =============================================================================
# Callbacks - Registration
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data == "register_now")
def cb_register_now(call):
    uid = call.from_user.id
    user_states[uid] = "WAITING_REGISTER_USERNAME"
    state_data[uid] = {}
    bot.send_message(uid, "👤 أرسل اسم المستخدم المطلوب (حروف إنجليزية وأرقام فقط):")
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "delete_account")
def cb_delete_account(call):
    uid = str(call.from_user.id)
    if uid in players_db:
        removed = players_db.pop(uid)
        save_players_db(players_db)
        bot.send_message(
            call.from_user.id,
            f"🗑️ تم حذف بيانات الحساب المحلية بنجاح.\n\n"
            f"👤 اسم المستخدم المحذوف: {removed.get('username', 'غير معروف')}\n\n"
            f"يمكنك الآن إنشاء حساب جديد إذا أردت."
        )
        bot.answer_callback_query(call.id, "✅ تم الحذف")
    else:
        bot.send_message(call.from_user.id, "❌ لا يوجد حساب مسجل لديك.")
        bot.answer_callback_query(call.id, "❌ لا يوجد حساب")


# =============================================================================
# Callbacks - Support Reply
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_support_"))
def cb_reply_support(call):
    uid = call.from_user.id
    target_uid = int(call.data.split("_")[-1])
    active_support_replies[uid] = target_uid
    bot.send_message(uid, f"✍️ أرسل رسالة الرد للمستخدم {target_uid} الآن:\n\n(ارسل 'إلغاء' للإلغاء)")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: active_support_replies.get(m.from_user.id))
def handle_support_reply(message):
    admin_id = message.from_user.id
    target_uid = active_support_replies.get(admin_id)
    text = message.text.strip()
    if text == "إلغاء":
        active_support_replies.pop(admin_id, None)
        bot.send_message(admin_id, "❌ تم إلغاء الرد.")
        return
    try:
        bot.send_message(target_uid, f"📩 رد من الدعم الفني:\n\n{text}")
        bot.send_message(admin_id, "✅ تم إرسال الرد.")
    except Exception as e:
        bot.send_message(admin_id, f"❌ فشل في إرسال الرد: {e}")
    active_support_replies.pop(admin_id, None)


# =============================================================================
# Callbacks - Admin Panel
# =============================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_") or call.data.startswith("edit_"))
def cb_admin_panel(call):
    uid = str(call.from_user.id)
    if uid not in owners_list and uid != str(OWNER_ID):
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

    elif data == "admin_remove_owner":
        user_states[call.from_user.id] = "WAITING_ADMIN_REMOVE_OWNER"
        current = "\n".join(owners_list) if owners_list else "(لا يوجد مالكين)"
        bot.send_message(call.from_user.id, f"➖ أرسل معرف المستخدم (User ID) للمالك المراد إزالته.\n\nالمالكين الحاليين:\n{current}")
        bot.answer_callback_query(call.id)

    elif data == "admin_remove_admin":
        user_states[call.from_user.id] = "WAITING_ADMIN_REMOVE_ADMIN"
        current = "\n".join(admins_list) if admins_list else "(لا يوجد مشرفين)"
        bot.send_message(call.from_user.id, f"➖ أرسل معرف المستخدم (User ID) للمشرف المراد إزالته.\n\nالمشرفين الحاليين:\n{current}")
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
    return "Bot is running! curl_cffi + Nodriver + SeleniumBase UC Mode enabled.", 200


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
def _init_background():
    """Background initialization: signin + affiliate ID fetch."""
    if do_signin():
        get_agent_affiliate_id()
    else:
        logger.error("Initial signin failed. API calls may fail until signin succeeds.")


if __name__ == "__main__":
    load_owners()
    load_admins()
    load_users_list()

    logger.info(f"RESIDENTIAL_PROXY env: {'SET' if RESIDENTIAL_PROXY else 'NOT SET'}")
    logger.info(f"curl_cffi available: {bool(curl_cffi_requests)}")
    logger.info(f"nodriver available: {bool(uc)}")
    logger.info(f"seleniumbase available: {bool(SB)}")
    logger.info(f"cloudscraper available: {bool(cloudscraper)}")
    logger.info(f"requests available: {bool(requests)}")
    logger.info(f"tls_client available: {bool(tls_client)}")

    # Start proxy pool refresh immediately
    _init_proxy_pool()

    # Start server immediately so Render detects the port.
    # Do signin in background to avoid blocking webhook health checks.
    init_thread = threading.Thread(target=_init_background, daemon=True)
    init_thread.start()

    refresh_thread = threading.Thread(target=token_refresh_loop, daemon=True)
    refresh_thread.start()

    set_webhook()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
