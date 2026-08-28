import dotenv from "dotenv";
dotenv.config();

import TelegramBot from "node-telegram-bot-api";
import http from "http";
import { api } from "./api";
import { storage } from "./storage";
import { PlayerAccount, DepositRequest, WithdrawRequest } from "./types";

const BOT_TOKEN = process.env.BOT_TOKEN || "8624354425:AAEYNe5BOSlFNoC-X0SpTCTwNnRre_SMsZE";
const ADMIN_GROUP = process.env.ADMIN_GROUP || "-1003983996094";
const OWNER_ID = Number(process.env.OWNER_ID || "6693251012");
const PORT = Number(process.env.PORT || 3000);

const bot = new TelegramBot(BOT_TOKEN, { polling: true });

const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ status: "ok", bot: "Texas4Win Telegram Bot is Running 24/7" }));
});
server.listen(PORT, "0.0.0.0", () => {
  console.log(`Web health server listening on port ${PORT}`);
});

interface UserState {
  step:
    | "idle"
    | "awaiting_deposit_amount"
    | "awaiting_deposit_receipt"
    | "awaiting_withdraw_amount"
    | "awaiting_withdraw_details"
    | "admin_set_sham_wallet"
    | "admin_set_syriatel_code"
    | "admin_set_min_deposit"
    | "admin_set_min_withdraw";
  depositData?: {
    method: "syriatel" | "sham";
    amount?: number;
  };
  withdrawData?: {
    method: "syriatel" | "sham";
    amount?: number;
  };
}

const userStates = new Map<number, UserState>();

function getState(telegramId: number): UserState {
  if (!userStates.has(telegramId)) {
    userStates.set(telegramId, { step: "idle" });
  }
  return userStates.get(telegramId)!;
}

function resetState(telegramId: number) {
  userStates.set(telegramId, { step: "idle" });
}

function getMainKeyboard(telegramId: number): TelegramBot.InlineKeyboardMarkup {
  const player = storage.getPlayerByTelegramId(telegramId);
  const cfg = storage.getConfig();

  if (!player) {
    return {
      inline_keyboard: [
        [{ text: "👤 إنشاء حساب جديد في المنصة", callback_data: "action_register" }],
        [{ text: "📞 الدعم الفني والمساعدة", callback_data: "action_support" }],
        [{ text: "🌐 زيارة موقع Texas4Win", url: "https://www.texas4win.com" }],
      ],
    };
  }

  return {
    inline_keyboard: [
      [
        { text: "💰 إيداع رصيد (شحن)", callback_data: "action_deposit" },
        { text: "💸 سحب رصيد (كاش)", callback_data: "action_withdraw" },
      ],
      [
        { text: "📊 رصيدي وحسابي", callback_data: "action_balance" },
        { text: "🔑 بيانات الدخول", callback_data: "action_credentials" },
      ],
      [
        { text: "📞 الدعم الفني", callback_data: "action_support" },
        { text: "📢 القناة الرسمية", url: cfg.channelLink },
      ],
      [{ text: "🌐 فتح موقع Texas4Win", url: "https://www.texas4win.com" }],
    ],
  };
}

function getAdminKeyboard(): TelegramBot.InlineKeyboardMarkup {
  return {
    inline_keyboard: [
      [
        { text: "💼 رصيد خزينة الوكيل", callback_data: "admin_wallets" },
        { text: "👥 إحصائيات اللاعبين", callback_data: "admin_stats" },
      ],
      [
        { text: "⚙️ تعديل محفظة شام كاش", callback_data: "admin_edit_sham" },
        { text: "⚙️ تعديل كود سيريتل كاش", callback_data: "admin_edit_syriatel" },
      ],
      [
        { text: "🔻 تعديل الحد الأدنى للإيداع", callback_data: "admin_edit_min_dep" },
        { text: "🔻 تعديل الحد الأدنى للسحب", callback_data: "admin_edit_min_with" },
      ],
    ],
  };
}

bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const telegramId = msg.from?.id || chatId;
  const name = msg.from?.first_name || "عزيزي اللاعب";

  resetState(telegramId);
  const player = storage.getPlayerByTelegramId(telegramId);

  let text = `مرحباً بك يا ${name} في بوت وكالة **Texas4Win** الرسمي 🎰✨\n\n`;

  if (player) {
    text += `🔹 **حسابك المسجل:** \`${player.login}\`\n`;
    text += `🔹 **معرف اللاعب (ID):** \`${player.playerId}\`\n\n`;
    text += `يمكنك شحن رصيدك أو سحب أرباحك فورياً عبر القائمة أدناه:`;
  } else {
    text += `البوت يتيح لك إنشاء حساب فوري، وشحن وسحب الرصيد بأسرع وأسهل طريقة.\n\n`;
    text += `👇 اضغط على **إنشاء حساب جديد** للبدء فوراً:`;
  }

  await bot.sendMessage(chatId, text, {
    parse_mode: "Markdown",
    reply_markup: getMainKeyboard(telegramId),
  });
});

