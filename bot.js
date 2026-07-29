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
    welcome_msg: "\u0645\u0631\u062d\u0628\u0627\u064b \u0628\u0643 \u0641\u064a \u0639\u0627\u0626\u0644\u062a\u0646\u0627\u060c \u062a\u0641\u0636\u0644 \u0628\u0627\u0644\u0627\u062e\u062a\u064a\u0627\u0631 \u0645\u0646 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0628\u062d\u0633\u0628 \u0627\u0644\u0632\u0631 \u0627\u0644\u0630\u064a \u064a\u0644\u0628\u064a \u0637\u0644\u0628\u0643.",
    technical_support: "\u0644\u0627 \u062a\u0642\u0644\u0642 \u0646\u062d\u0646 \u0645\u0639\u0643 \u0648\u0641\u0631\u064a\u0642\u0646\u0627 \u062c\u0627\u0647\u0632 \u0644\u062e\u062f\u0645\u062a\u0643\u0606 \u0627\u0643\u062a\u0628 \u0627\u0644\u0645\u0634\u0643\u0644\u0629 \u0628\u0627\u0644\u062a\u0641\u0635\u064a\u0644 \u0648\u0623\u0631\u0633\u0644\u0647\u0627 \u0627\u0644\u0622\u0646:",
    withdraw_rules: "\u0634\u0631\u0648\u0637 \u0648\u0642\u0648\u0627\u0646\u064a\u0646 \u0627\u0644\u0633\u062d\u0628:\n\u2022 \u0627\u0644\u062d\u062f \u0627\u0644\u0623\u062f\u0646\u064a: 200,000\n\u2022 \u0627\u0644\u062d\u062f \u0627\u0644\u0623\u0642\u0635\u064a: 2,000,000\n\u2022 \u0639\u0645\u0648\u0644\u0629 \u0627\u0644\u0633\u062d\u0628: 10%\n\n\u062e\u062a\u0631 \u0637\u0631\u064a\u0642\u0629 \u0627\u0633\u062a\u0644\u0627\u0645 \u0623\u0645\u0648\u0627\u0644\u0643:",
    syriatel_charge: "\u0633\u064a\u0631\u064a\u062a\u0644 \u0643\u0627\u0634:\n\u064a\u0631\u062c\u064a \u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0645\u0628\u0644\u063a \u0625\u0644\u064a \u0627\u0644\u0631\u0642\u0645:\n`{code}`\n\n\u0623\u0631\u0633\u0644 \u0635\u0648\u0631\u0629 \u0627\u0644\u0625\u064a\u0635\u0627\u0644 \u0648\u0627\u0636\u062d\u0629 \u0645\u0639 \u0627\u0644\u0645\u0628\u0644\u063a.",
    cham_charge: "\u0634\u0627\u0645 \u0643\u0627\u0634:\n\u064a\u0631\u062c\u064a \u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u0645\u0628\u0644\u063a \u0625\u0644\u064a \u0627\u0644\u0645\u062d\u0641\u0638\u0629:\n`{wallet}`\n\n\u0623\u0631\u0633\u0644 \u0635\u0648\u0631\u0629 \u0627\u0644\u0625\u064a\u0635\u0627\u0644 \u0648\u0627\u0636\u062d\u0629 \u0645\u0639 \u0627\u0644\u0645\u0628\u0644\u063a."
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

function getMainMenu(userId) { 
    let keyboard = [['\u0634\u062d\u0646 \u0627\u0644\u0631\u0635\u064a\u062f', '\u0637\u0644\u0628 \u0633\u062d\u0628'], ['\u062d\u0633\u0627\u0628\u064a \u0627\u0644\u0641\u0631\u062f\u064a', '\u0627\u0644\u062f\u0639\u0645 \u0627\u0644\u0641\u0646\u064a']]; 
    if (isOwner(userId)) keyboard.push(['\u0644\u0648\u062d\u0629 \u0627\u0644\u0625\u062f\u0627\u0631\u0629']); 
    return Markup.keyboard(keyboard).resize(); 
} 

bot.start((ctx) => { ctx.reply(loadSettings().welcome_msg, getMainMenu(ctx.from.id)); }); 
bot.hears('\u0627\u0644\u062f\u0639\u0645 \u0627\u0644\u0641\u0646\u064a', (ctx) => { ctx.reply(msgs.technical_support); }); 

