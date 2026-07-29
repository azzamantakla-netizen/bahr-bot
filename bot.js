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

// النصوص مشفرة برمجياً لحل مشكلة السنتكس للأبد
const msgs = {
    welcome_msg: "\u0645\u0631\u062d\u0628\u0627\u064b\u0628\u0643\u0645\u0641\u064a\u0639\u0627\u0626\u0644\u062a\u0646\u0627\u060c\u062a\u0641\u0636\u0644\u0628\u0627\u0644\u0627\u062e\u062a\u064a\u0627\u0631\u0645\u0646\u0627\u0644\u0642\u0627\u0626\u0645\u0629\u0628\u062d\u0633\u0628\u0627\u0644\u0632\u0631\u0627\u0644\u0630\u064a\u064a\u0644\u0628\u064a\u0637\u0644\u0628\u0643",
    technical_support: "\u2764\ufe0f\u0644\u0627\u062a\u0642\u0644\u0642\u0646\u062d\u0646\u0645\u0639\u0643\u0606\u062d\u0646\u062c\u0627\u0647\u0632\u0648\u0646\u0644\u062e\u062f\u0645\u062a\u0643\u0606\u0627\u0643\u062a\u0628\u0627\u0644\u0645\u0634\u0643\u0644\u0629\u0628\u0627\u0644\u062a\u0641\u0635\u064a\u0644\u0648\u0623\u0631\u0633\u0644\u0647\u0627\u0627\u0644\u0622\u0646:",
    withdraw_rules: "\ud83d\udccd\u0634\u0631\u064e\u0648\u0637\u0648\u0642\u0648\u0627\u0646\u064a\u0646\u0627\u0644\u0633\u062d\u0628\u0644\u0641\u0631\u064a\u0642\u0628\u062d\u0631\n\u0627\u0644\u062d\u062f\u0627\u0644\u0623\u062f\u0646\u064a:200,000\u0644.\u0633\n\u0627\u0644\u062d\u062f\u0627\u0623\u0642\u0635\u064a:2,000,000\u0644.\u0633\n\u0639\u0645\u0648\u0644\u0629\u0627\u0644\u0633\u062d\u0628:10%\n\n\u062e\u062a\u0631\u0637\u0631\u064a\u0642\u0629\u0627\u0633\u062a\u0644\u0627\u0645\u0623\u0645\u0648\u0627\u0644\u0643:",
    syriatel_charge: "\ud83d\udcb0*Syriatel Cash*\n\u064a\u0631\u062c\u064a\u062a\u062d\u0648\u064a\u0644\u0627\u0644\u0645\u0628\u0644\u063a\u0625\u0644\u064a\u0627\u0644\u0631\u0642\u0645:\n`{code}`\n\n\u0623\u0631\u0633\u0644\u0635\u0648\u0631\u0629\u0627\u0644\u0625\u064a\u0635\u0627\u0644\u0648\u0627\u0636\u062d\u0629\u0645\u0639\u0627\u0644\u0645\u0628\u0644\u063a.",
    cham_charge: "\ud83d\udcb3*Cham Cash*\n\u064a\u0631\u062c\u064a\u062a\u062d\u0648\u064a\u0644\u0627\u0644\u0645\u0628\u0644\u063a\u0625\u0644\u064a\u0627\u0644\u0645\u062d\u0641\u0638\u0629:\n`{wallet}`\n\n\u0623\u0631\u0633\u0644\u0635\u0648\u0631\u0629\u0627\u0644\u0625\u064a\u0635\u0627\u0644\u0648\u0627\u0636\u062d\u0629\u0645\u0639\u0627\u0644\u0645\u0628\u0644\u063a."
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
    let keyboard = [['\ud83d\udcb0 \u0634\u062d\u0646 \u0627\u0644\u0631\u0635\u064a\u062f', '\ud83c\udfe6 \u0637\u0644\u0628 \u0633\u062d\u0628'], ['\ud83d\udc64 \u062d\u0633\u0627\u0628\u064a \u0627\u0644\u0641\u0631\u062f\u064a', '\ud83d\udcde \u0627\u0644\u062f\u0639\u0645 \u0627\u0644\u0641\u0646\u064a']]; 
    if (isOwner(userId)) keyboard.push(['\u2699\ufe0f \u0644\u064load\u062d\u0629 \u062a\u062d\u0643\u0645 \u0627\u0644\u0625\u062f\u0627\u0631\u0629']); 
    return Markup.keyboard(keyboard).resize(); 
} 

function getAdminMenu() { 
    return Markup.keyboard([ 
        ['\u2699\ufe0f \u062a\u0632\u062f\u064a\u0644 \u0631\u0635\u064a\u062f', '\ud83d\udcdd \u062a\u0632\u062f\u064a\u0644 \u0627\u0644\u062a\u0631\u062d\u064a\u0628'],
        ['\ud83d\udcde \u0633\u064a\u0631\u064a\u062a\u0644', '\ud83d\udcb3 \u0634\u0627\u0645 \u0643\u0627\u0634'], 
        ['\ud83d\udce2 \u0625\u0630\u0627\u0639\u0629', '\ud83d\udd19 \u0627\u0644\u0639\u0648\u062f\u0629'] 
    ]).resize(); 
} 

