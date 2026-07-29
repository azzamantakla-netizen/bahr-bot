const { Telegraf, Markup } = require('telegraf'); 
const fs = require('fs'); 
const http = require('http'); 

const BOT_TOKEN = '8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8'; 
const bot = new Telegraf(BOT_TOKEN); 
const OWNER_ID = 6693251012; 
const ADMIN_GROUP_ID = -1003983996094; 
const SETTINGS_FILE = './settings.json'; 
const USERS_FILE = './users.json'; 
const ACCOUNTS_FILE = './accounts.json'; 
let userStates = {}; 

const msgs = {
    welcome_msg: "مرحبا بك في عائلتنا صمم هذا البوت باحترافية عالية ليقدم لك تجربة من نوع آخر نقدم لك سرعة عالية في الايداع ومرونة عالية في السحب تفضل بالاختيار من القائمة بحسب الزر الذي يلبي طلبك",
    technical_support: "❤️ لا تقلق نحن معك وفريقنا جاهز لخدمتك على مدار الساعة، فقط اكتب المشكلة أو الاستفسار بالتفصيل وأرسله الآن وسنقوم بالرد عليك فوراً:",
    withdraw_rules: "📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك:",
    syriatel_charge: "*Syriatel Cash 🇸🇾*\n\nيرجى تحويل المبلغ إلى الرقم التابع لنا:\n➡️ `{code}`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.",
    cham_charge: "*شام كاش (Cham Cash) 💳*\n\nيرجى تحويل المبلغ إلى عنوان المحفظة:\n➡️ `{wallet}`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ."
};

function loadSettings() { 
    if (!fs.existsSync(SETTINGS_FILE)) { 
        const defaultSettings = { 
            owners: ["6693251012"], admins: [], 
            syriatel_code: '48122120', cham_wallet: 'a18758d5324eb7595d4463ca355ad221', 
            cashier_user: 'Bero@yahoo.com', cashier_pass: 'Aazzam@318', 
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
    let accounts = fs.existsSync(ACCOUNTS_FILE) ? JSON.parse(fs.readFileSync(ACCOUNTS_FILE)) : {}; 
    accounts[userId] = { username: username, password: password, balance: balance }; 
    fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); 
} 

function deletePlayerAccount(userId) {
    if (!fs.existsSync(ACCOUNTS_FILE)) return;
    let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
    if (accounts[userId]) { delete accounts[userId]; fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); }
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

bot.start((ctx) => { ctx.reply(loadSettings().welcome_msg, getMainMenu(ctx.from.id)); }); 
bot.hears('🔙 العودة للقائمة الرئيسية', (ctx) => { ctx.reply('تم العودة للقائمة الرئيسية بنجاح.', getMainMenu(ctx.from.id)); }); 
bot.hears('📞 الدعم الفني', (ctx) => { userStates[ctx.from.id] = { step: 'awaiting_support_msg' }; ctx.reply(msgs.technical_support); }); 

bot.hears('👤 حسابي الفردي', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id); 
    if (!account) { 
        return ctx.reply('❌ حسابك غير مسجل.\n\nاضغط لإنشاء حساب وتعيين البيانات:', Markup.inlineKeyboard([[Markup.button.callback('🆕 إنشاء حساب جديد', 'register_account')]])); 
    } 
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي:*\n\n• اسم المستخدم: \`${account.username}\`\n• رصيدك الحالي: *${account.balance.toLocaleString()}* ل.س`, 
        Markup.inlineKeyboard([[Markup.button.callback('❌ حذف حسابي من البوت', 'confirm_delete_acc')]])); 
}); 

bot.action('confirm_delete_acc', (ctx) => {
    ctx.answerCbQuery();
    ctx.editMessageText('⚠️ هل أنت متأكد من حذف حسابك نهائياً؟', Markup.inlineKeyboard([[Markup.button.callback('✅ احذف', 'execute_delete_acc')], [Markup.button.callback('🔙 إلغاء', 'cancel_delete_acc')]]));
});
bot.action('execute_delete_acc', (ctx) => { ctx.answerCbQuery(); deletePlayerAccount(ctx.from.id); ctx.editMessageText('🗑️ تم حذف بيانات حسابك بالكامل.'); });
bot.action('cancel_delete_acc', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('تم إلغاء عملية الحذف.'); });
bot.action('register_account', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'awaiting_username' }; ctx.reply('✏️ يرجى كتابة اسم المستخدم (Username) الجديد:'); }); 

bot.hears('⚙️ لوحة تحكم الإدارة', (ctx) => { 
    if (!isOwner(ctx.from.id)) return ctx.reply('❌ مخصص للمالك فقط.'); 
    ctx.reply('⚙️ لوحة تحكم الإدارة الشاملة:', getAdminMenu()); 
}); 

bot.hears('⚙️ تعديل رصيد لاعب', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'admin_awaiting_player_id' };
    ctx.reply('✏️ أرسل معرف التلغرام (Telegram ID) الخاص باللاعب:');
});

