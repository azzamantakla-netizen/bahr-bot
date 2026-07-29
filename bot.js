const { Telegraf, Markup } = require('telegraf'); 
const fs = require('fs'); 
const http = require('http'); 

const msgs = {
    welcome_msg: `مرحبا بك في عائلتنا صمم هذا البوت باحترافية عالية ليقدم لك تجربة من نوع آخر نقدم لك سرعة عالية في الايداع ومرونة عالية في السحب تفضل بالاختيار من القائمة بحسب الزر الذي يلبي طلبك`,
    technical_support: `❤️ لا تقلق نحن معك وفريقنا جاهز لخدمتك على مدار الساعة، فقط اكتب المشكلة أو الاستفسار بالتفصيل وأرسله الآن وسنقوم بالرد عليك فوراً:`,
    withdraw_rules: `📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك:`,
    syriatel_charge: `*Syriatel Cash 🇸🇾*\n\nيرجى تحويل المبلغ إلى الرقم التابع لنا:\n➡️ \`{code}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`,
    cham_charge: `*شام كاش (Cham Cash) 💳*\n\nيرجى تحويل المبلغ إلى عنوان المحفظة:\n➡️ \`{wallet}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`
};

const BOT_TOKEN = '8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8'; 
const bot = new Telegraf(BOT_TOKEN); 
const OWNER_ID = 6693251012; 
const ADMIN_GROUP_ID = -1003983996094; 
const SETTINGS_FILE = './settings.json'; 
const USERS_FILE = './users.json'; 
const ACCOUNTS_FILE = './accounts.json'; 
let userStates = {}; 

function loadSettings() { 
    if (!fs.existsSync(SETTINGS_FILE)) { 
        const defaultSettings = { 
            owners: ["6693251012"], 
            admins: [], 
            syriatel_code: '48122120', 
            cham_wallet: 'a18758d5324eb7595d4463ca355ad221', 
            cashier_user: 'Bero@yahoo.com', 
            cashier_pass: 'Aazzam@318', 
            welcome_msg: msgs.welcome_msg 
        }; 
        fs.writeFileSync(SETTINGS_FILE, JSON.stringify(defaultSettings, null, 4)); 
        return defaultSettings; 
    } 
    return JSON.parse(fs.readFileSync(SETTINGS_FILE)); 
} 

function isOwner(userId) { 
    return loadSettings().owners.includes(String(userId)) || userId === OWNER_ID; 
} 

function getPlayerAccount(userId) { 
    if (!fs.existsSync(ACCOUNTS_FILE)) return null; 
    return JSON.parse(fs.readFileSync(ACCOUNTS_FILE))[userId] || null; 
} 

function savePlayerAccount(userId, username, password, balance = 0) { 
    let accounts = {}; 
    if (fs.existsSync(ACCOUNTS_FILE)) { 
        accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE)); 
    } 
    accounts[userId] = { username: username, password: password, balance: balance }; 
    fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); 
} 

function deletePlayerAccount(userId) {
    if (!fs.existsSync(ACCOUNTS_FILE)) return;
    let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
    if (accounts[userId]) {
        delete accounts[userId];
        fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4));
    }
}

function getMainMenu(userId) { 
    let keyboard = [['💰 شحن الرصيد', '🏦 طلب سحب'], ['👤 حسابي الفردي', '📞 الدعم الفني']]; 
    if (isOwner(userId)) keyboard.push(['⚙️ لوحة تحكم الإدارة']); 
    return Markup.keyboard(keyboard).resize(); 
} 

function getAdminMenu() { 
    return Markup.keyboard([ 
        ['⚙️ تعديل رصيد لاعب', '📝 تعديل رسالة الترحيب'],
        ['📞 تعديل سيريتل كاش', '💳 تعديل شام كاش'], 
        ['📢 إرسال إذاعة', '🔙 العودة للقائمة الرئيسية'] 
    ]).resize(); 
} 

bot.start((ctx) => { 
    ctx.reply(loadSettings().welcome_msg, getMainMenu(ctx.from.id)); 
}); 

bot.hears('🔙 العودة للقائمة الرئيسية', (ctx) => { 
    ctx.reply('تم العودة للقائمة الرئيسية بنجاح.', getMainMenu(ctx.from.id)); 
}); 

