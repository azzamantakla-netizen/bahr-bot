def api_register_player(username, password):
    global user_cookies
    try:
        import requests
        cookie_dict = {}
        if user_cookies:
            for item in user_cookies.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookie_dict[k.strip()] = v.strip()
                    
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": PANEL_BASE,
            "Referer": f"{PANEL_BASE}/global/agent/User/index",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        email = "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@gmail.com"
        payload = {"player": {"email": email, "password": password, "parentId": "2627036", "login": username}}
        print(f"[🚀] قذف حزمة إنشاء اللاعب البشري: {username}", flush=True)
        
        # استخدام requests مع فرض مهلة 5 ثوانٍ صارمة للاتصال والقراءة
        res = requests.post(REGISTER_PLAYER_API_URL, json=payload, headers=headers, cookies=cookie_dict, timeout=(5, 5))
        print(f"[🔬] رد لوحة إنشاء الحساب العكسي: الرمز {res.status_code}", flush=True)
        
        if res.status_code == 200:
            try:
                res_data = res.json()
                if res_data.get("result") == 1 or res_data.get("status") is True:
                    return True, "نجاح"
                return False, res_data.get("notification", {}).get("content", "خطأ في بيانات المدخلات باللوحة")
            except Exception as json_err:
                return False, f"فشل فك تشفير حزمة الرد الفعلي للوحة: {json_err}"
        return False, f"رد اللوحة بـ الرمز {res.status_code} (جلسة الكوكيز الحالية تالفة أو انتهت)"
        
    except requests.exceptions.Timeout:
        return False, "⚠️ انتهت مهلة الاتصال باللوحة (السيرفر لم يستجب خلال 5 ثوانٍ)."
    except requests.exceptions.RequestException as req_err:
        return False, f"⚠️ خطأ في الاتصال بالشبكة أو جدار الحماية: {req_err}"
    except Exception as general_e:
        return False, f"⚠️ خطأ غير متوقع في النظام: {general_e}"