bot.hears('\u062d\u0633\u0627\u0628\u064a \u0627\u0644\u0641\u0631\u062f\u064a', (ctx) => { 
    const account = getPlayerAccount(ctx.from.id); 
    if (!account) { 
        return ctx.reply('\u062d\u0633\u0627\u0628\u0643 \u063a\u064a\u0631 \u0645\u0633\u062c\u0644.', Markup.inlineKeyboard([[Markup.button.callback('\u0625\u0646\u0634\u0627\u0621 \u062d\u0633\u0627\u0628 \u062c\u062f\u064a\u062d', 'register_account')]])); 
    } 
    ctx.replyWithMarkdown(`\u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645: \`${account.username}\`\n\u0627\u0644\u0631\u0635\u064a\u062f: *${account.balance.toLocaleString()}* \u0644.\u0633`); 
}); 

bot.action('register_account', (ctx) => { ctx.answerCbQuery(); userStates[ctx.from.id] = { step: 'username' }; ctx.reply('\u0623\u0631\u0633\u0644 \u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645:'); }); 

bot.hears('\u0634\u062d\u0646 \u0627\u0644\u0631\u0635\u064a\u062f', (ctx) => { 
    if (!getPlayerAccount(ctx.from.id)) return ctx.reply('\u064a\u0631\u062c\u064a \u0625\u0646\u0634\u062e\u0627\u0621 \u062d\u0633\u0627\u0628 \u0623\u0648\u0644\u0627\u064b.');
    ctx.reply('\u062e\u062a\u0631 \u0637\u0631\u064a\u0642\u0629 \u0627\u0644\u062f\u0641\u0639:', Markup.inlineKeyboard([[Markup.button.callback('Syriatel Cash', 'sh_syr')], [Markup.button.callback('Cham Cash', 'sh_cham')]])); 
}); 

bot.action('sh_syr', (ctx) => { ctx.answerCbQuery(); ctx.replyWithMarkdown(msgs.syriatel_charge.replace('{code}', loadSettings().syriatel_code)); }); 
bot.action('sh_cham', (ctx) => { ctx.answerCbQuery(); ctx.replyWithMarkdown(msgs.cham_charge.replace('{wallet}', loadSettings().cham_wallet)); }); 
bot.hears('\u0637\u0644\u0628 \u0633\u062d\u0628', (ctx) => { ctx.replyWithMarkdown(msgs.withdraw_rules, Markup.inlineKeyboard([[Markup.button.callback('Syriatel', 'w_s')], [Markup.button.callback('Cham', 'w_c')]])); }); 

bot.action('w_s', (ctx) => { ctx.answerCbQuery(); ctx.reply('\u0623\u062f\u062e\u0644 \u0627\u0644\u0645\u0628\u0644\u063a:'); });
bot.action('w_c', (ctx) => { ctx.answerCbQuery(); ctx.reply('\u0623\u062f\u062e\u0644 \u0627\u0644\u0645\u0628\u0644\u063a:'); });

bot.hears('\u0644\u0648\u062d\u0629 \u0627\u0644\u0625\u062f\u0627\u0631\u0629', (ctx) => { ctx.reply('Admin Panel'); });

bot.on('text', async (ctx) => { 
    const userId = ctx.from.id; const text = ctx.message.text; const currentState = userStates[userId]?.step; 

    if (currentState === 'username' && text) { userStates[userId] = { step: 'password', username: text }; return ctx.reply('\u0623\u062f\u062e\u0644 \u0643\u0644\u0645\u064a\u0629 \u0627\u0644\u0633\u0631:'); } 
    if (currentState === 'password' && text) { 
        const username = userStates[userId].username; delete userStates[userId];
        savePlayerAccount(userId, username, text, 0);
        return ctx.reply('\u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u062d\u0633\u0627\u0628 \u0628\u0646\u062c\u0627\u062d.'); 
    } 
}); 

http.createServer((req, res) => { res.writeHead(200); res.end('OK'); }).listen(process.env.PORT || 10000); 
bot.launch().then(() => { console.log('Live!'); });
