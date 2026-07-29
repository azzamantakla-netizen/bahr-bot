// كود بوت تليجرام متكامل - فريق بحر (نسخة لوحة التحكم الديناميكية الشاملة)
const { Telegraf, Markup } = require('telegraf');
const fs = require('fs');

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

// دالة تحميل الإعدادات أو إنشائها تلقائياً مع دعم رسالة الترحيب الديناميكية
function loadSettings() {
    if (!fs.existsSync(SETTINGS_FILE)) {
        const defaultSettings = {
            syriatel_code: '48122120',
            cham_wallet: 'a18758d5324eb7595d4463ca355ad221',
            cashier_user: 'Bero@yahoo.com',
            cashier_pass: 'Aazzam@318',
            welcome_msg: "🎰 *أهلاً بك يا {name} في بوت الشحن والسحب لـ فريق بحر!*\n\n• 💰 *طرق التعبئة:* Syriatel Cash / Sham Cash\n• 🏦 *حدود السحب:* من 200,000 ل.س إلى 2,000,000 ل.س\n• ✂️ *عمولة السحب:* يتم حسم 10% تلقائياً عند تنفيذ الطلب.\n\nيرجى اختيار الخدمة المطلوبة من القائمة أدناه:"
        };
        fs.writeFileSync(SETTINGS_FILE, JSON.stringify(defaultSettings, null, 4));
        return defaultSettings;
    }
    return JSON.parse(fs.readFileSync(SETTINGS_FILE));
}

// دالة لحفظ الإعدادات المعدلة
function saveSettings(settings) {
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 4));
}

// دالة لحفظ المستخدمين الجدد من أجل نظام الإذاعة
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

// قائمة أزرار اللاعب الرئيسية
function getMainMenu(userId) {
    let keyboard = [
        ['💰 شحن الرصيد', '🏦 طلب سحب'],
        ['👤 حسابي الفردي', '📞 الدعم الفني']
    ];
    if (userId === OWNER_ID) {
        keyboard.push(['⚙️ لوحة تحكم الإدارة']);
    }
    return Markup.keyboard(keyboard).resize();
}

// قائمة أزرار الإدارة الفرعية
function getAdminMenu() {
    return Markup.keyboard([
        ['📞 تعديل سيريتل كاش', '💳 تعديل شام كاش'],
        ['📝 تعديل رسالة الترحيب', '📢 إرسال إذاعة'],
        ['🔙 العودة للقائمة الرئيسية']
    ]).resize();
}

// أمر البداية /start
bot.start((ctx) => {
    const userId = ctx.from.id;
    const firstName = ctx.from.first_name || 'اللاعب';
    saveUser(userId); // حفظ المستخدم للنشر لاحقاً
    
    const s = loadSettings();
    // استبدال كلمة {name} باسم اللاعب الحقيقي ديناميكياً
    const customizedWelcome = s.welcome_msg.replace('{name}', firstName);
                           
    ctx.replyWithMarkdown(customizedWelcome, getMainMenu(userId));
});

// العودة للقائمة الرئيسية
bot.hears('🔙 العودة للقائمة الرئيسية', (ctx) => {
    ctx.reply('تم العودة للقائمة الرئيسية بنجاح.', getMainMenu(ctx.from.id));
});

// زر الدعم الفني
bot.hears('📞 الدعم الفني', (ctx) => {
    ctx.reply('📞 للتواصل مع الدعم الفني والاستفسارات، يرجى مراسلة الحساب المعتمد التالي:\n\n➡️ @Bahr_Team_Support');
});

// زر حسابي الفردي
bot.hears('👤 حسابي الفردي', (ctx) => {
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي:*\n\n• الاسم: *${ctx.from.first_name}*\n• المعرف الرقمي: \`${ctx.from.id}\`\n\n📌 رصيد حسابك يتم تحديثه ومراجعته بواسطة نظام الكاشير يدويًا بعد مراجعة إ إيصالات التعبئة.`);
});

// الدخول للوحة تحكم الإدارة (للمالك فقط)
bot.hears('⚙️ لوحة تحكم الإدارة', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return ctx.reply('❌ عذراً، هذا القسم مخصص لمالك البوت فقط.');
    ctx.reply('⚙️ أهلاً بك في لوحة تحكم الإدارة. يرجى اختيار الإجراء المطلوب:', getAdminMenu());
});

// بدء عمليات تعديل الإعدادات من تليجرام
bot.hears('📞 تعديل سيريتل كاش', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'edit_syriatel' };
    ctx.reply('✏️ يرجى إرسال رقم السيريتل كاش الجديد الآن:');
});

bot.hears('💳 تعديل شام كاش', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'edit_cham' };
    ctx.reply('✏️ يرجى إرسال عنوان محفظة شام كاش الجديدة الآن:');
});

bot.hears('📝 تعديل رسالة الترحيب', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'edit_welcome' };
    ctx.replyWithMarkdown('✏️ أرسل رسالة الترحيب الجديدة الآن.\n\n💡 *ملاحظة هامة:* ضع كلمة `{name}` في المكان الذي تريد أن يظهر فيه اسم اللاعب تلقائياً.');
});

