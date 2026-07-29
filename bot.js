// كود بوت تليجرام متكامل - فريق بحر (نسخة نظام الدعم الفني المطور)
const { Telegraf, Markup } = require('telegraf');
const fs = require('fs');

const BOT_TOKEN = '8624354425:AAEEHP7BYNclcrDkYlxOqfHh5bJDIOhYaU8'; 
const bot = new Telegraf(BOT_TOKEN);

const OWNER_ID = 6693251012;
const ADMIN_GROUP_ID = -1003983996094;
const SETTINGS_FILE = './settings.json';
const USERS_FILE = './users.json';

let userStates = {};

const WITHDRAW_RULES = { min: 200000, max: 2000000, feePercent: 10 };

function loadSettings() {
    if (!fs.existsSync(SETTINGS_FILE)) {
        const defaultSettings = {
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
    if (userId === OWNER_ID) { keyboard.push(['⚙️ لوحة تحكم الإدارة']); }
    return Markup.keyboard(keyboard).resize();
}

function getAdminMenu() {
    return Markup.keyboard([
        ['📞 تعديل سيريتل كاش', '💳 تعديل شام كاش'],
        ['📝 تعديل رسالة الترحيب', '📢 إرسال إذاعة'],
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

// 📞 تعديل زر الدعم الفني ليدخل اللاعب في وضع كتابة المشكلة
bot.hears('📞 الدعم الفني', (ctx) => {
    userStates[ctx.from.id] = { step: 'awaiting_support_msg' };
    ctx.reply('❤️ لا تقلق نحن معك وفريقنا جاهز لخدمتك على مدار الساعة، فقط اكتب المشكلة أو الاستفسار بالتفصيل وأرسله الآن وسنقوم بالرد عليك فوراً:');
});

bot.hears('👤 حسابي الفردي', (ctx) => {
    ctx.replyWithMarkdown(`👤 *تفاصيل حسابك الفردي:*\n\n• الاسم: *${ctx.from.first_name}*\n• المعرف الرقمي: \`${ctx.from.id}\`\n\n📌 رصيد حسابك يتم تحديثه ومراجعته بواسطة نظام الكاشير يدويًا بعد مراجعة إيصالات التعبئة.`);
});

bot.hears('⚙️ لوحة تحكم الإدارة', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return ctx.reply('❌ عذراً، هذا القسم مخصص لمالك البوت فقط.');
    ctx.reply('⚙️ أهلاً بك في لوحة تحكم الإدارة. يرجى اختيار الإجراء المطلوب:', getAdminMenu());
});

bot.hears('📞 تعديل سيريتل كاش', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'edit_syriatel' };
    ctx.reply('✏️ يرجى إرسال رقم السيريتل كاش الجديد الآن:');
});

bot.hears('💳 تعديل شام كاش', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'edit_cham' };
    ctx.reply('✏️ يرجى إرسال عنوان محفظة شام كاش الجديدة الآن:');
});

bot.hears('📝 تعديل رسالة الترحيب', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'edit_welcome' };
    ctx.replyWithMarkdown('✏️ أرسل رسالة الترحيب الجديدة الآن.\n\n💡 *ملاحظة هامة:* ضع كلمة `{name}` في المكان الذي تريد أن يظهر فيه اسم اللاعب تلقائياً.');
});

