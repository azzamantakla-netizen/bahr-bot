// كود بوت تليجرام متكامل ومبرمج بالكامل - فريق بحر (النسخة الاحترافية الشاملة)
const { Telegraf, Markup } = require('telegraf');
const fs = require('fs');

// ⚠️ ضع التوكن الخاص بك هنا ليعمل البوت بشكل صحيح
const BOT_TOKEN = '8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8'; 
const bot = new Telegraf(BOT_TOKEN);

const OWNER_ID = 6693251012;
const ADMIN_GROUP_ID = -1003983996094;

const SETTINGS_FILE = './settings.json';
const USERS_FILE = './users.json';

let userStates = {};

const WITHDRAW_RULES = {
    min: 200000,
    max: 2000000,
    feePercent: 10
};

// دالة تحميل الإعدادات وتحديثها
function loadSettings() {
    if (!fs.existsSync(SETTINGS_FILE)) {
        const defaultSettings = {
            syriatel_code: '48122120',
            cham_wallet: 'a18758d5324eb7595d4463ca355ad221',
            cashier_user: 'Bero@yahoo.com',
            cashier_pass: 'Aazzam@318',
            welcome_msg: "🎰 *أهلاً بك في بوت الشحن والسحب لـ فريق بحر!*\n\n• 💰 *طرق التعبئة:* Syriatel Cash / Sham Cash\n• 🏦 *حدود السحب:* من 200,000 ل.س إلى 2,000,000 ل.س\n• ✂️ *عمولة السحب:* يتم حسم 10% تلقائياً عند تنفيذ الطلب.\n\nيرجى اختيار الخدمة المطلوبة من القائمة أدناه:",
            support_link: "https://t.me" // ⚠️ ضع رابط حساب الدعم الفني الخاص بك هنا
        };
        fs.writeFileSync(SETTINGS_FILE, JSON.stringify(defaultSettings, null, 4));
        return defaultSettings;
    }
    return JSON.parse(fs.readFileSync(SETTINGS_FILE));
}

function saveSettings(settings) {
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 4));
}

// دالة لحفظ المستخدمين من أجل نظام الإذاعة
function saveUser(userId) {
    let users = [];
    if (fs.existsSync(USERS_FILE)) {
        users = JSON.parse(fs.readFileSync(USERS_FILE));
    }
    if (!users.includes(userId)) {
        users.push(userId);
        fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 4));
    }
}

// أمر البداية /start
bot.start((ctx) => {
    const userId = ctx.from.id;
    const firstName = ctx.from.first_name || 'اللاعب';
    saveUser(userId);
    
    let keyboard = [
        ['💰 şحن الرصيد', '🏦 طلب سحب'],
        ['👤 حسابي الفردي', '📞 الدعم الفني']
    ];
    
    if (userId === OWNER_ID) {
        keyboard.push(['⚙️ لوحة تحكم الإدارة']);
    }
    
    const s = loadSettings();
    // استبدال كلمة الاسم ديناميكياً إذا وجدت
    let msg = s.welcome_msg.replace('{name}', firstName);
                           
    ctx.replyWithMarkdown(msg, Markup.keyboard(keyboard).resize());
});

// الأزرار الرئيسية السفلية
bot.hears('💰 şحن الرصيد', (ctx) => {
    ctx.reply('اختر طريقة الدفع المناسبة لك لإرسال الأموال وتعبئة حسابك:', 
        Markup.inlineKeyboard([
            [Markup.button.callback('Syriatel Cash 🇸🇾', 'show_syriatel')],
            [Markup.button.callback('شام كاش (Cham Cash) 💳', 'show_cham')]
        ])
    );
});

bot.hears('🏦 طلب سحب', (ctx) => {
    ctx.replyWithMarkdown(`📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك:`, 
        Markup.inlineKeyboard([
            [Markup.button.callback('Syriatel Cash 🇸🇾', 'withdraw_syriatel')],
            [Markup.button.callback('Sham Cash SYP 💳', 'withdraw_sham')]
        ])
    );
});