bot.start((ctx) => { ctx.reply(loadSettings().welcome_msg, getMainMenu(ctx.from.id)); }); 
bot.hears('\ud83d\udd19 \u0627\u0644\u0639\u0648\u062f\u0629', (ctx) => { ctx.reply('OK', getMainMenu(ctx.from.id)); }); 
bot.hears('\ud83d\udcde \u0627\u0644\u062f\u0639\u0645 \u0627\u0644\u0641\u0646\u064a', (ctx) => { userStates[ctx.from.id] = { step: 'support' }; ctx.reply(msgs.technical_support); }); 

bot.hears('\ud83d\udc64 \u062d\u0633\u0627\u0628\u064a \u0627\u0644\u0641\u0631\u062f\u064a', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id); 
    if (!account) { 
        return ctx.reply('❌ No Account.', Markup.inlineKeyboard([[Markup.button.callback('🆕 Register', 'register_account')]])); 
    } 
    ctx.replyWithMarkdown(`👤 *User:* \`${account.username}\`\n💰 *Balance:* *${account.balance.toLocaleString()}* SYP`, 
        Markup.inlineKeyboard([[Markup.button.callback('❌ Delete Account', 'confirm_delete_acc')]])); 
}); 

bot.action('confirm_delete_acc', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('⚠️ Delete?', Markup.inlineKeyboard([[Markup.button.callback('✅ Yes', 'execute_delete_acc')], [Markup.button.callback('🔙 No', 'cancel_delete_acc')]])); });
bot.action('execute_delete_acc', (ctx) => { ctx.answerCbQuery(); deletePlayerAccount(ctx.from.id); ctx.editMessageText('🗑️ Deleted.'); });
bot.action('cancel_delete_acc', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('Canceled.'); });
bot.action('register_account', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'username' }; ctx.reply('✏️ Enter Username:'); }); 

bot.hears('\u2699\ufe0f \u0644\u064load\u062d\u0629 \u062a\u062d\u0643\u0645 \u0627\u0644\u0625\u062f\u0627\u0631\u0629', (ctx) => { 
    if (!isOwner(ctx.from.id)) return ctx.reply('❌ Admin Only.'); 
    ctx.reply('⚙️ Admin Panel:', getAdminMenu()); 
}); 

bot.hears('\u2699\ufe0f \u062a\u0632\u062f\u064a\u0644 \u0631\u0635\u064a\u062f', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'admin_id' };
    ctx.reply('✏️ Enter Player Telegram ID:');
});

bot.hears('\ud83d\udcb0 \u0634\u062d\u0646 \u0627\u0644\u0631\u0635\u064a\u062f', (ctx) => { 
    if (!getPlayerAccount(ctx.from.id)) return ctx.reply('❌ Register First.');
    ctx.reply('Select Method:', Markup.inlineKeyboard([[Markup.button.callback('Syriatel Cash 🇸🇾', 'sh_syr')], [Markup.button.callback('Cham Cash 💳', 'sh_cham')]])); 
}); 

bot.action('sh_syr', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'proof', method: 'Syriatel' }; ctx.replyWithMarkdown(msgs.syriatel_charge.replace('{code}', loadSettings().syriatel_code)); }); 
bot.action('sh_cham', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'proof', method: 'Cham' }; ctx.replyWithMarkdown(msgs.cham_charge.replace('{wallet}', loadSettings().cham_wallet)); }); 
bot.hears('\ud83c\udfe6 \u0637\u0644\u0628 \u0633\u062d\u0628', (ctx) => { ctx.replyWithMarkdown(msgs.withdraw_rules, Markup.inlineKeyboard([[Markup.button.callback('Syriatel', 'w_s')], [Markup.button.callback('Cham', 'w_c')]])); }); 

bot.action('w_s', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'w_amt', method: 'Syriatel' }; ctx.reply('✏️ Enter Amount:'); });
bot.action('w_c', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'w_amt', method: 'Cham' }; ctx.reply('✏️ Enter Amount:'); });

bot.action('chg_app', (ctx) => { ctx.answerCbQuery(); ctx.reply('Admin Action Required via Panel.'); });
bot.action('chg_rej', (ctx) => { ctx.answerCbQuery(); ctx.editMessageCaption('❌ Rejected.'); });
bot.action('reg_app', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('✅ Approved.'); });
bot.action('reg_rej', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('❌ Rejected.'); });

bot.on('message', async (ctx) => { 
    const userId = ctx.from.id; const text = ctx.message.text; const currentState = userStates[userId]?.step; 

    if (userStates[userId]?.step === 'proof' && (ctx.message.photo || text)) {
        const method = userStates[userId].method; const captionText = ctx.message.caption || text || "";
        const amountMatch = captionText.match(/\d+/); const amount = amountMatch ? parseInt(amountMatch) : 0;
        const account = getPlayerAccount(userId); delete userStates[userId];

        if (ctx.message.photo) {
            await bot.telegram.sendPhoto(ADMIN_GROUP_ID, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
                caption: `💰 Deposit:\n• User: \`${account?.username || 'None'}\`\n• Amount: *${amount}*\n• Telegram ID: \`TGID:${userId}\``,
                ...Markup.inlineKeyboard([[Markup.button.callback('🟢 Accept', 'chg_app')], [Markup.button.callback('🔴 Reject', 'chg_rej')]])
            });
        }
        return ctx.reply('⏳ Uploaded.');
    }

