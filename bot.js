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
    welcome_msg: "Welcome to Bahr Team Bot! Please choose an option from the menu below to manage your account.",
    technical_support: "Support team is active 24/7. Please type your message or issue clearly and send it now:",
    withdraw_rules: "Withdraw Rules:\nMin: 200,000 SYP\nMax: 2,000,000 SYP\nFee: 10%\n\nSelect payout method:",
    syriatel_charge: "Syriatel Cash:\nTransfer to number: `{code}`\nAfter payment, send proof picture here.",
    cham_charge: "Cham Cash:\nTransfer to wallet: `{wallet}`\nAfter payment, send proof picture here."
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
    accounts[userId] = { username, password, balance }; 
    fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); 
} 

function deletePlayerAccount(userId) {
    if (!fs.existsSync(ACCOUNTS_FILE)) return;
    let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
    if (accounts[userId]) { delete accounts[userId]; fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); }
}

function getMainMenu(userId) { 
    let keyboard = [['Deposit', 'Withdraw'], ['My Account', 'Support']]; 
    if (isOwner(userId)) keyboard.push(['Admin Panel']); 
    return Markup.keyboard(keyboard).resize(); 
} 

function getAdminMenu() { 
    return Markup.keyboard([ 
        ['Edit Balance', 'Back to Main']
    ]).resize(); 
} 

bot.start((ctx) => { ctx.reply(loadSettings().welcome_msg, getMainMenu(ctx.from.id)); }); 
bot.hears('Back to Main', (ctx) => { ctx.reply('Back successfully.', getMainMenu(ctx.from.id)); }); 
bot.hears('Support', (ctx) => { userStates[ctx.from.id] = { step: 'support' }; ctx.reply(msgs.technical_support); }); 

bot.hears('My Account', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id); 
    if (!account) { 
        return ctx.reply('No account found. Click below to register:', Markup.inlineKeyboard([[Markup.button.callback('Register New Account', 'register_account')]])); 
    } 
    ctx.replyWithMarkdown(`👤 *Username:* \`${account.username}\`\n💰 *Balance:* *${account.balance.toLocaleString()}* SYP`, 
        Markup.inlineKeyboard([[Markup.button.callback('❌ Delete Account', 'confirm_delete_acc')]])); 
}); 

bot.action('confirm_delete_acc', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('Are you sure you want to delete your account?', Markup.inlineKeyboard([[Markup.button.callback('Yes, Delete', 'execute_delete_acc')], [Markup.button.callback('No, Cancel', 'cancel_delete_acc')]])); });
bot.action('execute_delete_acc', (ctx) => { ctx.answerCbQuery(); deletePlayerAccount(ctx.from.id); ctx.editMessageText('Account deleted.'); });
bot.action('cancel_delete_acc', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('Canceled.'); });
bot.action('register_account', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'username' }; ctx.reply('Enter your username:'); }); 

bot.hears('Admin Panel', (ctx) => { 
    if (!isOwner(ctx.from.id)) return ctx.reply('Admin only.'); 
    ctx.reply('Admin Panel:', getAdminMenu()); 
}); 

bot.hears('Edit Balance', (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    userStates[ctx.from.id] = { step: 'admin_id' };
    ctx.reply('Enter Player Telegram ID:');
});

bot.hears('Deposit', (ctx) => { 
    if (!getPlayerAccount(ctx.from.id)) return ctx.reply('Please register your account first.');
    ctx.reply('Select payment method:', Markup.inlineKeyboard([[Markup.button.callback('Syriatel Cash', 'sh_syr')], [Markup.button.callback('Cham Cash', 'sh_cham')]])); 
}); 

bot.action('sh_syr', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'proof', method: 'Syriatel' }; ctx.replyWithMarkdown(msgs.syriatel_charge.replace('{code}', loadSettings().syriatel_code)); }); 
bot.action('sh_cham', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'proof', method: 'Cham' }; ctx.replyWithMarkdown(msgs.cham_charge.replace('{wallet}', loadSettings().cham_wallet)); }); 
bot.hears('Withdraw', (ctx) => { ctx.replyWithMarkdown(msgs.withdraw_rules, Markup.inlineKeyboard([[Markup.button.callback('Syriatel', 'w_s')], [Markup.button.callback('Cham', 'w_c')]])); }); 