bot.hears('👤 حسابي الفردي', (ctx) => {
    const userId = ctx.from.id;
    const firstName = ctx.from.first_name;
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي (فريق بحر):*\n\n• *الاسم:* ${firstName}\n• *المعرف الرقمي (ID):* \`${userId}\`\n• *حالة الحساب:* نشط ✅\n\n_(ملاحظة: يمكنك إرسال الـ ID الخاص بك للدعم الفني عند الحاجة)_`);
});

bot.hears('📞 الدعم الفني', (ctx) => {
    const s = loadSettings();
    ctx.replyWithMarkdown(`📞 *قسم الدعم الفني لـ فريق بحر:*\n\nإذا واجهتك أي مشكلة في الشحن أو السحب، يمكنك التواصل مباشرة مع المشرف عبر الرابط التالي:`,
        Markup.inlineKeyboard([
            [Markup.button.url('💬 تواصل مع الدعم الفني الآن', s.support_link)]
        ])
    );
});

// دخول المالك إلى لوحة التحكم
bot.hears('⚙️ لوحة تحكم الإدارة', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    
    ctx.reply('⚙️ أهلاً بك يا مدير في لوحة تحكم الإدارة. اختر ما تريد تعديله أو التحكم به:',
        Markup.inlineKeyboard([
            [Markup.button.callback('📝 تعديل رسالة الترحيب', 'edit_welcome')],
            [Markup.button.callback('📞 تعديل رابط الدعم', 'edit_support')],
            [Markup.button.callback('💳 تعديل بيانات الدفع والكاشير', 'edit_payments')],
            [Markup.button.callback('📢 عمل إذاعة (Broadcast)', 'start_broadcast')]
        ])
    );
});

// خيارات تعديل الدفع
bot.action('edit_payments', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return ctx.answerCbQuery();
    ctx.answerCbQuery();
    ctx.reply('اختر القيمة المحددة التي ترغب بتعديلها الآن:',
        Markup.inlineKeyboard([
            [Markup.button.callback('🇸🇾 كود سيرياتيل كاش', 'set_syriatel')],
            [Markup.button.callback('💳 عنوان محفظة شام كاش', 'set_cham')],
            [Markup.button.callback('📧 بريد الكاشير الإلكتروني', 'set_cashier_user')],
            [Markup.button.callback('🔑 كلمة مرور الكاشير', 'set_cashier_pass')]
        ])
    );
});

// معالجة الضغط على أزرار التعديل والإذاعة
bot.action(/set_(.+)/, (ctx) => {
    if (ctx.from.id !== OWNER_ID) return ctx.answerCbQuery();
    ctx.answerCbQuery();
    const target = ctx.match[1];
    userStates[ctx.from.id] = { step: `awaiting_setting_${target}` };
    ctx.reply(`✏️ حسناً، أرسل لي القيمة أو البيانات الجديدة الخاصة بـ (${target}) ليتم حفظها فوراً:`);
});

bot.action('edit_welcome', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return ctx.answerCbQuery();
    ctx.answerCbQuery();
    userStates[ctx.from.id] = { step: 'awaiting_welcome_msg' };
    ctx.reply('✏️ أرسل الآن رسالة الترحيب الجديدة للبوت (يمكنك استخدام التنسيقات مثل النجمة للمائل والعريض وتضمين النص المراد):');
});

bot.action('edit_support', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return ctx.answerCbQuery();
    ctx.answerCbQuery();
    userStates[ctx.from.id] = { step: 'awaiting_support_link' };
    ctx.reply('✏️ أرسل رابط تليجرام الجديد الخاص بحساب الدعم الفني (مثال: https://t.me):');
});

bot.action('start_broadcast', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return ctx.answerCbQuery();
    ctx.answerCbQuery();
    userStates[ctx.from.id] = { step: 'awaiting_broadcast_msg' };
    ctx.reply('📢 حسناً، أرسل الآن الرسالة التي تريد إذاعتها ونشرها لكل مستخدمي البوت فوراً:');
});

