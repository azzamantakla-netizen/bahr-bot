import os
import json
import time
import threading
import logging
import base64
import random
import string
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

try:
    import tls_client
except Exception:
    tls_client = None

try:
    import requests
except Exception:
    requests = None

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
RENDER_URL = "https://onrender.com"

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


def _request_with_tls(url, headers, payload, method):
    if not session:
        return None
    try:
        if method.upper() == "GET":
            return session.get(url, headers=headers, timeout_seconds=30)
        else:
            return session.post(url, headers=headers, json=payload, timeout_seconds=30)
    except Exception as e:
        logger.warning(f"tls_client request failed: {e}")
        return None


def _request_with_requests(url, headers, payload, method):
    if not requests:
        return None
    try:
        if method.upper() == "GET":
            return requests.get(url, headers=headers, json=payload, timeout=30, verify=False)
        else:
            return requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
    except Exception as e:
        logger.warning(f"requests fallback failed: {e}")
        return None


class FakeResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def api_request(method, endpoint, payload=None, auth=False):
    url = f"{PANEL_BASE}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://agents.texas4win.com",
        "Referer": "https://agents.texas4win.com"
    }
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    logger.info(f"API REQUEST: {method} {url} | auth={auth} | payload={json.dumps(payload, ensure_ascii=False)[:500]}")
    try:
        response = _request_with_requests(url, headers, payload, method)
        if response is None:
            response = _request_with_tls(url, headers, payload, method)
        if response is None:
            raise Exception("Both requests and tls_client failed to connect")

        if auth and response.status_code in (401, 403):
            logger.warning(f"Auth failed ({response.status_code}), attempting re-signin...")
            if do_signin():
                headers["Authorization"] = f"Bearer {access_token}"
                response = _request_with_requests(url, headers, payload, method)
                if response is None:
                    response = _request_with_tls(url, headers, payload, method)
                if response is None:
                    raise Exception("Both requests and tls_client failed on retry")
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
    try:
        search_payload = {
            "start": 0,
            "limit": 1,
            "filter": {},
            "isNextPage": False
        }
        players_result = api_request("POST", "global/api/UserApi/getPlayersForCurrentAgent", search_payload, auth=True)
        logger.info(f"getPlayersForCurrentAgent affiliate fetch: {players_result}")
