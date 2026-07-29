const { Telegraf, Markup } = require('telegraf'); 
const fs = require('fs'); 
const http = require('http'); 

// مصفوفة النصوص مدمجة داخلياً لتناسب نظام التسجيل الجديد
const msgs = {
    welcome_msg: `مرحبا بك في عائلتنا صمم هذا البوت باحترافية عالية ليقدم لك تجربة من نوع آخر نقدم لك سرعة عالية في الايداع ومرونة عالية في السحب تفضل بالاختيار من القائمة بحسب الزر الذي يلبي طلبك`,
    technical_support: `❤️ لا تقلق نحن معك وفريقنا جاهز لخدمتك على مدار الساعة، فقط اكتب المشكلة أو الاستفسار بالتفصيل وأرسله الآن وسنقوم بالرد عليك فوراً:`,
    withdraw_rules: `📌 *شروط وقوانين السحب لـ فريق بحر:*\n• الحد الأدنى: 200,000 ل.س\n• الحد الأقصى: 2,000,000 ل.س\n• عمولة الاستقطاع: 10%\n\nاختر طريقة استلام أموالك:`,
    syriatel_charge: `*Syriatel Cash 🇸🇾*\n\nيرجى تحويل المبلغ إلى الرقم التابع لنا:\n➡️ \`{code}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`,
    cham_charge: `*شام كاش (Cham Cash) 💳*\n\nيرجى تحويل المبلغ إلى عنوان المحفظة:\n➡️ \`{wallet}\`\n\n⚠️ بعد التحويل، أرسل للبوت صورة الإيصال واضحة متبوعة بمعرف اللعبة والمبلغ.`,
    accept_caption: `💰 *إيصال تعبئة فريق بحر:*\n\n✅ تم *قبول* هذا الإيصال واعتماد المعاملة بواسطة: [{name}](tg://user?id={id})`,
    reject_caption: `💰 *إيصال تعبئة فريق بحر:*\n\n❌ تم *رفض* هذا الإيصال وإلغاء المعاملة بواسطة: [{name}](tg://user?id={id})`,
    player_accept: `🎉 *خبر سار من فريق بحر:*\n\nتمت مراجعة إيصال التحويل الخاص بك و*القبول* بنجاح! جاري شحن رصيد حسابك الآن.`,
    player_reject: `❌ *تنبيه من إدارة فريق بحر:*\n\nعذراً، تمت مراجعة إيصالك وتبيّن أن البيانات مدخلة بشكل *خاطئ* أو غير واصلة. تم *رفض* الطلب. يرجى التأكد وإعادة المحاولة.`
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

// دالة حفظ الحساب الجديد بالهيكل الجديد مئة بالمئة
function savePlayerAccount(userId, username, password, balance = 0) { 
    let accounts = {}; 
    if (fs.existsSync(ACCOUNTS_FILE)) { 
        accounts = JSON.parse(fs.readFileSync(ACCOUNTS_FILE)); 
    } 
    accounts[userId] = { username: username, password: password, balance: balance }; 
    fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accounts, null, 4)); 
} 

function getMainMenu(userId) { 
    let keyboard = [['💰 شحن الرصيد', '🏦 طلب سحب'], ['👤 حسابي الفردي', '📞 الدعم الفني']]; 
    if (isOwner(userId)) keyboard.push(['⚙️ لوحة تحكم الإدارة']); 
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
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي الموثق:*\n\n• الاسم: *${ctx.from.first_name}*\n• اسم المستخدم: \`${account.username}\`\n• رصيدك الحالي: *${account.balance.toLocaleString()}* ل.س\n\n📌 يتم تحديث الرصيد تلقائياً عند موافقة الإدارة على إيصالات الشحن الخاصة بك.`); 
}); 

bot.action('register_account', (ctx) => { 
    ctx.answerCbQuery(); 
    // الخطوة الأولى: طلب اسم المستخدم
    userStates[ctx.from.id] = { step: 'awaiting_username' }; 
    ctx.reply('✏️ يرجى كتابة اسم المستخدم (Username) الذي تريده للحساب الآن:'); 
}); 

bot.hears('⚙️ لوحة تحكم الإدارة', (ctx) => { 
    if (!isOwner(ctx.from.id)) return ctx.reply('❌ مخصص للمالك فقط.'); 
    ctx.reply('⚙️ لوحة تحكم الإدارة:', getAdminMenu()); 
}); 