// عرض معلومات الشحن للاعبين
bot.action('show_syriatel', (ctx) => {
    ctx.answerCbQuery();
    const s = loadSettings();
    ctx.replyWithMarkdown(`*Syriatel Cash 🇸🇾*\n\nيرجى تحويل المبلغ إلى الرقم التابع لنا:\n➡️ \`${s.syriatel_code}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`);
});

bot.action('show_cham', (ctx) => {
    ctx.answerCbQuery();
    const s = loadSettings();
    ctx.replyWithMarkdown(`*شام كاش (Cham Cash) 💳*\n\nيرجى تحويل المبلغ إلى عنوان المحفظة:\n➡️ \`${s.cham_wallet}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`);
});

// معالجة السحب للاعبين
bot.action(/withdraw_(.+)/, (ctx) => {
    const method = ctx.match[1] === 'syriatel' ? 'Syriatel Cash' : 'Sham Cash SYP';
    ctx.answerCbQuery();
    userStates[ctx.from.id] = { step: 'awaiting_withdraw_amount', method: method };
    ctx.reply('✏️ يرجى كتابة المبلغ الذي ترغب بسحبه بالليرة السورية (أرقام فقط):');
});

// استقبال كافة المدخلات النصية والصور وتحليل الحالات
bot.on('message', async (ctx) => {
    const userId = ctx.from.id;
    const currentState = userStates[userId];

    if (currentState) {
        // 1. معالجة الإذاعة (Broadcast) للمالك
        if (currentState.step === 'awaiting_broadcast_msg') {
            const broadcastMsg = ctx.message.text;
            delete userStates[userId];
            
            if (!fs.existsSync(USERS_FILE)) return ctx.reply('❌ لا يوجد مستخدمين مسجلين في البوت للإرسال لهم حالياً.');
            const users = JSON.parse(fs.readFileSync(USERS_FILE));
            
            ctx.reply(`📢 جاري بدء الإذاعة لـ ${users.length} مستخدم...`);
            let successCount = 0;
            
            for (let uId of users) {
                try {
                    await bot.telegram.sendMessage(uId, `📢 *إعلان هام من إدارة فريق بحر:*\n\n${broadcastMsg}`, { parse_mode: 'Markdown' });
                    successCount++;
                } catch (e) {
                    // تجاهل الحسابات التي حظرت البوت
                }
            }
            return ctx.reply(`✅ تم انتهاء الإذاعة بنجاح! وصلت الرسالة إلى ${successCount} مستخدم من أصل ${users.length}.`);
        }

        // 2. معالجة تعديلات لوحة التحكم للمالك
        if (currentState.step.startsWith('awaiting_setting_')) {
            const target = currentState.step.replace('awaiting_setting_', '');
            const value = ctx.message.text;
            delete userStates[userId];
            
            let s = loadSettings();
            s[target] = value;
            saveSettings(s);
            
            return ctx.reply(`✅ تم تحديث بيانات (${target}) بنجاح في الإعدادات إلى القيمة الجديدة.`);
        }

        if (currentState.step === 'awaiting_welcome_msg') {
            const newMsg = ctx.message.text;
            delete userStates[userId];
            let s = loadSettings();
            s.welcome_msg = newMsg;
            saveSettings(s);
            return ctx.reply('✅ تم تحديث رسالة الترحيب بنجاح! سيراها المشتركون الجدد عند الضغط على /start.');
        }

        if (currentState.step === 'awaiting_support_link') {
            const newLink = ctx.message.text;
            delete userStates[userId];
            let s = loadSettings();
            s.support_link = newLink;
            saveSettings(s);
            return ctx.reply('✅ تم تحديث رابط حساب الدعم الفني بنجاح.');
        }

        // 3. معالجة طلب سحب الأموال للاعب
