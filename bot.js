const { Telegraf, Markup } = require('telegraf'); 
const fs = require('fs'); 
const http = require('http'); 
const msgs = require('./messages'); // استدعاء ملف النصوص لحل المشكلة جذرياً

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
    accounts[userId] = { username, password, balance }; 
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
bot.hears('🏦 طلب سحب', (ctx) => { ctx.replyWithMarkdown(msgs.withdraw_rules, Markup.inlineKeyboard([[Markup.button.callback('Syriatel Cash 🇸🇾', 'withdraw_syriatel')], [Markup.button.callback('Sham Cash SYP 💳', 'withdraw_sham')]])); }); 

bot.action(/withdraw_(.+)/, (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'awaiting_withdraw_amount', method: ctx.match[1] }; ctx.reply('✏️ يرجى كتابة المبلغ المطلوب سحبه (أرقام فقط):'); }); 

bot.action(/reg_approve_(\d+)_([^_]+)_([^_]+)/, async (ctx) => { 
    ctx.answerCbQuery(); 
    savePlayerAccount(ctx.match[1], ctx.match[2], ctx.match[3], 0); 
    await ctx.editMessageText(`✅ تم تفعيل حساب المستخدم: \`${ctx.match[2]}\``); 
    try { await bot.telegram.sendMessage(ctx.match[1], `🎉 تم تفعيل حسابك بنجاح على الكاشير!\n• المستخدم: \`${ctx.match[2]}\``); } catch (e) {} 
}); 

bot.action(/reg_reject_(\d+)/, async (ctx) => { ctx.answerCbQuery(); await ctx.editMessageText(`❌ تم رفض طلب إنشاء الحساب.`); try { await bot.telegram.sendMessage(ctx.match[1], `❌ عذراً، تم رفض طلبك من قِبل الإدارة.`); } catch (e) {} }); 

bot.action(/charge_approve_(\d+)_(\d+)/, async (ctx) => {
    ctx.answerCbQuery();
    const playerTelegramId = ctx.match[1]; const amount = parseInt(ctx.match[2]);
    let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
    if (accounts[playerTelegramId]) {
        accounts[playerTelegramId].balance += amount; fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4));
        await ctx.editMessageCaption(`✅ تم شحن الحساب بمبلغ *${amount.toLocaleString()} ل.س*`);
        try { await bot.telegram.sendMessage(playerTelegramId, `🎉 تم شحن حسابك بمبلغ *${amount.toLocaleString()} ل.س* بنجاح.`); } catch (e) {}
    }
});

bot.action(/charge_reject_(\d+)/, async (ctx) => { ctx.answerCbQuery(); await ctx.editMessageCaption(`❌ تم رفض إيصال الشحن.`); try { await bot.telegram.sendMessage(ctx.match[1], `❌ عذراً، تم رفض إيصال الشحن المرفوع.`); } catch (e) {} });

bot.on('message', async (ctx) => { 
    const userId = ctx.from.id; const text = ctx.message.text; const currentState = userStates[userId]?.step; 

    if (userStates[userId]?.step === 'awaiting_payment_proof' && (ctx.message.photo || text)) {
        const method = userStates[userId].method; const captionText = ctx.message.caption || text || "";
        const amountMatch = captionText.match(/\d+/); const amount = amountMatch ? parseInt(amountMatch) : 0;
        const account = getPlayerAccount(userId); delete userStates[userId];

        if (ctx.message.photo) {
            await bot.telegram.sendPhoto(ADMIN_GROUP_ID, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
                caption: `💰 إيصال شحن جديد (${method}):\n• كاشير: \`${account?.username || 'لا يوجد'}\`\n• المبلغ: *${amount.toLocaleString()} ل.س*\n• الـ ID: \`معرف التلغرام: ${userId}\``,
                ...Markup.inlineKeyboard([[Markup.button.callback(`🟢 قبول وشحن ${amount.toLocaleString()}`, `charge_approve_${userId}_${amount}`)], [Markup.button.callback('🔴 رفض', `charge_reject_${userId}`)]])
            });
        }
        return ctx.reply('⏳ تم رفع إيصال الشحن بنجاح لتدقيقه.');
    }

    if (currentState === 'awaiting_username' && text) { userStates[userId] = { step: 'awaiting_password', username: text }; return ctx.reply('🔒 الآن أرسل كلمة السر المطلوبة للحساب:'); } 
    if (currentState === 'awaiting_password' && text) { 
        const username = userStates[userId].username; delete userStates[userId];
        await bot.telegram.sendMessage(ADMIN_GROUP_ID, `🔔 طلب حساب جديد:\n• المستخدم: \`${username}\`\n• كلمة السر: \`${text}\`\n• الـ ID: \`معرف التلغرام: ${userId}\``, 
            Markup.inlineKeyboard([[Markup.button.callback('🟢 تفعيل وتأكيد', `reg_approve_${userId}_${username}_${text}`)], [Markup.button.callback('🔴 رفض', `reg_reject_${userId}`)]])); 
        return ctx.reply('⏳ تم إرسال طلبك للإدارة، يرجى الانتظار لحين التفعيل.'); 
    } 

    if (currentState === 'admin_awaiting_player_id' && text && isOwner(userId)) {
        if (!getPlayerAccount(text.trim())) return ctx.reply('❌ غير مسجل.');
        userStates[userId] = { step: 'admin_awaiting_balance_change', targetId: text.trim() };
        return ctx.reply(`✏️ أرسل القيمة الكلية للرصيد الجديد الآن:`);
    }

    if (currentState === 'admin_awaiting_balance_change' && text && isOwner(userId)) {
        const targetId = userStates[userId].targetId; const newBalance = parseInt(text.trim()); delete userStates[userId];
        let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
