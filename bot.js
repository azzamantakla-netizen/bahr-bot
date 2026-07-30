const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const Database = require('better-sqlite3');
const messages = require('./messages');

const TOKEN = "8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8";
const ADMIN_GROUP = -1003983996094;
const PRIMARY_OWNER = 6693251012;

const bot = new TelegramBot(TOKEN, { polling: true });
const db = new Database('bot_data.db');
const axiosInstance = axios.create({ withCredentials: true });

db.prepare(`CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)`).run();
db.prepare(`CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, player_id TEXT, username TEXT, password TEXT)`).run();
db.prepare(`CREATE TABLE IF NOT EXISTS staff (telegram_id INTEGER PRIMARY KEY, role TEXT)`).run();

const setConfig = (key, val) => db.prepare(`INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)`).run(key, val);
const getConfig = (key, fallback) => { const r = db.prepare(`SELECT value FROM config WHERE key = ?`).get(key); return r ? r.value : fallback; };

if (!getConfig('cashier_user', '')) setConfig('cashier_user', 'Bero@yahoo.com');
if (!getConfig('cashier_pass', '')) setConfig('cashier_pass', 'Aazzam@318');
if (!getConfig('syriatel_code', '')) setConfig('syriatel_code', '48122120');
if (!getConfig('sham_wallet', '')) setConfig('sham_wallet', 'a18758d5324eb7595d4463ca355ad221');
if (!getConfig('bot_status', '')) setConfig('bot_status', 'ON');
if (!getConfig('welcome_msg', '')) setConfig('welcome_msg', messages.welcome);

const domain = "agents." + "texas4" + "win" + ".com";
const basePath = "https://" + domain + "/global/api/";

const API = {
    signIn: basePath + "User/signIn",
    balance: basePath + "Player/getPlayerBalanceById",
    deposit: basePath + "Player/depositToPlayer",
    withdraw: basePath + "Player/withdrawFromPlayer",
    register: basePath + "Player/registerPlayer"
};

async function loginCashier() {
    try {
        const res = await axiosInstance.post(API.signIn, {
            email: getConfig('cashier_user'),
            password: getConfig('cashier_pass')
        }, { 
            headers: { 
                'Content-Type': 'application/json', 
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Origin': 'https://texas4win.com',
                'Referer': 'https://texas4win.com/'
            } 
        });
        if (res.status === 200) console.log(">>> Cashier login successful! <<<");
    } catch (e) { 
        console.error("❌ Cashier login failed:", e.message); 
    }
}
function isOwner(id) {
    if (id === PRIMARY_OWNER) return true;
    const r = db.prepare(`SELECT role FROM staff WHERE telegram_id = ? AND role = 'OWNER'`).get(id);
    return !!r;
}
function isStaff(id) {
    if (id === PRIMARY_OWNER) return true;
    const r = db.prepare(`SELECT role FROM staff WHERE telegram_id = ?`).get(id);
    return !!r;
}

const playerKeyboard = (userId) => {
    const inline_keyboard = [
        [{ text: "👤 حسابي", callback_data: "p_account" }],
        [{ text: "📥 إيداع / شحن رصيد", callback_data: "p_deposit" }, { text: "📤 سحب رصيد", callback_data: "p_withdraw" }],
        [{ text: "📞 الدعم الفني", callback_data: "p_support" }]
    ];
    if (isOwner(userId)) inline_keyboard.push([{ text: "⚙️ قائمة التحكم (للمالك)", callback_data: "m_panel" }]);
    return { inline_keyboard };
};

bot.onText(/\/start/, (msg) => {
    if (getConfig('bot_status') === 'OFF' && !isOwner(msg.from.id)) {
        return bot.sendMessage(msg.chat.id, "🛑 الصيانة جارية حالياً للبوت، يرجى المحاولة لاحقاً.");
    }
    bot.sendMessage(msg.chat.id, getConfig('welcome_msg'), { parse_mode: 'Markdown', reply_markup: playerKeyboard(msg.from.id) });
});

