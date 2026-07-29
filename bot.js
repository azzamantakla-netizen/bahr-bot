// كود بوت تليجرام متكامل - فريق بحر (نسخة تخطي الحظر بدون VPN)
const { Telegraf, Markup } = require('telegraf');
const fs = require('fs');
const { HttpsProxyAgent } = require('https-proxy-agent'); // مكتبة البروكسي لتخطي الحجب

// ⚠️ تأكد من وضع التوكن الخاص بك هنا ليعمل البوت بشكل صحيح
const BOT_TOKEN = '8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8'; 

// سيرفر بروكسي خارجي لتمرير بيانات تليجرام وتخطي الحجب الجغرافي في سوريا
const proxyAgent = new HttpsProxyAgent('http://185.117.153.2:8080'); 

// تشغيل البوت مع دمج إعدادات البروكسي
const bot = new Telegraf(BOT_TOKEN, {
    telegram: { agent: proxyAgent }
});

const OWNER_ID = 6693251012;
const ADMIN_GROUP_ID = -1003983996094;
const SETTINGS_FILE = './settings.json';

let userStates = {};

const WITHDRAW_RULES = {
    min: 200000,
    max: 2000000,
    feePercent: 10
};

// دالة تحميل الإعدادات أو إنشائها تلقائياً
function loadSettings() {
    if (!fs.existsSync(SETTINGS_FILE)) {
        const defaultSettings = {
            syriatel_code: '48122120',
            cham_wallet: 'a18758d5324eb7595d4463ca355ad221',
            cashier_user: 'Bero@yahoo.com',
            cashier_pass: 'Aazzam@318' 
        };
        fs.writeFileSync(SETTINGS_FILE, JSON.stringify(defaultSettings, null, 4));
        return defaultSettings;
    }
    return JSON.parse(fs.readFileSync(SETTINGS_FILE));
}

// أمر البداية /start
bot.start((ctx) => {
    const userId = ctx.from.id;
    const firstName = ctx.from.first_name || 'اللاعب';
    
    let keyboard = [
        ['💰 شحن الرصيد', '🏦 طلب سحب'],
        ['👤 حسابي الفردي', '📞 الدعم الفني']
    ];
    
    if (userId === OWNER_ID) {
        keyboard.push(['⚙️ لوحة تحكم الإدارة']);
    }
    
    const welcomeMessage = `🎰 *أهلاً بك يا ${firstName} في بوت الشحن والسحب لـ فريق بحر!*\n\n` +
                           `• 💰 *طرق التعبئة:* Syriatel Cash / Sham Cash\n` +
                           `• 🏦 *حدود السحب:* من 200,000 ل.س إلى 2,000,000 ل.س\n` +
                           `• ✂️ *عمولة السحب:* يتم حسم 10% تلقائياً عند تنفيذ الطلب.\n\n` +
                           `يرجى اختيار الخدمة المطلوبة من القائمة أدناه:`;
                           
    ctx.replyWithMarkdown(welcomeMessage, Markup.keyboard(keyboard).resize());
});

// عند الضغط على زر شحن الرصيد
bot.hears('💰 شحن الرصيد', (ctx) => {
    ctx.reply('اختر طريقة الدفع المناسبة لك لإرسال الأموال وتعبئة حسابك:', 
        Markup.inlineKeyboard([
            [Markup.button.callback('Syriatel Cash 🇸🇾', 'show_syriatel')],
            [Markup.button.callback('شام كاش (Cham Cash) 💳', 'show_cham')]
        ])
    );
});

// عرض معلومات السيريتل كاش
bot.action('show_syriatel', (ctx) => {
    ctx.answerCbQuery();
    const s = loadSettings();
    ctx.replyWithMarkdown(`*Syriatel Cash 🇸🇾*\n\nيرجى تحويل المبلغ إلى الرقم التابع لنا:\n➡️ \`${s.syriatel_code}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`);
});

// عرض معلومات الشام كاش
bot.action('show_cham', (ctx) => {
    ctx.answerCbQuery();
    const s = loadSettings();
    ctx.replyWithMarkdown(`*شام كاش (Cham Cash) 💳*\n\nيرجى تحويل المبلغ إلى عنوان المحفظة:\n➡️ \`${s.cham_wallet}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`);
});

// عند الضغط على زر طلب سحب
bot.hears('🏦 طلب سحب', (ctx) => {
    ctx.replyWithMarkdown(`📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك:`, 
        Markup.inlineKeyboard([
            [Markup.button.callback('Syriatel Cash 🇸🇾', 'withdraw_syriatel')],
            [Markup.button.callback('Sham Cash SYP 💳', 'withdraw_sham')]
        ])
    );
});

// معالجة اختيار طريقة السحب
bot.action(/withdraw_(.+)/, (ctx) => {
    const method = ctx.match[1] === 'syriatel' ? 'Syriatel Cash' : 'Sham Cash SYP';
    ctx.answerCbQuery();
    
    userStates[ctx.from.id] = { 
        step: 'awaiting_withdraw_amount', 
        method: method 
    };
    
    ctx.reply('✏️ يرجى كتابة المبلغ الذي ترغب بسحبه بالليرة السورية (أرقام فقط):');
});

// استقبال الرسائل والصور وإرسال الإشعارات للإدارة
bot.on('message', async (ctx) => {
    const userId = ctx.from.id;
    
    // 1. معالجة إدخال مبلغ السحب
    if (userStates[userId] && userStates[userId].step === 'awaiting_withdraw_amount') {
        const amount = parseInt(ctx.message.text);
        
        if (isNaN(amount) || amount <= 0) {
            return ctx.reply('❌ يرجى إدخال مبلغ صحيح بالأرقام فقط.');
        }
        
        if (amount < WITHDRAW_RULES.min || amount > WITHDRAW_RULES.max) {
            return ctx.reply('❌ الطلب يخرق حدود السحب المسموحة (بين 200,000 و 2,000,000 ل.س).');
        }
        
        const fee = amount * (WITHDRAW_RULES.feePercent / 100);
        const finalAmount = amount - fee;
        
        await bot.telegram.sendMessage(ADMIN_GROUP_ID, 
            `🏦 *طلب سحب جديد (فريق بحر):*\n` +
            `• اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n` +
            `• الطريقة: ${userStates[userId].method}\n` +
            `• المبلغ: ${amount.toLocaleString()} ل.س\n` +
            `• الصافي بعد خصم الـ 10%: *${finalAmount.toLocaleString()}* ل.س`, 
            { parse_mode: 'Markdown' }
        );
        
        ctx.reply('✅ تم رفع طلب السحب الخاص بك لـ فريق الإدارة ومجموعة المشرفين بنجاح.');
        delete userStates[userId];
        return;
    }
    
    // 2. معالجة استقبال إيصالات التعبئة (الصور)
    if (ctx.message.photo) {
        const photoId = ctx.message.photo[ctx.message.photo.length - 1].file_id;
        
        await bot.telegram.sendPhoto(ADMIN_GROUP_ID, photoId, {
            caption: `💰 *إيصال تعبئة معلق (فريق بحر):*\n` +
                     `• من اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n` +
                     `• النص المرفق: "${ctx.message.caption || 'لا يوجد نص مرفق'}"`,
            parse_mode: 'Markdown'
        });
        
        return ctx.reply('✅ تم استلام الإيصال وجاري مراجعته لدى مشرفي فريق بحر.');
    }
});

// تشغيل البوت
bot.launch().then(() => console.log('✅ البوت يعمل الآن عبر البروكسي ومربوط بمجموعتكم...'));

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
