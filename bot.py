import subprocess
import sys

# كود إجباري لتثبيت مكتبة التيليجرام تلقائياً عند تشغيل السيرفر
try:
    import telegram
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot", "--upgrade"])
    import telegram

# ----------------------------------------------------
# الآن يبدأ كود البوت القديم الخاص بك بشكل طبيعي أدناه:
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# ... باقي الكود الخاص بك كما هو بدون أي تغيير ...