bot.hears('💰 شحن الرصيد', (ctx) => { 
    ctx.reply('اختر طريقة الدفع المناسبة:', Markup.inlineKeyboard([ 
        [Markup.button.callback('Syriatel Cash 🇸🇾', 'show_syriatel')], 
        [Markup.button.callback('شام كاش (Cham Cash) 💳', 'show_cham')] 
    ])); 
}); 

bot.action('show_syriatel', (ctx) => { 
    ctx.answerCbQuery(); 
    ctx.replyWithMarkdown(msgs.syriatel_charge.replace('{code}', loadSettings().syriatel_code)); 
}); 

bot.action('show_cham', (ctx) => { 
    ctx.answerCbQuery(); 
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

bot.action(/dep_(accept|reject)_(\d+)/, async (ctx) => { 
    ctx.answerCbQuery(); 
    const action = ctx.match[1]; 
    const playerTelegramId = ctx.match[2]; 
    
    if (action === 'accept') { 
        let text = msgs.accept_caption.replace('{name}', ctx.from.first_name).replace('{id}', ctx.from.id);
        await ctx.editMessageCaption(text, { parse_mode: 'Markdown' }); 
        try { await bot.telegram.sendMessage(playerTelegramId, msgs.player_accept, { parse_mode: 'Markdown' }); } catch (e) {} 
    } else { 
        let text = msgs.reject_caption.replace('{name}', ctx.from.first_name).replace('{id}', ctx.from.id);
        await ctx.editMessageCaption(text, { parse_mode: 'Markdown' }); 
        try { await bot.telegram.sendMessage(playerTelegramId, msgs.player_reject, { parse_mode: 'Markdown' }); } catch (e) {} 
    } 
}); 

// 5. قسم استقبال المدخلات النصية ومعالجة تدفق الحساب والردود
bot.on('message', async (ctx) => { 
    const userId = ctx.from.id; 
    const text = ctx.message.text;
    const currentState = userStates[userId]?.step; 

    // معالجة خطوات إنشاء الحساب المتتالي (اسم مستخدم -> كلمة سر)
    if (currentState === 'awaiting_username' && text) {
        // حفظ اسم المستخدم مؤقتاً والانتقال لطلب كلمة السر
        userStates[userId] = { step: 'awaiting_password', username: text };
        return ctx.reply('🔒 ممتاز، الآن يرجى كتابة كلمة السر (Password) المطلوبة لحسابك لإتمام التسجيل:');
    }

    if (currentState === 'awaiting_password' && text) {
        const username = userStates[userId].username;
        const password = text;
        
        // حفظ البيانات نهائياً برصيد 0
        savePlayerAccount(userId, username, password, 0);
        
        // مسح الحالة المؤقتة للمستخدم
        delete userStates[userId];
        
        return ctx.replyWithMarkdown(`🎉 *تهانينا! تم إنشاء حسابك بنجاح مئة بالمئة.*\n\n• اسم المستخدم: \`${username}\`\n• كلمة المرور: \`${password}\`\n\nيمكنك الآن تفقد رصيدك وبياناتك عبر زر *👤 حسابي الفردي*.`);
    }

    // معالجة رسائل الدعم الفني من القروب (عند عمل ريبلاي)
    if (ctx.chat.id === ADMIN_GROUP_ID && ctx.message.reply_to_message) { 
        const replyText = ctx.message.reply_to_message.text || ctx.message.reply_to_message.caption; 
        if (replyText && replyText.includes('ID:')) { 
            const matches = replyText.match(/ID:\s*(\d+)/); 
            if (matches && matches[1]) { 
                try { 
                    await bot.telegram.sendMessage(matches[1], `📬 *رد من الإدارة:*\n\n💬 ${text || ''}`, { parse_mode: 'Markdown' }); 
                } catch (e) {} 
            } 
        } 
    } 
}); 

// تشغيل سيرفر الويب لـ Render للبقاء حياً
http.createServer((req, res) => { 
    res.writeHead(200, { 'Content-Type': 'text/plain' }); 
    res.end('Bot Server Operational\n'); 
}).listen(process.env.PORT || 10000); 

bot.launch().then(() => { console.log('Deployed Successfully with Multi-step Registration!'); });