bot.hears('📢 إرسال إذاعة', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'broadcast_msg' };
    ctx.reply('📢 يرجى كتابة وإرسال نص الرسالة التي تريد نشرها لجميع المشتركين الآن:');
});

// أزرار الشحن للاعبين
bot.hears('💰 شحن الرصيد', (ctx) => {
    ctx.reply('اختر طريقة الدفع المناسبة لك لإرسال الأموال وتعبئة حسابك:', 
        Markup.inlineKeyboard([
            [Markup.button.callback('Syriatel Cash 🇸🇾', 'show_syriatel')],
            [Markup.button.callback('شام كاش (Cham Cash) 💳', 'show_cham')]
        ])
    );
});

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

// أزرار السحب للاعبين
bot.hears('🏦 طلب سحب', (ctx) => {
    ctx.replyWithMarkdown(`📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك:`, 
        Markup.inlineKeyboard([
            [Markup.button.callback('Syriatel Cash 🇸🇾', 'withdraw_syriatel')],
            [Markup.button.callback('Sham Cash SYP 💳', 'withdraw_sham')]
        ])
    );
});

bot.action(/withdraw_(.+)/, (ctx) => {
    const method = ctx.match === 'syriatel' ? 'Syriatel Cash' : 'Sham Cash SYP';
    ctx.answerCbQuery();
    userStates[ctx.from.id] = { step: 'awaiting_withdraw_amount', method: method };
    ctx.reply('✏️ يرجى كتابة المبلغ الذي ترغب بسحبه بالليرة السورية (أرقام فقط):');
});

// معالجة كافة الرسائل المدخلة
bot.on('message', async (ctx) => {
    const userId = ctx.from.id;
    const currentState = userStates[userId]?.step;
    
    if (currentState) {
        const s = loadSettings();
        
        if (currentState === 'edit_syriatel') {
            s.syriatel_code = ctx.message.text;
            saveSettings(s);
            delete userStates[userId];
            return ctx.reply(`✅ تم تحديث رقم سيريتل كاش بنجاح إلى: ${ctx.message.text}`, getAdminMenu());
        }
        
        if (currentState === 'edit_cham') {
            s.cham_wallet = ctx.message.text;
            saveSettings(s);
            delete userStates[userId];
            return ctx.reply(`✅ تم تحديث محفظة شام كاش بنجاح إلى: ${ctx.message.text}`, getAdminMenu());
        }
        
        if (currentState === 'edit_welcome') {
            s.welcome_msg = ctx.message.text;
            saveSettings(s);
            delete userStates[userId];
            return ctx.reply('✅ تم تحديث رسالة الترحيب الديناميكية بنجاح!', getAdminMenu());
        }
        
        if (currentState === 'broadcast_msg') {
            delete userStates[userId];
            ctx.reply('⏳ جاري بدء الإذاعة ونشر الرسالة لجميع اللاعبين...');
            
            if (fs.existsSync(USERS_FILE)) {
                const users = JSON.parse(fs.readFileSync(USERS_FILE));
                let successCount = 0;
                
                for (const uId of users) {
                    try {
                        await bot.telegram.sendMessage(uId, ctx.message.text);
                        successCount++;
                    } catch (err) {
                        console.log(`فشل الإرسال للمستخدم: ${uId}`);
                    }
                }
                return ctx.reply(`📢 تمت الإذاعة بنجاح! وصلت الرسالة لـ ${successCount} لاعب.`);
            } else {
                return ctx.reply('❌ لا يوجد لاعبون مسجلون في قائمة الإذاعة بعد.');
            }
        }
        
        if (currentState === 'awaiting_withdraw_amount') {
            const amount = parseInt(ctx.message.text);
            if (isNaN(amount) || amount <= 0) return ctx.reply('❌ يرجى إدخال مبلغ صحيح بالأرقام فقط.');
            if (amount < WITHDRAW_RULES.min || amount > WITHDRAW_RULES.max) return ctx.reply('❌ الطلب يخرق حدود السحب المسموحة.');
            
            const fee = amount * (WITHDRAW_RULES.feePercent / 100);
            const finalAmount = amount - fee;
            
            await bot.telegram.sendMessage(ADMIN_GROUP_ID, 
                `🏦 *طلب سحب جديد (فريق بحر):*\n• اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n• الطريقة: ${userStates[userId].method}\n• المبلغ: ${amount.toLocaleString()} ل.س\n• الصافي: *${finalAmount.toLocaleString()}* ل.س`, 
                { parse_mode: 'Markdown' }
            );
            
            ctx.reply('✅ تم رفع طلب السحب الخاص بك لـ فريق الإدارة ومجموعة المشرفين بنجاح.');
            delete userStates[userId];
            return;
        }
    }
    
    if (ctx.message.photo) {
        const photoId = ctx.message.photo[ctx.message.photo.length - 1].file_id;
        await bot.telegram.sendPhoto(ADMIN_GROUP_ID, photoId, {
            caption: `💰 *إيصال تعبئة معلق (فريق بحر):*\n• من اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n• النص: "${ctx.message.caption || ''}"`,
            parse_mode: 'Markdown'
        });
