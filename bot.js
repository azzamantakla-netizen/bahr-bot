const { Telegraf, Markup } = require('telegraf'); 
const fs = require('fs'); 
const http = require('http'); 

// 1. إعداد الثوابت الأساسية للبوت 
const BOT_TOKEN = '8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8'; 
const bot = new Telegraf(BOT_TOKEN); 
const OWNER_ID = 6693251012; 
const ADMIN_GROUP_ID = -1003983996094; 
const SETTINGS_FILE = './settings.json'; 
const USERS_FILE = './users.json'; 
const ACCOUNTS_FILE = './accounts.json'; 
let userStates = {}; 
const WITHDRAW_RULES = { min: 200000, max: 2000000, feePercent: 10 }; 

// 2. دالة تحميل الإعدادات وتصحيح بنية المصفوفات البرمجية مئة بالمئة 
function loadSettings() { 
    if (!fs.existsSync(SETTINGS_FILE)) { 
        const defaultSettings = { 
            owners: ["6693251012"], 
            admins: [], 
            syriatel_code: '48122120', 
            cham_wallet: 'a18758d5324eb7595d4463ca355ad221', 
            cashier_user: 'Bero@yahoo.com', 
            cashier_pass: 'Aazzam@318', 
            welcome_msg: "مرحبا بك في عائلتنا صمم هذا البوت باحترافية عالية ليقدم لك تجربة من نوع آخر نقدم لك سرعة عالية في الايداع ومرونة عالية في السحب تفضل بالاختيار من القائمة بحسب الزر الذي يلبي طلبك" 
        }; 
        fs.writeFileSync(SETTINGS_FILE, JSON.stringify(defaultSettings, null, 4)); 
        return defaultSettings; 
    } 
    return JSON.parse(fs.readFileSync(SETTINGS_FILE)); 
} 

function saveSettings(settings) { 
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 4)); 
} 

function isOwner(userId) { 
    const s = loadSettings(); 
    return s.owners.includes(String(userId)) || userId === OWNER_ID; 
} 

function getPlayerAccount(userId) { 
    if (!fs.existsSync(ACCOUNTS_FILE)) return null; 
    const accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE)); 
    return accounts[userId] || null; 
} 

function savePlayerAccount(userId, gameId, balance = 0) { 
    let accounts = {}; 
    if (fs.existsSync(ACCOUNTS_FILE)) { 
        accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE)); 
    } 
    accounts[userId] = { gameId: gameId, balance: balance }; 
    fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); 
} 

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

// 3. قوائم التحكم بالأزرار 
function getMainMenu(userId) { 
    let keyboard = [ 
        ['💰 شحن الرصيد', '🏦 طلب سحب'], 
        ['👤 حسابي الفردي', '📞 الدعم الفني'] 
    ]; 
    if (isOwner(userId)) { 
        keyboard.push(['⚙️ لوحة تحكم الإدارة']); 
    } 
    return Markup.keyboard(keyboard).resize(); 
} 

function getAdminMenu() { 
    return Markup.keyboard([ 
        ['📞 تعديل سيريتل كاش', '💳 تعديل شام كاش'], 
        ['📝 تعديل رسالة الترحيب', '📢 إرسال إذاعة'], 
        ['➕ إضافة مالك جديد', '➕ إضافة مشرف جديد'], 
        ['📧 تعديل إيميل الكاشير', '🔑 تعديل باسورد الكاشير'], 
        ['🔙 العودة للقائمة الرئيسية'] 
    ]).resize(); 
} 

// 4. معالجة الأوامر الرئيسية وبدء تشغيل البوت 
bot.start((ctx) => { 
    const userId = ctx.from.id; 
    saveUser(userId); 
    const s = loadSettings(); 
    ctx.reply(s.welcome_msg, getMainMenu(userId)); 
}); 

bot.hears('🔙 العودة للقائمة الرئيسية', (ctx) => { 
    ctx.reply('تم العودة للقائمة الرئيسية بنجاح.', getMainMenu(ctx.from.id)); 
}); 

