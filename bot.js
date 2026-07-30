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

const WITHDRAW_RULES = { min: 200000, max: 2000000, feePercent: 10 }; 

const msgs = {
    welcome_msg: "مرحباً بك في عائلتنا! تم تصميم هذا البوت باحترافية عالية ليقدم لك تجربة ماليّة مرنة وسريعة في عمليات الإيداع والسحب. تفضل بالاختيار من القائمة أدناه بما يلبي طلبك:",
    technical_support: "❤️ لا تقلق، فريق الدعم الفني جاهز لخدمتك على مدار الساعة. اكتب استفسارك أو مشكلتك بالتفصيل الآن وسنقوم بالرد عليك فوراً:",
    withdraw_rules: "📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك الآن:",
    syriatel_charge: "*Syriatel Cash 🇸🇾*\n\nيرجى تحويل المبلغ إلى الرقم التابع لنا:\n➡️ `{code}`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة واكتب في وصفها المبلغ الذي قمت بتحويله.",
    cham_charge: "*شام كاش (Cham Cash) 💳*\n\nيرجى تحويل المبلغ إلى عنوان المحفظة التالية:\n➡️ `{wallet}`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة واكتب في وصفها المبلغ الذي قمت بتحويله."
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
    if (accounts[userId]) { 
        delete accounts[userId]; 
        fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); 
    }
}

function getMainMenu(userId) { 
    let keyboard = [['💰 شحن الرصيد', '🏦 طلب سحب'], ['👤 حسابي الفردي', '📞 الدعم الفني']]; 
    if (isOwner(userId)) { keyboard.push(['⚙️ لوحة الإدارة']); }
    return Markup.keyboard(keyboard).resize(); 
} 

function getAdminMenu() { 
    return Markup.keyboard([['⚙️ تعديل رصيد لاعب', '🔙 العودة للقائمة الرئيسية']]).resize(); 
} 

bot.start((ctx) => { ctx.reply(loadSettings().welcome_msg, getMainMenu(ctx.from.id)); }); 
bot.hears('🔙 العودة للقائمة الرئيسية', (ctx) => { ctx.reply('تمت العودة للقائمة الرئيسية بنجاح.', getMainMenu(ctx.from.id)); }); 
bot.hears('📞 الدعم الفني', (ctx) => { userStates[ctx.from.id] = { step: 'support' }; ctx.reply(msgs.technical_support); }); 

bot.hears('👤 حسابي الفردي', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id); 
    if (!account) { 
        return ctx.reply('❌ حسابك غير مسجل في نظام البوت حتى الآن.\n\nيرجى الضغط على الزر أدناه لإنشاء حسابك وتعيين بيانات الدخول الخاصة بك:', Markup.inlineKeyboard([[Markup.button.callback('🆕 إنشاء حساب جديد', 'register_account')]])); 
    } 
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي الموثق:*\n\n• اسم المستخدم: \`${account.username}\`\n• رصيدك الحالي: *${account.balance.toLocaleString()}* ل.س\n\n📌 يتم تحديث الرصيد تلقائياً عند موافقة الإدارة على إيصالات الشحن الخاصة بك.`, 
        Markup.inlineKeyboard([[Markup.button.callback('❌ حذف حسابي نهائياً', 'confirm_delete_acc')]])); 
}); 

bot.action('confirm_delete_acc', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('⚠️ هل أنت متأكد تماماً من رغبتك في حذف حسابك نهائياً؟', Markup.inlineKeyboard([[Markup.button.callback('✅ نعم، احذف', 'execute_delete_acc')], [Markup.button.callback('🔙 إلغاء وتراجع', 'cancel_delete_acc')]])); });
bot.action('execute_delete_acc', (ctx) => { ctx.answerCbQuery(); deletePlayerAccount(ctx.from.id); ctx.editMessageText('🗑️ تم حذف بيانات حسابك بالكامل من نظام البوت بنجاح.'); });
bot.action('cancel_delete_acc', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('تم إلغاء عملية الحذف وبقاء حسابك آمناً.'); });
bot.action('register_account', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'username' }; ctx.reply('✏️ يرجى كتابة اسم المستخدم (Username) الذي تريده للحساب الآن:'); }); 

bot.hears('⚙️ لوحة الإدارة', (ctx) => { 
    if (!isOwner(ctx.from.id)) return ctx.reply('❌ هذا القسم مخصص لمالك البوت فقط.'); 
    ctx.reply('⚙️ أهلاً بك في لوحة تحكم الإدارة الشاملة. اختر الإجراء المطلوب:', getAdminMenu()); 
}); 

bot.hears('⚙️ تعديل رصيد لاعب', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'admin_id' };
    ctx.reply('✏️ يرجى إرسال معرف التلغرام (Telegram ID) الخاص باللاعب المراد تعديل رصيده:');
});