bot.on('callback_query', async (query) => {
    const { data, message, from } = query;
    bot.answerCallbackQuery(query.id);

    if (getConfig('bot_status') === 'OFF' && !isOwner(from.id)) return;

    if (data === "p_account") {
        const user = db.prepare(`SELECT * FROM users WHERE telegram_id = ?`).get(from.id);
        if (!user) {
            bot.sendMessage(message.chat.id, "⚠️ لا تمتلك حساباً مرتبطاً حتى الآن.", {
                reply_markup: { inline_keyboard: [[{ text: "➕ إنشاء حساب لاعب جديد تلقائياً", callback_data: "p_create_acc" }]] }
            });
        } else {
            bot.sendMessage(message.chat.id, `👤 **لوحة معلومات حسابك الشخصي:**\n\n🆔 **آيدي التلجرام:** \`${from.id}\`\n🔐 **اسم المستخدم (الموقع):** \`${user.username}\`\n🔑 **كلمة المرور:** \`${user.password}\`\n\n💳 رصيدك الحالي يتم تحديثه تلقائياً في السيرفر الرئيسي.`, { parse_mode: 'Markdown' });
        }
    }

    if (data === "p_create_acc") {
        bot.sendMessage(message.chat.id, "🔄 جاري التواصل مع السيرفر لإنشاء حسابك وتوليد البيانات الحصريّة...");
        const randUser = "TX_" + Math.floor(100000 + Math.random() * 900000);
        const randPass = Math.random().toString(36).slice(-8);
        try {
            await loginCashier();
            await axiosInstance.post(API.register, {
                player: {
                    email: `${randUser}@texasbot.com`, firstname: "Player", lastname: "Bot",
                    login: randUser, middleName: "Bot", parentId: "2688288", password: randPass
                }
            });
            db.prepare(`INSERT INTO users (telegram_id, player_id, username, password) VALUES (?, ?, ?, ?)`).run(from.id, randUser, randUser, randPass);
            bot.sendMessage(message.chat.id, `🎉 **تم إنشاء حسابك بنجاح وعقد الشراكة!**\n\n🔐 اسم المستخدم: \`${randUser}\`\n🔑 كلمة المرور: \`${randPass}\`\n\nيمكنك الآن تسجيل الدخول للموقع واستخدام أزرار الإيداع والسحب.`, { parse_mode: 'Markdown' });
        } catch (e) { bot.sendMessage(message.chat.id, "❌ حدث خطأ من سيرفر اللوحة أثناء التسجيل، يرجى المحاولة لاحقاً."); }
    }

    if (data === "p_deposit") {
        bot.sendMessage(message.chat.id, "📥 اختر وسيلة الدفع التي تناسبك للإيداع:", {
            reply_markup: { inline_keyboard: [[{ text: "🔴 Syriatel Cash", callback_data: "dep_syriatel" }], [{ text: "🔵 Sham Cash", callback_data: "dep_sham" }]] }
        });
    }
    if (data === "dep_syriatel") bot.sendMessage(message.chat.id, messages.syriatelDeposit(getConfig('syriatel_code')), { parse_mode: 'Markdown' }).then(() => initiateDepositProcess(from.id, 'Syriatel Cash'));
    if (data === "dep_sham") bot.sendMessage(message.chat.id, messages.shamDeposit(getConfig('sham_wallet')), { parse_mode: 'Markdown' }).then(() => initiateDepositProcess(from.id, 'Sham Cash'));

    if (data === "p_withdraw") {
        bot.sendMessage(message.chat.id, "📤 اختر وسيلة الدفع لاستلاف أرباحك كاش:", {
            reply_markup: { inline_keyboard: [[{ text: "🔴 استلام عبر Syriatel Cash", callback_data: "wd_syriatel" }], [{ text: "🔵 استلام عبر Sham Cash", callback_data: "wd_sham" }]] }
        });
    }
    if (data.startsWith("wd_")) {
        const method = data.includes("syriatel") ? "Syriatel Cash" : "Sham Cash";
        bot.sendMessage(message.chat.id, `✍️ يرجى كتابة **المبلغ** المراد سحبه أولاً متبوعاً بـ **رقم أو عنوان محفظتك** كاش.\n\n*صيغة الكتابة المعتمدة:* \`المبلغ المحفظة\`\n*مثال:* \`100000 0912345678\``, { parse_mode: 'Markdown' }).then(() => {
            bot.onReplyToMessage(message.chat.id, message.message_id, (wMsg) => processWithdrawalOrder(wMsg, method));
        });
    }

    if (data === "p_support") {
        bot.sendMessage(message.chat.id, "📞 **أنت بأمان لا تقلق، نحن هنا لخدمتك! فريقنا جاهز على مدار الساعة. فقط اكتب لنا ما هي المشكلة وسنقوم بالرد عليها فوراً.** 👇").then(() => {
            bot.once('message', (sMsg) => {
                if(sMsg.text && !sMsg.text.startsWith('/')) {
                    bot.sendMessage(ADMIN_GROUP, `✉️ **رسالة دعم فني جديدة:**\n\n👤 **اللاعب:** \`${sMsg.from.username || sMsg.from.first_name}\`\n🆔 **آيدي التلجرام:** \`${sMsg.from.id}\`\n📝 **المشكلة:** "${sMsg.text}"\n\n💬 _للرد على اللاعب، قم بعمل Reply مباشر على هذه الرسالة واكتب الحل._`);
                    bot.sendMessage(sMsg.chat.id, "✔ تم إرسال مشكلتك لفريق الدعم، جاري فحص الطلب والرد عليك.");
                }
            });
        });
    }

    if (data === "m_panel" && isOwner(from.id)) {
        bot.sendMessage(message.chat.id, "⚙️ **لوحة التحكم العليا للمالك الإداري:**", {
            reply_markup: {
                inline_keyboard: [
                    [{ text: "📝 تعديل الترحيب", callback_data: "m_edit_welcome" }, { text: "🔐 حساب الكاشير", callback_data: "m_edit_cashier" }],
                    [{ text: "🔴 تعديل سيرياتيل", callback_data: "m_edit_syria" }, { text: "🔵 تعديل شام كاش", callback_data: "m_edit_sham" }],
                    [{ text: "👥 إضافة مشرف", callback_data: "m_add_staff" }, { text: "📢 إذاعة عامة", callback_data: "m_broadcast" }],
                    [{ text: getConfig('bot_status') === 'ON' ? "🛑 إطفاء البوت" : "🟢 تشغيل البوت", callback_data: "m_toggle_bot" }]
                ]
            }
        });
    }

    if (data === "m_toggle_bot" && isOwner(from.id)) {
        const next = getConfig('bot_status') === 'ON' ? 'OFF' : 'ON';
        setConfig('bot_status', next);
        bot.sendMessage(message.chat.id, `⚙️ تم تغيير حالة البوت الحركية إلى: **${next}**`, { parse_mode: 'Markdown' });
    }

    if (isStaff(from.id)) {
        if (data.startsWith("adm_dep_approve_")) {
            const [,, tgId, txId] = data.split('_');
          function initiateDepositProcess(tgId, method) {
    bot.once('message', (msg) => {
        if (msg.from.id === tgId && msg.text && !msg.text.startsWith('/')) {
            const txId = msg.text.trim();
            bot.sendMessage(ADMIN_GROUP, `🚨 **طلب إيداع قيد الانتظار لمطابقة الأموال:**\n\n🆔 **آيدي التلجرام:** \`${tgId}\`\n💳 **طريقة الدفع:** ${method}\n🧾 **رقم المعاملة المرسل:** \`${txId}\`\n\n🎛️ تأكد من محفظتك قبل الموافقة للشحن التلقائي:`, {
                reply_markup: {
                    inline_keyboard: [
                        [{ text: "✅ موافقة وشحن تلقائي", callback_data: `adm_dep_approve_${tgId}_${txId}` }],
                        [{ text: "❌ رفض المعاملة", callback_data: `adm_dep_reject_${tgId}` }]
                    ]
                }
            });
            bot.sendMessage(tgId, "⏳ تم إرسال طلب المعاملة ورقمها للإدارة، سيتم شحن حسابك تلقائياً فور التأكيد البشري.");
        }
    });
}

function processWithdrawalOrder(msg, method) {
    const parts = msg.text.split(' ');
    if (parts.length < 2) return bot.sendMessage(msg.chat.id, "⚠️ البيانات المدخلة غير صحيحة، يرجى إعادة المحاولة من زر السحب.");
    const amount = parseFloat(parts[0]);
    const wallet = parts[1];
    const fee = amount * 0.10;
    const net = amount - fee;

    bot.sendMessage(msg.chat.id, `📊 **تفاصيل طلب السحب الخاص بك:**\n\n💰 **المبلغ المطلوب خصمه:** \`${amount}\` NSP\n✂️ **عمولة السحب (10%):** \`${fee}\` NSP\n💵 **صافي المبلغ للاستلام:** \`${net}\` ل.س\n📲 **المحفظة المستلمة:** \`${wallet}\`\n\n⏳ تم إرسال طلبك للإدارة لتأكيد الخصم المباشر.`);

    bot.sendMessage(ADMIN_GROUP, `🚨 **طلب سحب كاش جديد قيد الانتظار:**\n\n🆔 **آيدي التلجرام:** \`${msg.from.id}\`\n📉 **المبلغ المطلوب خصمه:** \`${amount}\` NSP\n💵 **الصافي المستحق للإرسال:** \`${net}\` ل.س\n📲 **حساب العميل:** \`${wallet}\` (${method})\n\n🎛️ اضغط للموافقة على الخصم الفوري التلقائي من لوحة الكاشير:`, {
        reply_markup: {
            inline_keyboard: [[{ text: "✅ موافقة وخصم الرصيد تلقائياً", callback_data: `adm_wd_app_${msg.from.id}_${amount}_${net}_${wallet}` }]]
        }
    });
}

bot.on('message', (msg) => {
    if (msg.chat.id === ADMIN_GROUP && msg.reply_to_message) {
        const text = msg.reply_to_message.text;
        if (text && text.includes("رسالة دعم فني جديدة:")) {
            const matches = text.match(/آيدي التلجرام:\s*`(\d+)`/);
            if (matches && matches[1]) {
                const playerTgId = matches[1];
                bot.sendMessage(playerTgId, `🔔 **رد من الدعم الفني لـ عائلتنا:**\n\n💬 "${msg.text}"`);
                bot.sendMessage(ADMIN_GROUP, "✔ تم تسليم ردك للاعب بنجاح وفي الحين.");
            }
        }
    }
});

console.log(">>> Bot is running successfully! <<<");