bot.action('w_s', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'w_amt', method: 'Syriatel' }; ctx.reply('Enter payout amount:'); });
bot.action('w_c', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'w_amt', method: 'Cham' }; ctx.reply('Enter payout amount:'); });

bot.action('chg_app', (ctx) => { ctx.answerCbQuery(); ctx.reply('Action required via Admin Panel.'); });
bot.action('chg_rej', (ctx) => { ctx.answerCbQuery(); ctx.editMessageCaption('Rejected.'); });
bot.action('reg_app', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('Approved.'); });
bot.action('reg_rej', (ctx) => { ctx.answerCbQuery(); ctx.editMessageText('Rejected.'); });

bot.on('message', async (ctx) => { 
    const userId = ctx.from.id; const text = ctx.message.text; const currentState = userStates[userId]?.step; 

    if (userStates[userId]?.step === 'proof' && (ctx.message.photo || text)) {
        const method = userStates[userId].method; const captionText = ctx.message.caption || text || "";
        const amountMatch = captionText.match(/\d+/); const amount = amountMatch ? parseInt(amountMatch) : 0;
        const account = getPlayerAccount(userId); delete userStates[userId];

        if (ctx.message.photo) {
            await bot.telegram.sendPhoto(ADMIN_GROUP_ID, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
                caption: `New Deposit (${method}):\nUser: \`${account?.username || 'None'}\`\nAmount: *${amount}*\nTGID:${userId}`,
                ...Markup.inlineKeyboard([[Markup.button.callback('Accept', 'chg_app')], [Markup.button.callback('Reject', 'chg_rej')]])
            });
        }
        return ctx.reply('Receipt uploaded to admins successfully.');
    }

    if (currentState === 'username' && text) { userStates[userId] = { step: 'password', username: text }; return ctx.reply('Enter your password:'); } 
    if (currentState === 'password' && text) { 
        const username = userStates[userId].username; delete userStates[userId];
        await bot.telegram.sendMessage(ADMIN_GROUP_ID, `New Registration Request:\nUser: \`${username}\`\nPass: \`${text}\`\nTGID:${userId}`, 
            Markup.inlineKeyboard([[Markup.button.callback('Approve & Register', 'reg_app')], [Markup.button.callback('Reject', 'reg_rej')]])); 
        return ctx.reply('Request sent to admin for activation.'); 
    } 

    if (currentState === 'admin_id' && text && isOwner(userId)) {
        if (!getPlayerAccount(text.trim())) return ctx.reply('Player not found.');
        userStates[userId] = { step: 'admin_bal', targetId: text.trim() };
        return ctx.reply('Enter new balance total amount:');
    }

    if (currentState === 'admin_bal' && text && isOwner(userId)) {
        const targetId = userStates[userId].targetId; const newBalance = parseInt(text.trim()); delete userStates[userId];
        let accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE));
        accounts[targetId].balance = newBalance; fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4));
        ctx.reply(`Balance updated to ${newBalance}`);
        try { await bot.telegram.sendMessage(targetId, `Your balance has been updated to: *${newBalance}*`); } catch (e) {}
        return;
    }

    if (ctx.chat.id === ADMIN_GROUP_ID && ctx.message.reply_to_message) { 
        const replyText = ctx.message.reply_to_message.text || ctx.message.reply_to_message.caption; 
        if (replyText && replyText.includes('TGID:')) { 
            const matches = replyText.match(/TGID:(\d+)/); 
            if (matches) { try { await bot.telegram.sendMessage(matches[1], `Admin reply: ${text}`); } catch (e) {} } 
        } 
    } 
}); 

http.createServer((req, res) => { res.writeHead(200); res.end('OK'); }).listen(process.env.PORT || 10000); 
bot.launch().then(() => { console.log('Live!'); });
