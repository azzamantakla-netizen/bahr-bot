import requests
import logging

logger = logging.getLogger(__name__)

def execute_panel_registration(username, password, email):
    """
    جسر خارجي صامت ومستقل تماماً ومحمي بالكامل 100%.
    مهمته فقط إرسال البيانات للوحة، ولا يمكنه إيقاف أو تخريب البوت الأساسي.
    """
    # بيانات تسجيل دخول الوكيل (تعديل الايميل والباسورد هنا فقط)
    AGENT_EMAIL = "Bero@yahoo.com"
    AGENT_PASSWORD = "Aazzam@318"
    
    LOGIN_URL = "https://agents.texas4win.com"
    REGISTER_URL = "https://agents.texas4win.com"