bot.onText(/\/admin/, async (msg) => {
  const chatId = msg.chat.id;
  const telegramId = msg.from?.id || chatId;

  if (telegramId !== OWNER_ID && String(chatId) !== ADMIN_GROUP) {
    return bot.sendMessage(chatId, "⛔️ هذا الأمر مخصص للإدارة فقط.");
  }

  const cfg = storage.getConfig();
  const text =
    `👑 **لوحة تحكم المشرف والوكيل (Texas4Win)**\n\n` +
    `💼 **حساب الوكيل:** \`${process.env.AGENT_USERNAME || "Bero@yahoo.com"}\`\n` +
    `💳 **محفظة شام كاش:** \`${cfg.shamCashWallet}\`\n` +
    `📱 **كود سيريتل كاش:** \`${cfg.syriatelCashCode}\`\n` +
    `💰 **الحد الأدنى للإيداع:** \`${cfg.minDeposit.toLocaleString()} ل.س\`\n` +
    `💸 **الحد الأدنى للسحب:** \`${cfg.minWithdraw.toLocaleString()} ل.س\`\n\n` +
    `اختر من الأزرار أدناه:`;

  await bot.sendMessage(chatId, text, {
    parse_mode: "Markdown",
    reply_markup: getAdminKeyboard(),
  });
});

