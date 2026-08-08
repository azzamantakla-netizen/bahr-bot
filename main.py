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

# Improved TLS Client for Cloudflare Bypass
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
RENDER_URL = "https://bahr-bot-c3ac.onrender.com"

AGENT_USERNAME = "Bero@yahoo.com"
AGENT_PASSWORD = "Aazzam@318"
SHAM_CASH_WALLET = "a18758d5324eb7595d4463ca355ad221"
SYRIATEL_CASH_CODE = "481 22120"

OWNERS_FILE = "owners.txt"
ADMINS_FILE = "admins.txt"
USERS_FILE = "users.txt"
PLAYERS_DB_FILE = "players_db.json"

# Session Management
session = None
def create_session():
    global session
    if tls_client:
        try:
            session = tls_client.Session(
                client_identifier="chrome_120",
                random_tls_extension_order=True
            )
            logger.info("TLS Session created successfully.")
        except Exception as e:
            logger.error(f"Failed to create TLS session: {e}")
            session = None
    return session

create_session()

access_token = None
refresh_token = None
agent_affiliate_id = None

# =============================================================================
# Optimized API Helper
# =============================================================================
def api_request(method, endpoint, payload=None, auth=False, retries=2):
    url = f"{PANEL_BASE}/{endpoint}"
    
    # Professional headers to mimic real browser and bypass basic Cloudflare checks
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://agents.texas4win.com",
        "Referer": "https://agents.texas4win.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    
    if auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    for attempt in range(retries + 1):
        try:
            if not session:
                create_session()
                
            if method.upper() == "GET":
                resp = session.get(url, headers=headers, timeout_seconds=30)
            else:
                resp = session.post(url, headers=headers, json=payload, timeout_seconds=30)
            
            if resp.status_code in (401, 403) and auth:
                logger.warning(f"Auth error ({resp.status_code}), re-signing in...")
                if do_signin():
                    headers["Authorization"] = f"Bearer {access_token}"
                    continue # Retry with new token
            
            if resp.status_code == 200 or resp.status_code == 201:
                return resp.json()
            else:
                logger.error(f"API Error: {resp.status_code} - {resp.text}")
                return resp.json() if resp.text else {"status": False, "error": resp.status_code}
                
        except Exception as e:
            logger.error(f"Request attempt {attempt+1} failed: {e}")
            if attempt == retries:
                return None
            time.sleep(2)
    return None

def do_signin():
    global access_token, refresh_token
    payload = {"username": AGENT_USERNAME, "password": AGENT_PASSWORD}
    result = api_request("POST", "global/api/UserApi/signIn", payload)
    if result and result.get("status") and isinstance(result.get("result"), dict):
        access_token = result["result"].get("accessToken")
        refresh_token = result["result"].get("refreshToken")
        logger.info("Sign in successful.")
        return True
    logger.error("Sign in failed.")
    return False

# =============================================================================
# Registration Logic Improvement
# =============================================================================
def register_player_logic(chat_id, username, password):
    global agent_affiliate_id
    if not agent_affiliate_id:
        # Fetch or use fallback
        agent_affiliate_id = "2688288" 
    
    # Ensure unique email
    email = f"{username}_{random.randint(1000,9999)}@texas-bot.com"
    
    payload = {
        "player": {
            "login": username,
            "email": email,
            "password": password,
            "parentId": int(agent_affiliate_id),
            "firstName": username,
            "lastName": "Player"
        }
    }
    
    result = api_request("POST", "global/api/UserApi/registerPlayer", payload, auth=True)
    return result

# Note: The rest of the bot logic (Telebot handlers, Flask webhook) remains as provided 
# but uses these improved helper functions for stable connection.
# The user should replace the helper functions in their original file with these.
