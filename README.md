Texas4Win Telegram Agent Bot 🎰
بوت تيليجرام احترافي لإدارة وكالة Texas4Win — إنشاء حسابات اللاعبين، معالجة الإيداع والسحب، تذاكر الدعم الفني، ولوحة تحكم المالك.
المميزات ✨
	🤖 واجهة عربية كاملة عبر تيليجرام
	👤 إنشاء حسابات لاعبين جدد
	💰 معالجة الإيداع والسحب مع موافقة المشرفين
	🎫 نظام تذاكر دعم فني
	📢 نظام إذاعة رسائل لجميع اللاعبين
	🔐 لوحة تحكم المالك مع صلاحيات مشرفين
	🛡️ تجاوز Cloudflare عبر بروكسي Thordata
	🌐 Webhook mode على Render
متغيرات البيئة 🌍
المتغير	الوصف	مطلوب؟
BOT_TOKEN	توكن بوت تيليجرام من @BotFather	✅ نعم
AGENT_USERNAME	اسم مستخدم الوكيل على texas4win.com	✅ نعم
AGENT_PASSWORD	كلمة مرور الوكيل على texas4win.com	✅ نعم
PARENT_ID	رقم الوكالة (affiliateId)	✅ نعم
OWNER_ID	معرف تيليجرام لمالك البوت	✅ نعم
ADMIN_GROUP	معرف مجموعة المشرفين (مع علامة -)	✅ نعم
SHAM_CASH_WALLET	عنوان محفظة شام كاش	✅ نعم
SYRIATEL_CASH_CODE	كود شام كاش سيرياتيل	✅ نعم
WEBHOOK_URL	رابط الويب هوك الكامل (https://.../webhook)	✅ نعم
THORDATA_PROXY	رابط بروكسي Thordata السكني (https://user:pass@host:port)	⚠️ مطلوب لتجاوز Cloudflare
THORDATA_TOKEN	توكن Thordata Web Unlocker (لجلب الصفحات فقط)	❌ اختياري
CURRENCY	العملة (افتراضي: SYP)	❌ اختياري
DEPOSIT_MIN	حد أدنى للإيداع (افتراضي: 100000)	❌ اختياري
WITHDRAW_MIN	حد أدنى للسحب (افتراضي: 200000)	❌ اختياري
WITHDRAW_MAX	حد أقصى للسحب (افتراضي: 2000000)	❌ اختياري
WITHDRAW_FEE_PERCENT	نسبة عمولة السحب (افتراضي: 10)	❌ اختياري
API_BASE	رابط API الأساسي	❌ اختياري
DB_PATH	مسار قاعدة البيانات (افتراضي: /tmp/texas4win.db)	❌ اختياري
إعداد Thordata 🛡️
البروكسي السكني (مطلوب لتجاوز Cloudflare)
عنوان Render IP محظور بواسطة Cloudflare على موقع texas4win.com. البروكسي السكني من Thordata يحل هذه المشكلة.
صيغة الرابط:
https://username:password@m26xjqfo.pr.thordata.net:9999
⚠️ مهم: استخدم https:// وليس http:// لتجنب خطأ SSL WRONG_VERSION_NUMBER.
Web Unlocker (اختياري)
يُستخدم فقط لجلب محتوى الصفحات (GET). لا يمكنه إرسال طلبات POST إلى API.
صيغة التوكن:
``
thordata_web_unlocker_token_here
---
## النشر على Render 🚀
1. أنشئ حسابًا على [Render](https://render.com)
2. اربط مستودع GitHub الخاص بك
3. اختر **Web Service**
4. حدد:
   - **Runtime:** Python 3.12
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn bot:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT`
5. أضف جميع متغيرات البيئة من الجدول أعلاه
6. اضغط **Deploy**
### إعداد الويب هوك
بعد النشر، ثبت الويب هوك عبر:
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=<WEBHOOK_URL>"
أو استخدم نقطة الفحص:
curl https://your-app.onrender.com/health
هيكل المشروع 📁
├── bot.py              # البوت الرئيسي (Flask + python-telegram-bot)
├── requirements.txt    # حزم Python المطلوبة
├── render.yaml         # إعدادات النشر على Render
├── .gitignore          # ملفات مستثناة من Git
└── README.md           # هذا الملف
حدود العمليات 💵
العملية	الحد الأدنى	الحد الأقصى	العمولة
إيداع	100,000 SYP	بدون حد	بدون عمولة
سحب	200,000 SYP	2,000,000 SYP	10%
استكشاف الأخطاء 🔧
البوت لا يستجيب
1.	تحقق من /health — هل api_authenticated = true؟
2.	راجع سجلات Render للأخطاء
3.	تأكد من تسجيل الويب هوك بشكل صحيح
خطأ Cloudflare 403
1.	تأكد من تعيين THORDATA_PROXY
2.	تحقق من أن البروكسي يستخدم https://
3.	راجع سجلات Render لرسائل proxy_fallback
خطأ SSL WRONG_VERSION_NUMBER
	غيّر رابط البروكسي من http:// إلى https://
	البوت يحاول كلا البروتوكولين تلقائيًا
الترخيص 📄
مشروع خاص — جميع الحقوق محفوظة.