bot.hears('💰 شحن الرصيد', (ctx) => { 
    if (!getPlayerAccount(ctx.from.id)) return ctx.reply('❌ يجب عليك إنشاء حساب أولاً قبل البدء بعمليات الشحن.');
    ctx.reply('اختر طريقة الدفع المناسبة لك لإرسال الأموال وتعبئة حسابك:', Markup.inlineKeyboard([[Markup.button.callback('Syriatel Cash 🇸🇾', 'sh_syr')], [Markup.button.callback('شام كاش (Cham Cash) 💳', 'sh_cham')]])); 
}); 

bot.action('sh_syr', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'proof', method: 'Syriatel Cash' }; ctx.replyWithMarkdown(msgs.syriatel_charge.replace('{code}', loadSettings().syriatel_code)); }); 
bot.action('sh_cham', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'proof', method: 'Cham Cash' }; ctx.replyWithMarkdown(msgs.cham_charge.replace('{wallet}', loadSettings().cham_wallet)); }); 

bot.hears('🏦 طلب سحب', (ctx) => { 
    if (!getPlayerAccount(ctx.from.id)) return ctx.reply('❌ يجب عليك إنشاء حساب أولاً قبل البدء بعمليات السحب.');
    ctx.replyWithMarkdown(msgs.withdraw_rules, Markup.inlineKeyboard([[Markup.button.callback('Syriatel Cash 🇸🇾', 'w_syr')], [Markup.button.callback('Cham Cash SYP 💳', 'w_cham')]])); 
}); 

bot.action('w_syr', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'w_amt', method: 'Syriatel Cash' }; ctx.reply('✏️ يرجى كتابة المبلغ الذي ترغب بسحبه بالليرة السورية (أرقام فقط):'); });
bot.action('w_cham', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'w_amt', method: 'Cham Cash' }; ctx.reply('✏️ يرجى كتابة المبلغ الذي ترغب بسحبه بالليرة السورية (أرقام فقط):'); });

bot.action('admin_approve_action', async (ctx) => {
    ctx.answerCbQuery();
    ctx.reply('تنبيه للمشرف: يرجى تنفيذ إجراءات التعديل المباشر والآمن من خلال لوحة تحكم الإدارة النصية لضمان استقرار الملفات.');
});
bot.action('admin_reject_action', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('❌ تم رفض الطلب وإلغاء المعاملة بواسطة المشرف.'); });

bot.on('message', async (ctx) => { 
    try {
        const userId = ctx.from.id; const text = ctx.message.text; const currentState = userStates[userId]?.step; 

        if (userStates[userId]?.step === 'proof' && (ctx.message.photo || text)) {
            const method = userStates[userId].method; const captionText = ctx.message.caption || text || "";
            let amount = 0;
            // استخراج الأرقام بنظام نصي خالص بدون استخدام RegExp
            let numStr = "";
            for (let i = 0; i < captionText.length; i++) {
                if (captionText[i] >= '0' && captionText[i] <= '9') { numStr += captionText[i]; }
            }
            if (numStr.length > 0) { amount = parseInt(numStr); }
            
            const account = getPlayerAccount(userId); delete userStates[userId];

            if (ctx.message.photo) {
                await bot.telegram.sendPhoto(ADMIN_GROUP_ID, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
                    caption: `💰 إيصال شحن جديد واصل (${method}):\n\n• اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n• حساب الكاشير: \`${account?.username || 'لا يوجد'}\`\n• المبلغ المحدد: *${amount.toLocaleString()} ل.س*\n\n• معرف اللاعب التلغرام: \`TGID:${userId}\``,
                    parse_mode: 'Markdown',
                    ...Markup.inlineKeyboard([[Markup.button.callback('🟢 قبول وإرسال إشعار', 'admin_approve_action')], [Markup.button.callback('🔴 رفض الإيصال', 'admin_reject_action')]])
                });
            }
            return ctx.reply('⏳ تم رفع إيصال شحنك بنجاح لقسم المالية والتدقيق المالي، يرجى الانتظار لحين مراجعته.');
        }

        if (currentState === 'username' && text) { userStates[userId] = { step: 'password', username: text }; return ctx.reply('🔒 ممتاز، الآن يرجى كتابة كلمة السر (Password) المطلوبة لحسابك لإتمام التسجيل:'); } 
        if (currentState === 'password' && text) { 
            const username = userStates[userId].username; delete userStates[userId];
            await bot.telegram.sendMessage(ADMIN_GROUP_ID, `🔔 طلب إنشاء حساب جديد واصل:\n\n• اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n• اسم المستخدم: \`${username}\`\n• كلمة المرور: \`${text}\`\n\n• معرف اللاعب التلغرام: \`TGID:${userId}\``, 
                { parse_mode: 'Markdown', ...Markup.inlineKeyboard([[Markup.button.callback('🟢 موافقة وتفعيل الحساب', 'admin_approve_action')], [Markup.button.callback('🔴 رفض الطلب', 'admin_reject_action')]]) }); 
