const { Telegraf, Markup } = require('telegraf');
const fs = require('fs');

const BOT_TOKEN = '8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8'; 
const bot = new Telegraf(BOT_TOKEN);

const OWNER_ID = 6693251012;
const ADMIN_GROUP_ID = -1003983996094;
const SETTINGS_FILE = './settings.json';
const USERS_FILE = './users.json';
const ACCOUNTS_FILE = './accounts.json';

let userStates = {};
const WITHDRAW_RULES = { min: 200000, max: 2000000, feePercent: 10 };

function loadSettings() {
    if (!fs.existsSync(SETTINGS_FILE)) {
        const defaultSettings = {
            owners:, 
            admins: [],          
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

function saveSettings(settings) {
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 4));
}

function isOwner(userId) {
    const s = loadSettings();
    return s.owners.includes(userId);
}

function getPlayerAccount(userId) {
    if (!fs.existsSync(ACCOUNTS_FILE)) return null;
    const accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
    return accounts[userId] || null;
}

function savePlayerAccount(userId, gameId, balance = 0) {
    let accounts = {};
    if (fs.existsSync(ACCOUNTS_FILE)) { accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE)); }
    accounts[userId] = { gameId: gameId, balance: balance };
    fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4));
}

function saveUser(userId) {
    let users = [];
    if (fs.existsSync(USERS_FILE)) { users = JSON.parse(fs.readFileSync(USERS_FILE)); }
    if (!users.includes(userId)) {
        users.push(userId);
        fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 4));
    }
}

function getMainMenu(userId) {
    let keyboard = [['💰 شحن الرصيد', '🏦 طلب سحب'], ['👤 حسابي الفردي', '📞 الدعم الفني']];
    if (isOwner(userId)) { keyboard.push(['⚙️ لوحة تحكم الإدارة']); }
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

bot.start((ctx) => {
    const userId = ctx.from.id;
    saveUser(userId);
    const s = loadSettings();
    const customizedWelcome = s.welcome_msg.replace('{name}', ctx.from.first_name || 'اللاعب');
    ctx.replyWithMarkdown(customizedWelcome, getMainMenu(userId));
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
    if (!isOwner(ctx.from.id)) return ctx.reply('❌ عذراً، هذا القسم مخصص لمالك البوت فقط.');
    ctx.reply('⚙️ أهلاً بك في لوحة تحكم الإدارة الشاملة. اختر الإجراء المطلوب:', getAdminMenu());
});

bot.hears('📞 تعديل سيريتل كاش', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'edit_syriatel' };
    ctx.reply('✏️ يرجى إرسال رقم السيريتل كاش الجديد الآن:');
});

bot.hears('💳 تعديل شام كاش', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'edit_cham' };
    ctx.reply('✏️ يرجى إرسال عنوان محفظة شام كاش الجديدة الآن:');
});

bot.hears('📝 تعديل رسالة الترحيب', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'edit_welcome' };
    ctx.replyWithMarkdown('✏️ أرسل رسالة الترحيب الجديدة الآن، ضع كلمة `{name}` مكان اسم اللاعب.');
});

bot.hears('📢 إرسال إذاعة', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'broadcast_msg' };
    ctx.reply('📢 يرجى كتابة وإرسال نص الرسالة المراد إذاعتها لجميع المشتركين:');
});

bot.hears('➕ إضافة مالك جديد', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'add_owner' };
    ctx.reply('✏️ يرجى إرسال المعرف الرقمي (ID) الخاص بالمالك الجديد:');
});

bot.hears('➕ إضافة مشرف جديد', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'add_admin' };
    ctx.reply('✏️ يرجى إرسال المعرف الرقمي (ID) الخاص بالمشرف الجديد:');
});

bot.hears('📧 تعديل إيميل الكاشير', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'edit_cashier_user' };
    ctx.reply('✏️ يرجى إرسال البريد الإلكتروني (Email) الجديد الخاص بالكاشير الآن:');
});

bot.hears('🔑 تعديل باسورد الكاشير', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'edit_cashier_pass' };
    ctx.reply('✏️ يرجى إرسال كلمة المرور (Password) الجديدة الخاصة بالكاشير الآن:');
});

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

bot.on('message', async (ctx) => {
    const userId = ctx.from.id;
    const currentState = userStates[userId]?.step;
    
    if (ctx.chat.id === ADMIN_GROUP_ID && ctx.message.reply_to_message) {
        const replyText = ctx.message.reply_to_message.text || ctx.message.reply_to_message.caption;
        if (replyText && replyText.includes('ID:')) {
            const matches = replyText.match(/ID:\s*(\d+)/);
            if (matches && matches) {
                try {
                    await bot.telegram.sendMessage(matches[1], `📬 *رد من إدارة فريق بحر على استفسارك:*\n\n💬 ${ctx.message.text}`, { parse_mode: 'Markdown' });
                    return ctx.reply('✅ تم إرسال ردك إلى اللاعب بنجاح.');
                } catch (err) {
                    return ctx.reply('❌ فشل إرسال الرد، قد يكون اللاعب قد حظر البوت.');
                }
            }
        }
    }

    if (currentState) {
        const s = loadSettings();
        
        if (currentState === 'awaiting_game_id') {
            savePlayerAccount(userId, ctx.message.text, 0);
            delete userStates[userId];
            return ctx.reply(`🎉 تم إنشاء حسابك بنجاح وربطه بمعرف اللعبة: ${ctx.message.text}\nرصيدك الحالي هو: 0 ل.س`, getMainMenu(userId));
        }
        if (currentState === 'edit_syriatel') {
            s.syriatel_code = ctx.message.text; saveSettings(s); delete userStates[userId];
            return ctx.reply(`✅ تم تحديث رقم سيريتل كاش بنجاح إلى: ${ctx.message.text}`, getAdminMenu());
        }
        if (currentState === 'edit_cham') {
            s.cham_wallet = ctx.message.text; saveSettings(s); delete userStates[userId];
            return ctx.reply(`✅ تم تحديث محفظة شام كاش بنجاح إلى: ${ctx.message.text}`, getAdminMenu());
        }
        if (currentState === 'edit_welcome') {