bot.hears('📞 الدعم الفني', (ctx) => { 
    userStates[ctx.from.id] = { step: 'awaiting_support_msg' }; 
    ctx.reply('❤️ لا تقلق نحن معك وفريقنا جاهز لخدمتك على مدار الساعة، فقط اكتب المشكلة أو الاستفسار بالتفصيل وأرسله الآن وسنقوم بالرد عليك فوراً:'); 
});

bot.hears('👤 حسابي الفردي', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id); 
    if (!account) { 
        return ctx.reply('❌ حسابك غير مسجل في نظام البوت حتى الآن.\n\nيرجى الضغط على الزر أدناه لإنشاء حسابك وربطه بمعرف اللعبة:', 
            Markup.inlineKeyboard([[Markup.button.callback('🆕 إنشاء حساب جديد', 'register_account')]]) 
        ); 
    } 
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي الموثق:*\n\n• الاسم: *${ctx.from.first_name}*\n• معرف اللعبة (ID): \`${account.gameId}\`\n• رصيدك الحالي: *${account.balance.toLocaleString()}* ل.س\n\n📌 يتم تحديث الرصيد تلقائياً عند موافقة الإدارة على إيصالات الشحن الخاصة بك.`); 
}); 

bot.action('register_account', (ctx) => { 
    ctx.answerCbQuery(); 
    userStates[ctx.from.id] = { step: 'awaiting_game_id' }; 
    ctx.reply('✏️ يرجى إرسال معرف اللعبة (ID) الخاص بك الآن لإنشاء الحساب:'); 
}); 

bot.hears('⚙️ لوحة تحكم الإدارة', (ctx) => { 
    if (!isOwner(ctx.from.id)) return ctx.reply('❌ عذراً، هذا قسم مخصص لمالك البوت فقط.'); 
    ctx.reply('⚙️ أهلاً بك في لوحة تحكم الإدارة الشاملة. اختر الإجراء المطلوب:', getAdminMenu()); 
}); 

bot.hears('💰 شحن الرصيد', (ctx) => { 
    ctx.reply('اختر طريقة الدفع المناسبة لك لإرسال الأموال وتعبئة حسابك:', Markup.inlineKeyboard([ 
        [Markup.button.callback('Syriatel Cash 🇸🇾', 'show_syriatel')], 
        [Markup.button.callback('شام كاش (Cham Cash) 💳', 'show_cham')] 
    ])); 
}); 

bot.action('show_syriatel', (ctx) => { 
    ctx.answerCbQuery(); 
    const s = loadSettings(); 
    userStates[ctx.from.id] = { step: 'awaiting_receipt' }; 
    ctx.replyWithMarkdown(`*Syriatel Cash 🇸🇾*\n\nيرجى تحويل المبلغ إلى الرقم التابع لنا:\n➡️ \`${s.syriatel_code}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`); 
}); 

bot.action('show_cham', (ctx) => { 
    ctx.answerCbQuery(); 
    const s = loadSettings(); 
    userStates[ctx.from.id] = { step: 'awaiting_receipt' }; 
    ctx.replyWithMarkdown(`*شام كاش (Cham Cash) 💳*\n\nيرجى تحويل المبلغ إلى عنوان المحفظة:\n➡️ \`${s.cham_wallet}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`); 
});

bot.hears('🏦 طلب سحب', (ctx) => { 
    ctx.replyWithMarkdown(`📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك:`, 
        Markup.inlineKeyboard([ 
            [Markup.button.callback('Syriatel Cash 🇸🇾', 'withdraw_syriatel')], 
            [Markup.button.callback('Sham Cash SYP 💳', 'withdraw_sham')] 
        ]) 
    ); 
}); 

bot.action(/withdraw_(.+)/, (ctx) => { 
    const method = ctx.match[1] === 'syriatel' ? 'Syriatel Cash' : 'Sham Cash SYP'; 
    ctx.answerCbQuery(); 
    userStates[ctx.from.id] = { step: 'awaiting_withdraw_amount', method: method }; 
    ctx.reply('✏️ يرجى كتابة المبلغ الذي ترغب بسحبه بالليرة السورية (أرقام فقط):'); 
}); 