bot.hears('📞 الدعم الفني', (ctx) => { 
    userStates[ctx.from.id] = { step: 'awaiting_support_msg' }; 
    ctx.reply(msgs.technical_support); 
}); 

bot.hears('👤 حسابي الفردي', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id); 
    if (!account) { 
        return ctx.reply('❌ حسابك غير مسجل في نظام البوت حتى الآن.\n\nيرجى الضغط على الزر أدناه لإنشاء حسابك وتعيين بيانات الدخول الخاصة بك:', 
            Markup.inlineKeyboard([[Markup.button.callback('🆕 إنشاء حساب جديد', 'register_account')]]) 
        ); 
    } 
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي الموثق:*\n\n• الاسم: *${ctx.from.first_name}*\n• اسم المستخدم: \`${account.username}\`\n• رصيدك الحالي: *${account.balance.toLocaleString()}* ل.س\n\n📌 يتم تحديث الرصيد تلقائياً عند موافقة الإدارة على إيصالات الشحن الخاصة بك.`, 
        Markup.inlineKeyboard([[Markup.button.callback('❌ حذف حسابي من البوت', 'confirm_delete_acc')]])
    ); 
}); 

bot.action('confirm_delete_acc', (ctx) => {
    ctx.answerCbQuery();
    ctx.editMessageText('⚠️ *تنبيه حرج:* هل أنت متأكد تماماً من رغبتك في حذف حسابك نهائياً من نظام البوت؟ لا يمكن التراجع عن هذا الإجراء.', {
        parse_mode: 'Markdown',
        ...Markup.inlineKeyboard([
            [Markup.button.callback('✅ نعم، احذف الحساب', 'execute_delete_acc')],
            [Markup.button.callback('🔙 إلغاء والعودة', 'cancel_delete_acc')]
        ])
    });
});

bot.action('execute_delete_acc', (ctx) => {
    ctx.answerCbQuery();
    deletePlayerAccount(ctx.from.id);
    ctx.editMessageText('🗑️ تم حذف بيانات حسابك بالكامل من نظام البوت بنجاح. يمكنك إنشاء حساب جديد في أي وقت تشاء.');
});

bot.action('cancel_delete_acc', (ctx) => {
    ctx.answerCbQuery();
    ctx.editMessageText('تم إلغاء عملية الحذف وبقاء حسابك آمناً.');
});

bot.action('register_account', (ctx) => { 
    ctx.answerCbQuery(); 
    userStates[ctx.from.id] = { step: 'awaiting_username' }; 
    ctx.reply('✏️ يرجى كتابة اسم المستخدم (Username) الذي تريده للحساب الآن:'); 
}); 

bot.hears('⚙️ لوحة تحكم الإدارة', (ctx) => { 
    if (!isOwner(ctx.from.id)) return ctx.reply('❌ مخصص للمالك فقط.'); 
    ctx.reply('⚙️ أهلاً بك في لوحة تحكم الإدارة الشاملة. اختر الإجراء المطلوب:', getAdminMenu()); 
}); 

bot.hears('⚙️ تعديل رصيد لاعب', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'admin_awaiting_player_id' };
    ctx.reply('✏️ يرجى إرسال معرف التلغرام (Telegram ID) الخاص باللاعب المراد تعديل رصيده:');
});

bot.hears('💰 شحن الرصيد', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id);
    if (!account) return ctx.reply('❌ يجب عليك إنشاء حساب أولاً قبل البدء بعمليات الشحن.');
    
    ctx.reply('اختر طريقة الدفع المناسبة:', Markup.inlineKeyboard([ 
        [Markup.button.callback('Syriatel Cash 🇸🇾', 'show_syriatel')], 
        [Markup.button.callback('شام كاش (Cham Cash) 💳', 'show_cham')] 
    ])); 
}); 

bot.action('show_syriatel', (ctx) => { 
    ctx.answerCbQuery(); 
    userStates[ctx.from.id] = { step: 'awaiting_payment_proof', method: 'Syriatel Cash' };
    ctx.replyWithMarkdown(msgs.syriatel_charge.replace('{code}', loadSettings().syriatel_code)); 
}); 

