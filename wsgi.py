from bot import main
import asyncio

# هذا الملف لضمان توافق خادم الاستضافة مع تشغيل البوت المباشر
if __name__ == "__main__":
    asyncio.run(main())