bot.on("callback_query", async (query) => {
  const chatId = query.message?.chat.id;
  const messageId = query.message?.message_id;
  const telegramId = query.from.id;
  const data = query.data || "";

  if (!chatId) return;

  try {
    await bot.answerCallbackQuery(query.id);

    if (data === "action_register") {
      const existing = storage.getPlayerByTelegramId(telegramId);
      if (existing) {
        return bot.sendMessage(
          chatId,
          `⚠️ لديك حساب مسجل مسبقاً!\n\n🆔 **معرف الحساب:** \`${existing.playerId}\`\n👤 **اسم المستخدم:** \`${existing.login}\``,
          { parse_mode: "Markdown", reply_markup: getMainKeyboard(telegramId) }
        );
      }

      await bot.sendMessage(chatId, "⏳ جاري إنشاء حسابك في المنصة، يرجى الانتظار ثوانٍ...");

      const randNum = Math.floor(100000 + Math.random() * 900000);
      const login = `tx_${randNum}`;
      const password = `Tx#${randNum}!`;
      const email = `tg_${telegramId}_${randNum}@texas4win.com`;

      const regResult = await api.registerPlayer({ login, password, email });

      if (!regResult.success) {
        return bot.sendMessage(
          chatId,
          `❌ عذراً، تعذر إنشاء الحساب حالياً: ${regResult.message || "يرجى المحاولة لاحقاً أو التواصل مع الدعم."}`,
          { reply_markup: getMainKeyboard(telegramId) }
        );
      }

      await new Promise((r) => setTimeout(r, 1500));
      const playerInfo = await api.getPlayerInfo({ userName: login });
      const playerId = playerInfo ? playerInfo.playerId : String(randNum);

      const newAccount: PlayerAccount = {
        telegramId,
        telegramUsername: query.from.username,
        fullName: `${query.from.first_name || ""} ${query.from.last_name || ""}`.trim(),
        playerId,
        login,
        email,
        currency: playerInfo?.currency || "USD",
        createdAt: new Date().toISOString(),
      };

      storage.savePlayer(newAccount);

      const successMsg =
        `🎉 **تم إنشاء حسابك بنجاح في Texas4Win!**\n\n` +
        `🆔 **معرف اللاعب (Player ID):** \`${playerId}\`\n` +
        `👤 **اسم المستخدم:** \`${login}\`\n` +
        `🔑 **كلمة المرور:** \`${password}\`\n` +
        `🌐 **رابط المنصة:** [Texas4Win](https://www.texas4win.com)\n\n` +
        `⚠️ *يرجى حفظ كلمة المرور في مكان آمن وعدم مشاركتها مع أحد.*\n` +
        `👇 يمكنك الآن شحن رصيدك فوراً للبدء:`;

      await bot.sendMessage(chatId, successMsg, {
        parse_mode: "Markdown",
        reply_markup: getMainKeyboard(telegramId),
      });

      const adminNotice =
        `🆕 **تسجيل لاعب جديد في الوكالة**\n\n` +
        `👤 **الاسم:** ${query.from.first_name} (@${query.from.username || "بدون_معرف"})\n` +
        `🆔 **معرف اللاعب:** \`${playerId}\`\n` +
        `👤 **اسم الدخول:** \`${login}\`\n` +
        `📅 **الوقت:** ${new Date().toLocaleString("ar-SA")}`;

      bot.sendMessage(ADMIN_GROUP, adminNotice, { parse_mode: "Markdown" }).catch(() => {});
      return;
    }

    if (data === "action_balance") {
      const player = storage.getPlayerByTelegramId(telegramId);
      if (!player) return bot.sendMessage(chatId, "يرجى إنشاء حساب أولاً.");

      await bot.sendMessage(chatId, "🔄 جاري الاستعلام عن رصيدك المباشر...");
      const bal = await api.getPlayerBalance(player.playerId);

      if (bal !== null) {
        const balMsg =
          `📊 **تفاصيل حسابك المالي**\n\n` +
          `🆔 **معرف اللاعب:** \`${player.playerId}\`\n` +
          `👤 **اسم المستخدم:** \`${player.login}\`\n` +
          `💰 **الرصيد المتاح:** \`${bal.balance.toLocaleString()} ${bal.currencyCode}\`\n` +
          `🌐 **حالة الحساب:** نشط ومتصل بالوكالة ✅`;

        return bot.sendMessage(chatId, balMsg, {
          parse_mode: "Markdown",
          reply_markup: getMainKeyboard(telegramId),
        });
      } else {
        return bot.sendMessage(
          chatId,
          `⚠️ تعذر جلب الرصيد حالياً. حسابك: \`${player.playerId}\``,
          { parse_mode: "Markdown", reply_markup: getMainKeyboard(telegramId) }
        );
      }
    }

    if (data === "action_credentials") {
      const player = storage.getPlayerByTelegramId(telegramId);
      if (!player) return bot.sendMessage(chatId, "يرجى إنشاء حساب أولاً.");

      const credMsg =
        `🔑 **بيانات حسابك في Texas4Win**\n\n` +
        `🆔 **معرف اللاعب (ID):** \`${player.playerId}\`\n` +
        `👤 **اسم المستخدم:** \`${player.login}\`\n` +
        `🌐 **موقع اللعب:** [اضغط هنا للدخول](https://www.texas4win.com)\n\n` +
        `💡 في حال نسيت كلمة المرور تواصل مع الدعم الفني.`;

      return bot.sendMessage(chatId, credMsg, {
        parse_mode: "Markdown",
        reply_markup: getMainKeyboard(telegramId),
      });
    }

    if (data === "action_deposit") {
      const player = storage.getPlayerByTelegramId(telegramId);
      if (!player) return bot.sendMessage(chatId, "يرجى إنشاء حساب أولاً.");

      const cfg = storage.getConfig();
      const depSelectMsg =
        `💳 **شحن الرصيد (الإيداع)**\n\n` +
        `📌 **الحد الأدنى للإيداع:** \`${cfg.minDeposit.toLocaleString()} ل.س\`\n\n` +
        `اختر وسيلة التحويل المناسبة لك أدناه:`;

      return bot.sendMessage(chatId, depSelectMsg, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [{ text: "📱 سيريتل كاش (Syriatel Cash)", callback_data: "dep_method_syriatel" }],
            [{ text: "💳 شام كاش (Sham Cash)", callback_data: "dep_method_sham" }],
            [{ text: "🔙 رجوع للقائمة الرئيسية", callback_data: "action_main_menu" }],
          ],
        },
      });
    }

    if (data === "dep_method_syriatel" || data === "dep_method_sham") {
      const method = data === "dep_method_syriatel" ? "syriatel" : "sham";
      const cfg = storage.getConfig();
      const st = getState(telegramId);
      st.step = "awaiting_deposit_amount";
      st.depositData = { method };

      let payInfo = "";
      if (method === "syriatel") {
        payInfo = `📱 **رمز سيريتل كاش للتحويل:**\n\`${cfg.syriatelCashCode}\`\n*(اضغط على الرقم لنسخه)*`;
      } else {
        payInfo = `💳 **محفظة شام كاش للتحويل:**\n\`${cfg.shamCashWallet}\`\n*(اضغط على العنوان لنسخه)*`;
      }

      const promptMsg =
        `${payInfo}\n\n` +
        `⚠️ **الحد الأدنى:** \`${cfg.minDeposit.toLocaleString()} ل.س\`\n\n` +
        `✍️ **الآن، يرجى كتابة المبلغ الذي قمت بتحويله بالأرقام فقط (مثال: 50000):**`;

      return bot.sendMessage(chatId, promptMsg, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "❌ إلغاء العملية", callback_data: "action_cancel" }]],
        },
      });
    }

    if (data === "action_withdraw") {
      const player = storage.getPlayerByTelegramId(telegramId);
      if (!player) return bot.sendMessage(chatId, "يرجى إنشاء حساب أولاً.");

      const cfg = storage.getConfig();
      const withSelectMsg =
        `💸 **طلب سحب الرصيد (الكاش)**\n\n` +
        `📌 **الحد الأدنى للسحب:** \`${cfg.minWithdraw.toLocaleString()} ل.س\`\n\n` +
        `اختر وسيلة استلام المبلغ:`;

      return bot.sendMessage(chatId, withSelectMsg, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [{ text: "📱 استلام عبر سيريتل كاش", callback_data: "with_method_syriatel" }],
            [{ text: "💳 استلام عبر شام كاش", callback_data: "with_method_sham" }],
            [{ text: "🔙 رجوع للقائمة الرئيسية", callback_data: "action_main_menu" }],
          ],
        },
      });
    }

    if (data === "with_method_syriatel" || data === "with_method_sham") {
      const method = data === "with_method_syriatel" ? "syriatel" : "sham";
      const cfg = storage.getConfig();
      const st = getState(telegramId);
      st.step = "awaiting_withdraw_amount";
      st.withdrawData = { method };

      const promptMsg =
        `💸 **سحب عبر ${method === "syriatel" ? "سيريتل كاش" : "شام كاش"}**\n\n` +
        `📌 **الحد الأدنى للسحب:** \`${cfg.minWithdraw.toLocaleString()} ل.س\`\n\n` +
        `✍️ **اكتب المبلغ المطلوب سحبه بالأرقام فقط (مثال: 30000):**`;

      return bot.sendMessage(chatId, promptMsg, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "❌ إلغاء العملية", callback_data: "action_cancel" }]],
        },
      });
    }

    if (data === "action_support") {
      const cfg = storage.getConfig();
      return bot.sendMessage(
        chatId,
        `📞 **الدعم الفني والخدمة المباشرة**\n\n` +
          `نحن هنا لمساعدتك على مدار الساعة في عمليات الشحن، السحب، أو أي استفسار.\n\n` +
          `👤 **تواصل مع المشرف:** @${cfg.supportUsername}\n` +
          `📢 **القناة الرسمية:** [اضغط هنا](${cfg.channelLink})`,
        { parse_mode: "Markdown", reply_markup: getMainKeyboard(telegramId) }
      );
    }

    if (data === "action_cancel" || data === "action_main_menu") {
      resetState(telegramId);
      return bot.sendMessage(chatId, "تم الرجوع للقائمة الرئيسية.", {
        reply_markup: getMainKeyboard(telegramId),
      });
    }

    // قبول الإيداع من المشرف
    if (data.startsWith("adm_app_dep_")) {
      const depId = data.replace("adm_app_dep_", "");
      const deposit = storage.getDeposit(depId);

      if (!deposit) return bot.sendMessage(chatId, "لم يتم العثور على هذا الطلب.");
      if (deposit.status !== "pending") {
        return bot.sendMessage(chatId, `⚠️ هذا الطلب تمت معالجته مسبقاً (الحالة: ${deposit.status}).`);
      }

      await bot.sendMessage(chatId, `⏳ جاري شحن الرصيد للاعب \`${deposit.playerId}\`...`);

      const depApiRes = await api.depositToPlayer({
        playerId: deposit.playerId,
        amount: deposit.amount,
        comment: `Telegram Deposit #${deposit.id}`,
      });

      if (depApiRes.success) {
        deposit.status = "approved";
        deposit.processedAt = new Date().toISOString();
        deposit.processedBy = query.from.first_name;
        storage.saveDeposit(deposit);

        await bot.editMessageCaption(
          `✅ **تم قبول طلب الإيداع وشحن الرصيد بنجاح!**\n\n` +
            `👤 اللاعب: \`${deposit.playerId}\`\n` +
            `💰 المبلغ: \`${deposit.amount.toLocaleString()}\`\n` +
            `👨‍💼 تمت الموافقة بواسطة: ${query.from.first_name}`,
          { chat_id: chatId, message_id: messageId }
        );

        bot.sendMessage(
          deposit.telegramId,
          `🎉 **تهانينا! تم شحن رصيدك بنجاح** ✅\n\n` +
            `💰 **المبلغ المضاف:** \`${deposit.amount.toLocaleString()} ل.س\`\n` +
            `🆔 **معرف الحساب:** \`${deposit.playerId}\`\n\n` +
            `نتمنى لك أوقاتاً ممتعة وحظاً وفيراً! 🎰✨`,
          { parse_mode: "Markdown", reply_markup: getMainKeyboard(deposit.telegramId) }
        ).catch(() => {});
      } else {
        await bot.sendMessage(
          chatId,
          `❌ فشل إيداع الرصيد في السيرفر: ${depApiRes.message || "خطأ غير معروف"}`
        );
      }
      return;
    }

    // رفض الإيداع
    if (data.startsWith("adm_rej_dep_")) {
      const depId = data.replace("adm_rej_dep_", "");
      const deposit = storage.getDeposit(depId);

      if (!deposit || deposit.status !== "pending") {
        return bot.sendMessage(chatId, "هذا الطلب غير متاح أو تمت معالجته.");
      }

      deposit.status = "rejected";
      deposit.processedAt = new Date().toISOString();
      deposit.processedBy = query.from.first_name;
      storage.saveDeposit(deposit);

      await bot.editMessageCaption(
        `❌ **تم رفض طلب الإيداع**\n\n` +
          `👤 اللاعب: \`${deposit.playerId}\`\n` +
          `💰 المبلغ: \`${deposit.amount.toLocaleString()}\`\n` +
          `👨‍💼 المشرف: ${query.from.first_name}`,
        { chat_id: chatId, message_id: messageId }
      );

      bot.sendMessage(
        deposit.telegramId,
        `❌ **عذراً، تم رفض طلب الإيداع الخاص بك**\n\n` +
          `المبلغ: \`${deposit.amount.toLocaleString()} ل.س\`\n` +
          `يرجى التأكد من صحة إشعار التحويل والتواصل مع الدعم الفني في حال وجود استفسار.`,
        { parse_mode: "Markdown", reply_markup: getMainKeyboard(deposit.telegramId) }
      ).catch(() => {});
      return;
    }

    // موافقة وخصم السحب
    if (data.startsWith("adm_app_with_")) {
      const withId = data.replace("adm_app_with_", "");
      const withdraw = storage.getWithdraw(withId);

      if (!withdraw || withdraw.status !== "pending") {
        return bot.sendMessage(chatId, "هذا الطلب تمت معالجته مسبقاً.");
      }

      await bot.sendMessage(chatId, `⏳ جاري خصم الرصيد من حساب اللاعب \`${withdraw.playerId}\`...`);

      const withApiRes = await api.withdrawFromPlayer({
        playerId: withdraw.playerId,
        amount: withdraw.amount,
        comment: `Telegram Withdraw #${withdraw.id}`,
      });

      if (withApiRes.success) {
        withdraw.status = "approved";
        withdraw.processedAt = new Date().toISOString();
        withdraw.processedBy = query.from.first_name;
        storage.saveWithdraw(withdraw);

        await bot.editMessageText(
          `✅ **تمت الموافقة على السحب وخصم الرصيد من المنصة!**\n\n` +
            `👤 اللاعب: \`${withdraw.playerId}\`\n` +
            `💸 المبلغ: \`${withdraw.amount.toLocaleString()} ل.س\`\n` +
            `💳 تفاصيل التحويل: \`${withdraw.accountDetails}\`\n` +
            `👨‍💼 تمت المعالجة بواسطة: ${query.from.first_name}`,
          { chat_id: chatId, message_id: messageId }
        );

        bot.sendMessage(
          withdraw.telegramId,
          `✅ **تمت معالجة طلب السحب بنجاح!**\n\n` +
            `💸 **المبلغ:** \`${withdraw.amount.toLocaleString()} ل.س\`\n` +
            `💳 **المحفظة/الرقم المحول إليه:** \`${withdraw.accountDetails}\`\n\n` +
            `شكراً لثقتكم بنا! ✨`,
          { parse_mode: "Markdown", reply_markup: getMainKeyboard(withdraw.telegramId) }
        ).catch(() => {});
      } else {
        await bot.sendMessage(
          chatId,
          `❌ فشل خصم الرصيد من السيرفر: ${withApiRes.message || "تأكد من كفاية رصيد اللاعب"}`
        );
      }
      return;
    }

    // رفض السحب
    if (data.startsWith("adm_rej_with_")) {
      const withId = data.replace("adm_rej_with_", "");
      const withdraw = storage.getWithdraw(withId);

      if (!withdraw || withdraw.status !== "pending") {
        return bot.sendMessage(chatId, "هذا الطلب تمت معالجته مسبقاً.");
      }

      withdraw.status = "rejected";
      withdraw.processedAt = new Date().toISOString();
      withdraw.processedBy = query.from.first_name;
      storage.saveWithdraw(withdraw);

      await bot.editMessageText(
        `❌ **تم رفض طلب السحب**\n\n` +
          `👤 اللاعب: \`${withdraw.playerId}\`\n` +
          `💸 المبلغ: \`${withdraw.amount.toLocaleString()}\`\n` +
          `👨‍💼 المشرف: ${query.from.first_name}`,
        { chat_id: chatId, message_id: messageId }
      );

      bot.sendMessage(
        withdraw.telegramId,
        `❌ **عذراً، تم رفض طلب السحب الخاص بك**\n\n` +
          `المبلغ: \`${withdraw.amount.toLocaleString()} ل.س\`\n` +
          `يرجى مراجعة الدعم الفني للاستفسار.`,
        { parse_mode: "Markdown", reply_markup: getMainKeyboard(withdraw.telegramId) }
      ).catch(() => {});
      return;
    }

    if (data === "admin_wallets") {
      await bot.sendMessage(chatId, "🔄 جاري جلب أرصدة خزينة الوكيل...");
      const wallets = await api.getAgentWallets();

      if (wallets.length === 0) {
        return bot.sendMessage(chatId, "⚠️ تعذر جلب محافظ الوكيل حالياً.");
      }

      let wText = `💼 **أرصدة محافظ وخزينة الوكيل:**\n\n`;
      wallets.forEach((w) => {
        wText += `🔹 **${w.currencyName} (${w.currencyCode}):**\n`;
        wText += `   - الرصيد المتاح: \`${w.availableWallet}\`\n`;
        wText += `   - الرصيد الكلي: \`${w.balance}\`\n`;
        wText += `   - الائتمان: \`${w.credit}\`\n\n`;
      });

      return bot.sendMessage(chatId, wText, { parse_mode: "Markdown", reply_markup: getAdminKeyboard() });
    }

    if (data === "admin_stats") {
      const players = storage.getAllPlayers();
      const statText =
        `👥 **إحصائيات وكالة Texas4Win**\n\n` +
        `👤 **إجمالي اللاعبين المسجلين:** \`${players.length}\` لاعب\n` +
        `📅 تاريخ اليوم: ${new Date().toLocaleDateString("ar-SA")}`;

      return bot.sendMessage(chatId, statText, { parse_mode: "Markdown", reply_markup: getAdminKeyboard() });
    }

    if (data === "admin_edit_sham") {
      const st = getState(telegramId);
      st.step = "admin_set_sham_wallet";
      return bot.sendMessage(chatId, "✍️ أرسل الآن عنوان محفظة شام كاش الجديد:");
    }

    if (data === "admin_edit_syriatel") {
      const st = getState(telegramId);
      st.step = "admin_set_syriatel_code";
      return bot.sendMessage(chatId, "✍️ أرسل الآن رمز سيريتل كاش الجديد:");
    }

    if (data === "admin_edit_min_dep") {
      const st = getState(telegramId);
      st.step = "admin_set_min_deposit";
      return bot.sendMessage(chatId, "✍️ أرسل الحد الأدنى للإيداع الجديد (بالأرقام):");
    }

    if (data === "admin_edit_min_with") {
      const st = getState(telegramId);
      st.step = "admin_set_min_withdraw";
      return bot.sendMessage(chatId, "✍️ أرسل الحد الأدنى للسحب الجديد (بالأرقام):");
    }
  } catch (err: any) {
    console.error("Callback error:", err);
    bot.sendMessage(chatId, "حدث خطأ غير متوقع، يرجى المحاولة مرة أخرى.");
  }
});