bot.action('show_cham', (ctx) => { 
    ctx.answerCbQuery(); 
    userStates[ctx.from.id] = { step: 'awaiting_payment_proof', method: 'Cham Cash' };
    ctx.replyWithMarkdown(msgs.cham_charge.replace('{wallet}', loadSettings().cham_wallet)); 
}); 

bot.hears('🏦 طلب سحب', (ctx) => { 
    ctx.replyWithMarkdown(msgs.withdraw_rules, Markup.inlineKeyboard([ 
        [Markup.button.callback('Syriatel Cash 🇸🇾', 'withdraw_syriatel')], 
        [Markup.button.callback('Sham Cash SYP 💳', 'withdraw_sham')] 
    ])); 
}); 

bot.action(/withdraw_(.+)/, (ctx) => { 
    ctx.answerCbQuery(); 
    userStates[ctx.from.id] = { step: 'awaiting_withdraw_amount', method: ctx.match[1] }; 
    ctx.reply('✏️ يرجى كتابة المبلغ المطلوب سحبه (أرقام فقط):'); 
}); 

bot.action(/reg_approve_(\d+)_([^_]+)_([^_]+)/, async (ctx) => { 
    ctx.answerCbQuery(); 
    const playerTelegramId = ctx.match[1]; 
    const username = ctx.match[2]; 
    const password = ctx.match[3]; 
    
    savePlayerAccount(playerTelegramId, username, password, 0); 
    
    await ctx.editMessageText(`✅ تم اعتماد وإنشاء الحساب في الكاشير بواسطة المشرف: [${ctx.from.first_name}](tg://user?id=${ctx.from.id})\n\n👤 المستخدم: \`${username}\``, { parse_mode: 'Markdown' }); 
    
    try { 
        await bot.telegram.sendMessage(playerTelegramId, `🎉 *خبر سار من فريق بحر:*\n\nتمت مراجعة طلبك وتفعيل حسابك بنجاح على الكاشير!\n\n• اسم المستخدم: \`${username}\`\n• كلمة المرور: \`${password}\``, { parse_mode: 'Markdown' }); 
    } catch (e) {} 
}); 

bot.action(/reg_reject_(\d+)/, async (ctx) => { 
    ctx.answerCbQuery(); 
    const playerTelegramId = ctx.match[1]; 
    await ctx.editMessageText(`❌ تم رفض طلب إنشاء الحساب بواسطة المشرف.`); 
    try { 
        await bot.telegram.sendMessage(playerTelegramId, `❌ عذراً، تم رفض طلب إنشاء حسابك من قِبل الإدارة. يرجى مراجعة الدعم الفني.`); 
    } catch (e) {} 
}); 

// معالجة قبول الإيصال وشحن الرصيد الفعلي في ملف الـ JSON تلقائياً
bot.action(/charge_approve_(\d+)_(\d+)/, async (ctx) => {
    ctx.answerCbQuery();
    const playerTelegramId = ctx.match[1];
    const amount = parseInt(ctx.match[2]);
    
    if (!fs.existsSync(ACCOUNTS_FILE)) return ctx.reply('❌ ملف الحسابات غير موجود.');
    let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
    
    if (accounts[playerTelegramId]) {
        accounts[playerTelegramId].balance += amount;
        fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4));
        
        await ctx.editMessageCaption(`💰 *معاملة شحن معتمدة:*\n\n✅ تم قبول الإيصال وشحن الحساب بمبلغ *${amount.toLocaleString()} ل.س* بواسطة: [${ctx.from.first_name}](tg://user?id=${ctx.from.id})`, { parse_mode: 'Markdown' });
        try {
            await bot.telegram.sendMessage(playerTelegramId, `🎉 *تم شحن حسابك بنجاح!*\n\nتمت إضافة *${amount.toLocaleString()} ل.س* إلى رصيدك المالي الموثق في البوت. تفقد حسابك الآن.`);
        } catch (e) {}
    } else {
        ctx.reply('❌ خطأ: الحساب غير موجود في ملف الـ JSON.');
    }
});

bot.action(/charge_reject_(\d+)/, async (ctx) => {
    ctx.answerCbQuery();
    const playerTelegramId = ctx.match[1];
    await ctx.editMessageCaption(`❌ تم *رفض* إيصال الشحن هذا وإلغاء الطلب بواسطة المشرف.`);
    try {