// معالجة الضغط على أزرار القبول والرفض داخل مجموعة المشرفين
bot.action(/dep_(accept|reject)_(\d+)/, async (ctx) => { 
    ctx.answerCbQuery(); 
    const action = ctx.match[1]; 
    const playerTelegramId = ctx.match[2]; 
    
    if (action === 'accept') { 
        // نقل حالة المشرف ليقوم بإدخال قيمة الشحن يدوياً لهذا اللاعب
        userStates[ctx.from.id] = { step: 'admin_entering_amount', targetPlayer: playerTelegramId, messageId: ctx.callbackQuery.message.message_id };
        await ctx.reply(`✏️ [${ctx.from.first_name}] يرجى كتابة المبلغ الدقيق المراد شحنه الآن لهذا اللاعب بالخاص (أرقام فقط دون فواصل):`);
    } else { 
        await ctx.editMessageCaption(`💰 *إيصال تعبئة فريق بحر:*\n\n❌ تم *رفض* هذا الإيصال وإلغاء المعاملة بواسطة: [${ctx.from.first_name}](tg://user?id=${ctx.from.id})`, { parse_mode: 'Markdown' }); 
        try { 
            await bot.telegram.sendMessage(playerTelegramId, `❌ *تنبيه من إدارة فريق بحر:*\n\nعذراً، تمت مراجعة إيصالك وتبيّن أن البيانات مدخلة بشكل *خاطئ* أو غير واصلة. تم *رفض* الطلب. يرجى التأكد وإعادة المحاولة.`, { parse_mode: 'Markdown' }); 
        } catch (e) {} 
    } 
}); 

// 5. استقبال وإعادة توجيه الرسائل والصور والحالات التفاعلية
bot.on('message', async (ctx) => { 
    const userId = ctx.from.id; 
    const state = userStates[userId];

    // أ) استقبال إيصالات الصور من اللاعبين وإرسالها للإدارة
    if (ctx.message.photo && state?.step === 'awaiting_receipt') {
        userStates[userId] = null; // إنهاء الحالة
        await bot.telegram.sendPhoto(ADMIN_GROUP_ID, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
            caption: `💰 *إيصال شحن جديد واصل:*\n\n• من اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n• معرف التلغرام (ID): \`ID: ${userId}\`\n\n💬 النص المرفق من اللاعب:\n${ctx.message.caption || 'لا يوجد'}`,
            parse_mode: 'Markdown',
            ...Markup.inlineKeyboard([
                [Markup.button.callback('✅ قبول وإدخال رصيد', `dep_accept_${userId}`)],
                [Markup.button.callback('❌ رفض الطلب', `dep_reject_${userId}`)]
            ])
        });
        return ctx.reply('✅ تم إرسال إيصالك بنجاح إلى قسم التدقيق والمالية، يرجى الانتظار لحين مراجعته من قبل المشرفين.');
    }

    // ب) معالجة قيام المشرف بكتابة مبلغ الشحن بالرقم الدقيق
    if (state?.step === 'admin_entering_amount' && ctx.message.text) {
        const amount = parseInt(ctx.message.text.replace(/[^0-8]/g, ''));
        if (isNaN(amount) || amount <= 0) {
            return ctx.reply('❌ يرجى إدخال مبلغ صحيح (أرقام فقط):');
        }

        const targetPlayer = state.targetPlayer;
        let accounts = {};
        if (fs.existsSync(ACCOUNTS_FILE)) {
            accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
        }

        if (!accounts[targetPlayer]) {
            // إذا لم يمتلك حساب نقوم بإنشاء حساب افتراضي له
            accounts[targetPlayer] = { gameId: "غير محدد", balance: 0 };
        }

        // إضافة الرصيد وحفظ الملف
        accounts[targetPlayer].balance += amount;
        fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4));
        userStates[userId] = null; // تصفير حالة الإدارة

        // تحديث رسالة الإيصال داخل القروب
        try {
