Texas4Win Telegram Bot
كازينو تكساس - بوت تليجرام لوكالة إدارة اللاعبين
الملفات
	bot.py — الملف الرئيسي للبوت
	requirements.txt — المكتبات المطلوبة
	render.yaml — إعدادات Render
	.gitignore — ملفات مستثناة من Git
النشر على Render
1. رفع الكود إلى GitHub
git init
git add .
git commit -m "Texas4Win Bot v1"
git remote add origin <YOUR_GITHUB_REPO>
git push -u origin main
2. إنشاء خدمة على Render
	اذهب إلى render.com وأنشئ خدمة Web Service جديدة
	اختر مستودع GitHub الخاص بك
	اختر Python كـ Runtime
3. Build Command
pip install -r requirements.txt
4. Start Command
gunicorn bot:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
5. Environment Variables
المتغير	القيمة
BOT_TOKEN	8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE
AGENT_USERNAME	Bero@yahoo.com
AGENT_PASSWORD	Aazzam@318
PARENT_ID	2688288
OWNER_ID	6693251012
ADMIN_GROUP	-1003983996094
SHAM_CASH_WALLET	a18758d5324eb7595d4463ca355ad221
SYRIATEL_CASH_CODE	48122120
WEBHOOK_URL	https://YOUR-APP-NAME.onrender.com/8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE
CURRENCY	SYP
DEPOSIT_MIN	100000
WITHDRAW_MIN	200000
WITHDRAW_MAX	2000000
WITHDRAW_FEE_PERCENT	10
API_BASE	https://agents.texas4win.com/global/api/User/
DB_PATH	/tmp/texas4win.db

⚠️WEBHOOK_URL: بعد نشر البوت، خذ رابط الخدمة من Render (مثلاً https://texas4win.onrender.com) وأضف /8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE كمتصف كامل

الأوامر
	/start — القائمة الرئيسية
	/panel — لوحة تحكم المالك (للمالك فقط)