bot.hears('💰 شحن الرصيد', (ctx) => { 
    if (!getPlayerAccount(ctx.from.id)) return ctx.reply('❌ يجب عليك إنشاء حساب أولاً قبل البدء بعمليات الشحن.');
    ctx.reply('اختر طريقة الدفع المناسبة:', Markup.inlineKeyboard([[Markup.button.callback('Syriatel Cash 🇸🇾', 'show_syriatel')], [Markup.button.callback('شام كاش (Cham Cash) 💳', 'show_cham')]])); 
}); 

bot.action('show_syriatel', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'awaiting_payment_proof', method: 'Syriatel Cash' }; ctx.replyWithMarkdown(msgs.syriatel_charge.replace('{code}', loadSettings().syriatel_code)); }); 
bot.action('show_cham', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'awaiting_payment_proof', method: 'Cham Cash' }; ctx.replyWithMarkdown(msgs.cham_charge.replace('{wallet}', loadSettings().cham_wallet)); }); 

bot.hears('🏦 طلب سحب', (ctx) => { 
    ctx.replyWithMarkdown(msgs.withdraw_rules, Markup.inlineKeyboard([
        [Markup.button.callback('Syriatel Cash 🇸🇾', 'w_syriatel')], 
        [Markup.button.callback('Sham Cash SYP 💳', 'w_sham')]
    ])); 
}); 

bot.action('w_syriatel', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'awaiting_withdraw_amount', method: 'Syriatel Cash' }; ctx.reply('✏️ يرجى كتابة المبلغ المطلوب سحبه (أرقام فقط):'); });
bot.action('w_sham', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'awaiting_withdraw_amount', method: 'Sham Cash SYP' }; ctx.reply('✏️ يرجى كتابة المبلغ المطلوب سحبه (أرقام فقط):'); });

// تم استبدال الـ Regex القاتل بأزرار نصية مباشرة وثابتة ومحميّة بالكامل
bot.action('chg_app', async (ctx) => {
    ctx.answerCbQuery();
    ctx.reply('تنبيه للمشرف: يرجى استخدام أمر لوحة التحكم الإدارية لتعديل الرصيد بدقة لضمان الأمان المالي الكامل.');
});
bot.action('chg_rej', (ctx) => { ctx.answerCbQuery(); ctx.editMessageCaption('❌ تم رفض إيصال الشحن.'); });
bot.action('reg_app', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('✅ تم التفعيل بنجاح (يرجى مراجعة ملف الحسابات المحدث).'); });
bot.action('reg_rej', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('❌ تم رفض الطلب.'); });

bot.on('message', async (ctx) => { 
    const userId = ctx.from.id; const text = ctx.message.text; const currentState = userStates[userId]?.step; 

    if (userStates[userId]?.step === 'awaiting_payment_proof' && (ctx.message.photo || text)) {
        const method = userStates[userId].method; const captionText = ctx.message.caption || text || "";
        const amountMatch = captionText.match(/\d+/); const amount = amountMatch ? parseInt(amountMatch) : 0;
        const account = getPlayerAccount(userId); delete userStates[userId];

        if (ctx.message.photo) {
            await bot.telegram.sendPhoto(ADMIN_GROUP_ID, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
                caption: `💰 إيصال شحن جديد (${method}):\n• كاشير: \`${account?.username || 'لا يوجد'}\`\n• المبلغ: *${amount.toLocaleString()} ل.س*\n• الـ ID: \`معرف التلغرام: ${userId}\``,
                ...Markup.inlineKeyboard([[Markup.button.callback('🟢 قبول الإيصال', 'chg_app')], [Markup.button.callback('🔴 رفض الإيصال', 'chg_rej')]])
            });
        }
        return ctx.reply('⏳ تم رفع إيصال الشحن بنجاح لتدقيقه من قِبل المشرفين.');
    }

    if (currentState === 'awaiting_username' && text) { userStates[userId] = { step: 'awaiting_password', username: text }; return ctx.reply('🔒 الآن أرسل كلمة السر المطلوبة للحساب:'); } 
    if (currentState === 'awaiting_password' && text) { 
        const username = userStates[userId].username; delete userStates[userId];
        await bot.telegram.sendMessage(ADMIN_GROUP_ID, `🔔 طلب حساب جديد:\n• المستخدم: \`${username}\`\n• كلمة السر: \`${text}\`\n• الـ ID: \`معرف التلغرام: ${userId}\``, 
            Markup.inlineKeyboard([[Markup.button.callback('🟢 تفعيل وتأكيد', 'reg_app')], [Markup.button.callback('🔴 رفض الطلب', 'reg_rej')]])); 
        return ctx.reply('⏳ تم إرسال طلبك للإدارة، يرجى الانتظار لحين التفعيل.'); 
    } 

    if (currentState === 'admin_awaiting_player_id' && text && isOwner(userId)) {
        if (!getPlayerAccount(text.trim())) return ctx.reply('❌ غير مسجل.');
        userStates[userId] = { step: 'admin_awaiting_balance_change', targetId: text.trim() };
        return ctx.reply('✏️ أرسل القيمة الكلية للرصيد الجديد الآن (أرقام فقط):');
    }

    if (currentState === 'admin_awaiting_balance_change' && text && isOwner(userId)) {
        const targetId = userStates[userId].targetId; const newBalance = parseInt(text.trim()); delete userStates[userId];
        let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
