import requests
import logging

logger = logging.getLogger(__name__)

def execute_panel_registration(username, password, email):
    """
    جسر خارجي صامت للاتصال بلوحة الوكيل وإنشاء الحساب في أجزاء من الثانية.
    محمي بالكامل ولا يمكن أن يتسبب في إيقاف أو انطفاء البوت الأساسي.
    """
    # بيانات تسجيل دخول الوكيل الثابتة
    AGENT_EMAIL = "Bero@yahoo.com"
    AGENT_PASSWORD = "Aazzam@318"
    
    LOGIN_URL = "https://agents.texas4win.com"
    # مسار السيرفر الخلفي لإنشاء اللاعبين بناءً على تحديثات النظام لديك
    REGISTER_URL = "https://agents.texas4win.com"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://agents.texas4win.com",
        "Content-Type": "application/json"
    })
    
    try:
        # 1. تسجيل الدخول خلف الكواليس بجلسة صامتة
        login_payload = {
            "username": AGENT_EMAIL,
            "password": AGENT_PASSWORD
        }
        login_res = session.post(LOGIN_URL, json=login_payload, timeout=8)
        
        if login_res.status_code not in:
            logger.error("Bridge: Failed to login to agent panel.")
            return False
            
        # 2. بناء بيانات اللاعب المطابقة تماماً لهيكل الوكيل والنظام النصي (المعرف 2688288)
        # تمرير صيغة الوكيل المدمجة "2688288-bero@yahoo.com" كما في اللوحة تماماً
        agent_identity = f"2688288-{AGENT_EMAIL.lower()}"
        
        player_payload = {
            "player": {
                "login": username,
                "email": email,
                "password": password,
                "parentId": 2688288,
                "firstName": username,
                "lastName": username,
                "agent": agent_identity,
                "role": "player",
                "status": "active"
            }
        }
        
        # إرسال طلب الإنشاء الفوري للسيرفر
        reg_res = session.post(REGISTER_URL, json=player_payload, timeout=8)
        
        if reg_res.status_code in:
            return True
        else:
            logger.error(f"Bridge: Panel rejected registration with status {reg_res.status_code}")
            return False
            
    except Exception as e:
        # حماية مطلقة: أي خطأ في شبكة اللوحة يتم التقاطه هنا لمنع انهيار البوت
        logger.error(f"Bridge Critical Exception: {e}")
        return False