bot.hears('📢 إرسال إذاعة', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userStates[ctx.from.id] = { step: 'broadcast_msg' };
    ctx.reply('📢 يرجى كتابة وإرسال نص الرسالة التي تريد نشرها لجميع المشتركين الآن:');
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
    
    // 🛠️ معالجة ردود الإدارة على تذاكر دعم اللاعبين داخل المجموعة
    if (ctx.chat.id === ADMIN_GROUP_ID && ctx.message.reply_to_message) {
        const replyText = ctx.message.reply_to_message.text || ctx.message.reply_to_message.caption;
        if (replyText && replyText.includes('ID:')) {
            // استخراج الأرقام الخاصة بـ ID اللاعب من الرسالة الأصلية تلقائياً
            const matches = replyText.match(/ID:\s*(\d+)/);
            if (matches && matches[1]) {
                const targetPlayerId = matches[1];
                try {
                    await bot.telegram.sendMessage(targetPlayerId, `📬 *رد من إدارة فريق بحر على استفسارك:*\n\n💬 ${ctx.message.text}`, { parse_mode: 'Markdown' });
                    return ctx.reply('✅ تم إرسال ردك إلى اللاعب بنجاح.');
                } catch (err) {
                    return ctx.reply('❌ فشل إرسال الرد، قد يكون اللاعب قد حظر البوت.');
                }
            }
        }
    }

    if (currentState) {
        const s = loadSettings();
        
        // تحويل رسالة استفسار اللاعب إلى المجموعة الإدارية
        if (currentState === 'edit_syriatel') {
            s.syriatel_code = ctx.message.text;
            saveSettings(s);
            delete userStates[userId];
            return ctx.reply(`✅ تم تحديث رقم سيريتل كاش بنجاح إلى: ${ctx.message.text}`, getAdminMenu());
        }
        if (currentState === 'edit_cham') {
            s.cham_wallet = ctx.message.text;
            saveSettings(s);
            delete userStates[userId];
            return ctx.reply(`✅ تم تحديث محفظة شام كاش بنجاح إلى: ${ctx.message.text}`, getAdminMenu());
        }
        if (currentState === 'edit_welcome') {
            s.welcome_msg = ctx.message.text;
            saveSettings(s);
            delete userStates[userId];
            return ctx.reply('✅ تم تحديث رسالة الترحيب الديناميكية بنجاح!', getAdminMenu());
        }
        if (currentState === 'broadcast_msg') {
            delete userStates[userId];
            ctx.reply('⏳ جاري بدء الإذاعة ونشر الرسالة...');
            if (fs.existsSync(USERS_FILE)) {
                const users = JSON.parse(fs.readFileSync(USERS_FILE));
                let successCount = 0;
                for (const uId of users) {
                    try { await bot.telegram.sendMessage(uId, ctx.message.text); successCount++; } catch (err) {}
                }
                return ctx.reply(`📢 تمت الإذاعة بنجاح! وصلت لـ ${successCount} لاعب.`);
            }
            return ctx.reply('❌ لا يوجد لاعبون مسجلون للاستقبال.');
        }
        
        // تحويل رسالة تذكرة الدعم إلى المشرفين
        if (currentState === 'awaiting_support_msg') {
            delete userStates[userId];
            await bot.telegram.sendMessage(ADMIN_GROUP_ID, 
                `📞 *رسالة دعم فني جديدة (فريق بحر):*\n` +
                `• من اللاعب: [${ctx.from.first_name}](tg://user?id=${userId})\n` +
                `• حساب اللاعب ID: \`${userId}\`\n\n` +
                `💬 *الرسالة:* "${ctx.message.text}"\n\n` +
                `💡 _للرد على اللاعب، قم بعمل Reply (رد) مباشرة على هذه الرسالة واكتب جوابك._`
            );
            return ctx.reply('✅ تم إرسال رسالتك إلى قسم المشرفين بنجاح، يرجى الانتظار لحين المراجعة والرد عليك هنا.');
        }

        if (currentState === 'awaiting_withdraw_amount') {
            const amount = parseInt(ctx.message.text);
            if (isNaN(amount) || amount <= 0) return ctx.reply('❌ يرجى إدخال مبلغ صحيح بالأرقام فقط.');
            if (amount < WITHDRAW_RULES.min || amount > WITHDRAW_RULES.max) return ctx.reply('❌ الطلب يخرق حدود السحب المسموحة.');
            
            const fee = amount * (WITHDRAW_RULES.feePercent / 100);
            const finalAmount = amount - fee;
            
            await bot.telegram.sendMessage(ADMIN_GROUP_ID, 