bot.on("message", async (msg) => {
  if (msg.text?.startsWith("/start") || msg.text?.startsWith("/admin")) return;

  const chatId = msg.chat.id;
  const telegramId = msg.from?.id || chatId;
  const st = getState(telegramId);

  try {
    if (st.step === "awaiting_deposit_amount" && msg.text) {
      const amount = parseInt(msg.text.replace(/[^0-9]/g, ""), 10);
      const cfg = storage.getConfig();

      if (isNaN(amount) || amount < cfg.minDeposit) {
        return bot.sendMessage(
          chatId,
          `⚠️ المبلغ غير صالح أو أقل من الحد الأدنى (\`${cfg.minDeposit.toLocaleString()} ل.س\`).\nيرجى كتابة رقم صحيح:`
        );
      }

      st.depositData!.amount = amount;
      st.step = "awaiting_deposit_receipt";

      const receiptPrompt =
        `✅ **المبلغ المطلوب إيداعه:** \`${amount.toLocaleString()} ل.س\`\n\n` +
        `📸 **الآن يرجى إرسال صورة إشعار التحويل (سكرين شوت أو إيصال الدفع) أو كتابة رقم عملية التحويل:**`;

      return bot.sendMessage(chatId, receiptPrompt, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "❌ إلغاء", callback_data: "action_cancel" }]],
        },
      });
    }

    if (st.step === "awaiting_deposit_receipt") {
      const player = storage.getPlayerByTelegramId(telegramId);
      if (!player) return resetState(telegramId);

      const depId = `DEP-${Date.now().toString().slice(-6)}`;
      const amount = st.depositData!.amount || 0;
      const method = st.depositData!.method || "syriatel";

      const depositReq: DepositRequest = {
        id: depId,
        telegramId,
        telegramUsername: msg.from?.username,
        playerId: player.playerId,
        amount,
        method,
        referenceNumber: msg.text || undefined,
        photoFileId: msg.photo ? msg.photo[msg.photo.length - 1].file_id : undefined,
        status: "pending",
        createdAt: new Date().toISOString(),
      };

      storage.saveDeposit(depositReq);
      resetState(telegramId);

      await bot.sendMessage(
        chatId,
        `✅ **تم استلام طلب الإيداع الخاص بك بنجاح!**\n\n` +
          `🔖 رقم الطلب: \`#${depId}\`\n` +
          `💰 المبلغ: \`${amount.toLocaleString()} ل.س\`\n` +
          `⏳ يتم مراجعة الإشعار من قبل الإدارة وشحن رصيدك خلال دقائق معدودة.`,
        { parse_mode: "Markdown", reply_markup: getMainKeyboard(telegramId) }
      );

      const adminCaption =
        `🔔 **طلب إيداع جديد #${depId}**\n\n` +
        `👤 اللاعب: ${msg.from?.first_name} (@${msg.from?.username || "بدون_معرف"})\n` +
        `🆔 معرف الحساب: \`${player.playerId}\`\n` +
        `👤 اسم الدخول: \`${player.login}\`\n` +
        `💰 المبلغ: \`${amount.toLocaleString()} ل.س\`\n` +
        `💳 الوسيلة: ${method === "syriatel" ? "سيريتل كاش" : "شام كاش"}\n` +
        (msg.text ? `📝 رقم العملية/الملاحظة: \`${msg.text}\`\n` : "") +
        `📅 الوقت: ${new Date().toLocaleString("ar-SA")}`;

      const adminButtons: TelegramBot.InlineKeyboardMarkup = {
        inline_keyboard: [
          [
            { text: "✅ موافقة وشحن تلقائي", callback_data: `adm_app_dep_${depId}` },
            { text: "❌ رفض الطلب", callback_data: `adm_rej_dep_${depId}` },
          ],
        ],
      };

      if (depositReq.photoFileId) {
        bot.sendPhoto(ADMIN_GROUP, depositReq.photoFileId, {
          caption: adminCaption,
          parse_mode: "Markdown",
          reply_markup: adminButtons,
        }).catch(() => {});
      } else {
        bot.sendMessage(ADMIN_GROUP, adminCaption, {
          parse_mode: "Markdown",
          reply_markup: adminButtons,
        }).catch(() => {});
      }
      return;
    }

    if (st.step === "awaiting_withdraw_amount" && msg.text) {
      const amount = parseInt(msg.text.replace(/[^0-9]/g, ""), 10);
      const cfg = storage.getConfig();
      const player = storage.getPlayerByTelegramId(telegramId);

      if (isNaN(amount) || amount < cfg.minWithdraw) {
        return bot.sendMessage(
          chatId,
          `⚠️ المبلغ أقل من الحد الأدنى للسحب (\`${cfg.minWithdraw.toLocaleString()} ل.س\`).\nيرجى كتابة رقم صحيح:`
        );
      }

      if (player) {
        const liveBal = await api.getPlayerBalance(player.playerId);
        if (liveBal && liveBal.balance < amount) {
          return bot.sendMessage(
            chatId,
            `⚠️ رصيدك الحالي في المنصة هو: \`${liveBal.balance.toLocaleString()} ${liveBal.currencyCode}\` وهو غير كافٍ لسحب \`${amount.toLocaleString()} ل.س\`!`
          );
        }
      }

      st.withdrawData!.amount = amount;
      st.step = "awaiting_withdraw_details";

      const detailsPrompt =
        `💸 **المبلغ المطلوب سحبه:** \`${amount.toLocaleString()} ل.س\`\n\n` +
        `✍️ **الآن يرجى إرسال رقم هاتفك أو عنوان محفظتك لاستلام المبلغ عليها:**`;

      return bot.sendMessage(chatId, detailsPrompt, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "❌ إلغاء", callback_data: "action_cancel" }]],
        },
      });
    }

    if (st.step === "awaiting_withdraw_details" && msg.text) {
      const player = storage.getPlayerByTelegramId(telegramId);
      if (!player) return resetState(telegramId);

      const withId = `WIT-${Date.now().toString().slice(-6)}`;
      const amount = st.withdrawData!.amount || 0;
      const method = st.withdrawData!.method || "syriatel";
      const accountDetails = msg.text.trim();

      const withdrawReq: WithdrawRequest = {
        id: withId,
        telegramId,
        telegramUsername: msg.from?.username,
        playerId: player.playerId,
        amount,
        method,
        accountDetails,
        status: "pending",
        createdAt: new Date().toISOString(),
      };

      storage.saveWithdraw(withdrawReq);
      resetState(telegramId);

      await bot.sendMessage(
        chatId,
        `✅ **تم إرسال طلب السحب الخاص بك بنجاح!**\n\n` +
          `🔖 رقم الطلب: \`#${withId}\`\n` +
          `💸 المبلغ: \`${amount.toLocaleString()} ل.س\`\n` +
          `📱 وسيلة الاستلام: \`${accountDetails}\`\n\n` +
          `سيتم تحويل المبلغ لبياناتك وخصمه بعد مراجعة الإدارة فوراً.`,
        { parse_mode: "Markdown", reply_markup: getMainKeyboard(telegramId) }
      );

      const adminWithMsg =
        `🚨 **طلب سحب رصيد جديد #${withId}**\n\n` +
        `👤 اللاعب: ${msg.from?.first_name} (@${msg.from?.username || "بدون_معرف"})\n` +
        `🆔 معرف الحساب: \`${player.playerId}\`\n` +
        `👤 اسم الدخول: \`${player.login}\`\n` +
        `💸 المبلغ المطلوب: \`${amount.toLocaleString()} ل.س\`\n` +
        `💳 وسيلة الاستلام: ${method === "syriatel" ? "سيريتل كاش" : "شام كاش"}\n` +
        `📱 الحساب/الرقم المحول إليه: \`${accountDetails}\`\n` +
        `📅 الوقت: ${new Date().toLocaleString("ar-SA")}`;

      const adminWithButtons: TelegramBot.InlineKeyboardMarkup = {
        inline_keyboard: [
          [
            { text: "✅ تم التحويل (خصم الرصيد)", callback_data: `adm_app_with_${withId}` },
            { text: "❌ رفض السحب", callback_data: `adm_rej_with_${withId}` },
          ],
        ],
      };

      bot.sendMessage(ADMIN_GROUP, adminWithMsg, {
        parse_mode: "Markdown",
        reply_markup: adminWithButtons,
      }).catch(() => {});
      return;
    }

    if (telegramId === OWNER_ID || String(chatId) === ADMIN_GROUP) {
      if (st.step === "admin_set_sham_wallet" && msg.text) {
        storage.saveConfig({ shamCashWallet: msg.text.trim() });
        resetState(telegramId);
        return bot.sendMessage(chatId, `✅ تم تحديث عنوان محفظة شام كاش إلى:\n\`${msg.text.trim()}\``, {
          parse_mode: "Markdown",
          reply_markup: getAdminKeyboard(),
        });
      }

      if (st.step === "admin_set_syriatel_code" && msg.text) {
        storage.saveConfig({ syriatelCashCode: msg.text.trim() });
        resetState(telegramId);
        return bot.sendMessage(chatId, `✅ تم تحديث كود سيريتل كاش إلى:\n\`${msg.text.trim()}\``, {
          parse_mode: "Markdown",
          reply_markup: getAdminKeyboard(),
        });
      }

      if (st.step === "admin_set_min_deposit" && msg.text) {
        const val = parseInt(msg.text.replace(/[^0-9]/g, ""), 10);
        if (!isNaN(val) && val > 0) {
          storage.saveConfig({ minDeposit: val });
          resetState(telegramId);
          return bot.sendMessage(chatId, `✅ تم تحديث الحد الأدنى للإيداع إلى: \`${val.toLocaleString()} ل.س\``, {
            parse_mode: "Markdown",
            reply_markup: getAdminKeyboard(),
          });
        }
      }

      if (st.step === "admin_set_min_withdraw" && msg.text) {
        const val = parseInt(msg.text.replace(/[^0-9]/g, ""), 10);
        if (!isNaN(val) && val > 0) {
          storage.saveConfig({ minWithdraw: val });
          resetState(telegramId);
          return bot.sendMessage(chatId, `✅ تم تحديث الحد الأدنى للسحب إلى: \`${val.toLocaleString()} ل.س\``, {
            parse_mode: "Markdown",
            reply_markup: getAdminKeyboard(),
          });
        }
      }
    }
  } catch (error) {
    console.error("Message handler error:", error);
  }
});

console.log("Texas4Win Telegram Bot started successfully! 🚀");
