import { Bot, Context, session, SessionFlavor, InlineKeyboard } from "grammy";
import { api } from "./api";
import { UserState } from "./types";

interface SessionData {
  step: "idle" | "awaiting_deposit_player" | "awaiting_deposit_amount" | "awaiting_withdraw_player" | "awaiting_withdraw_amount";
  tempPlayerId?: string;
  tempAmount?: number;
}

type MyContext = Context & SessionFlavor<SessionData>;

export class TexasBot {
  private bot: Bot<MyContext>;
  private users: Map<number, UserState> = new Map();

  constructor() {
    const token = process.env.BOT_TOKEN;
    if (!token) {
      throw new Error("BOT_TOKEN is required in environment variables");
    }

    this.bot = new Bot<MyContext>(token);

    this.bot.use(
      session({
        initial: (): SessionData => ({ step: "idle" }),
      })
    );

    this.setupHandlers();
  }

  private setupHandlers() {
    this.bot.command("start", async (ctx: MyContext) => {
      const from = ctx.from;
      if (!from) return;

      let userState = this.users.get(from.id);
      if (!userState) {
        userState = {
          telegramId: from.id,
          first_name: from.first_name,
          username: from.username,
        };
        this.users.set(from.id, userState);
      }

      const welcomeText =
        `👋 أهلاً بك يا ${from.first_name} في بوت وكالة **Texas4Win** الرسمي 🎰\n\n` +
        `يمكنك من خلال هذا البوت:\n` +
        `✨ إنشاء حساب لاعب جديد فوراً في المنصة\n` +
        `💳 شحن رصيد وإيداع بحسابك\n` +
        `💸 سحب أرباحك ورصيدك\n` +
        `📊 الاستعلام عن رصيدك وحسابك\n\n` +
        (userState.texasPlayerId
          ? `👤 **معرف حسابك في اللعبة:** \`${userState.texasPlayerId}\`\n🔑 **اسم المستخدم:** \`${userState.texasUsername}\``
          : `⚠️ ليس لديك حساب لاعب مسجل بعد. اضغط على الزر أدناه لإنشاء حسابك فوراً!`);

      const keyboard = new InlineKeyboard();

      if (!userState.texasPlayerId) {
        keyboard.text("👤 إنشاء حساب جديد في المنصة", "register_player").row();
      } else {
        keyboard
          .text("💳 شحن رصيد (إيداع)", "deposit")
          .text("💸 سحب رصيد (سحب)", "withdraw")
          .row()
          .text("📊 رصيدي وحسابي", "check_balance")
          .text("🔄 ربط حساب آخر", "link_account")
          .row();
      }

      keyboard.text("💼 رصيد وخزينة الوكيل", "agent_balance").row();

      await ctx.reply(welcomeText, {
        reply_markup: keyboard,
        parse_mode: "Markdown",
      });
    });

    // معالج زر إنشاء حساب
    this.bot.callbackQuery("register_player", async (ctx: MyContext) => {
      const from = ctx.from;
      if (!from) return;

      await ctx.answerCallbackQuery("جاري إنشاء الحساب في السيرفر...");
      await ctx.reply("⏳ جاري إنشاء حسابك في المنصة، يرجى الانتظار ثوانٍ...");

      // توليد اسم مستخدم عشوائي متوافق مع قواعد Texas4Win
      const randomSuffix = Math.floor(1000 + Math.random() * 9000);
      const generatedUsername = `tx_${from.id.toString().slice(-4)}${randomSuffix}`;
      const generatedPassword = `Tx@${Math.floor(100000 + Math.random() * 900000)}`;
      const generatedEmail = `user${from.id}${randomSuffix}@gmail.com`;

      const result = await api.registerPlayer({
        login: generatedUsername,
        password: generatedPassword,
        email: generatedEmail,
      });

      if (result.success) {
        // البحث عن معرف اللاعب الجديد
        const playerInfo = await api.getPlayerInfo({ userName: generatedUsername });
        const playerId = playerInfo?.playerId || "تم الإنشاء بنجاح";

        this.users.set(from.id, {
          telegramId: from.id,
          first_name: from.first_name,
          username: from.username,
          texasPlayerId: playerId !== "تم الإنشاء بنجاح" ? playerId : undefined,
          texasUsername: generatedUsername,
        });

        await ctx.reply(
          `🎉 **تم إنشاء حسابك في المنصة بنجاح!**\n\n` +
            `👤 **اسم المستخدم (Login):** \`${generatedUsername}\`\n` +
            `🔑 **كلمة المرور (Password):** \`${generatedPassword}\`\n` +
            `🆔 **معرف اللاعب (Player ID):** \`${playerId}\`\n\n` +
            `🔗 يمكنك تسجيل الدخول واللعب الآن عبر الموقع الرسمي!\n` +
            `💡 يمكنك شحن حسابك في أي وقت عبر هذا البوت مباشرة.`,
          {
            parse_mode: "Markdown",
            reply_markup: new InlineKeyboard()
              .text("💳 شحن رصيد الآن", "deposit")
              .text("📊 رصيدي وحسابي", "check_balance")
              .row(),
          }
        );
      } else {
        await ctx.reply(
          `❌ عذراً، تعذر إنشاء الحساب حالياً:\n${result.message || "خطأ غير معروف"}\n\nيرجى المحاولة مرة أخرى أو التواصل مع الدعم.`,
          {
            reply_markup: new InlineKeyboard().text("🔄 إعادة المحاولة", "register_player"),
          }
        );
      }
    });

    // معالج استعلام الرصيد
    this.bot.callbackQuery("check_balance", async (ctx: MyContext) => {
      const from = ctx.from;
      if (!from) return;
      const user = this.users.get(from.id);

      if (!user?.texasPlayerId) {
        await ctx.answerCallbackQuery("ليس لديك حساب مسجل!");
        await ctx.reply("⚠️ ليس لديك حساب لاعب مسجل بعد. اضغط على زر إنشاء حساب أولاً.");
        return;
      }

      await ctx.answerCallbackQuery("جاري جلب الرصيد...");
      const bal = await api.getPlayerBalance(user.texasPlayerId);

      if (bal !== null) {
        await ctx.reply(
          `📊 **بيانات حسابك في Texas4Win:**\n\n` +
            `👤 **المستخدم:** \`${user.texasUsername || "غير محدد"}\`\n` +
            `🆔 **معرف اللاعب:** \`${user.texasPlayerId}\`\n` +
            `💰 **الرصيد الحالي:** **${bal.balance} ${bal.currencyCode}**\n`,
          {
            parse_mode: "Markdown",
            reply_markup: new InlineKeyboard()
              .text("💳 شحن رصيد", "deposit")
              .text("💸 سحب رصيد", "withdraw")
              .row(),
          }
        );
      } else {
        await ctx.reply("⚠️ تعذر جلب رصيد اللاعب من السيرفر حالياً.");
      }
    });

    // معالج رصيد الوكيل
    this.bot.callbackQuery("agent_balance", async (ctx: MyContext) => {
      await ctx.answerCallbackQuery("جاري جلب أرصدة الخزينة...");
      const wallets = await api.getAgentWallets();

      if (wallets && wallets.length > 0) {
        let msg = `💼 **أرصدة خزينة ومحافظ الوكيل:**\n\n`;
        wallets.forEach((w: any) => {
          msg += `🪙 **العملة:** ${w.currencyCode} (${w.currencyName || ""})\n`;
          msg += `💵 **الرصيد المتاح:** ${w.availableWallet || w.balance || "0"}\n`;
          msg += `📈 **الائتمان:** ${w.credit || "0"}\n`;
          msg += `--------------------------\n`;
        });
        await ctx.reply(msg, { parse_mode: "Markdown" });
      } else {
        await ctx.reply("💼 تعذر جلب أرصدة خزينة الوكيل حالياً.");
      }
    });

    // معالج بدء الإيداع
    this.bot.callbackQuery("deposit", async (ctx: MyContext) => {
      const from = ctx.from;
      if (!from) return;
      const user = this.users.get(from.id);
      await ctx.answerCallbackQuery();

      if (user?.texasPlayerId) {
        ctx.session.tempPlayerId = user.texasPlayerId;
        ctx.session.step = "awaiting_deposit_amount";
        await ctx.reply(
          `💳 **شحن رصيد للاعب:** \`${user.texasPlayerId}\`\n\nيرجى إرسال **المبلغ** المطلوب شحنه بالأرقام فقط (مثال: 500):`,
          { parse_mode: "Markdown" }
        );
      } else {
        ctx.session.step = "awaiting_deposit_player";
        await ctx.reply("💳 يرجى إرسال **معرف اللاعب (Player ID)** المطلوب شحنه:");
      }
    });

    // معالج بدء السحب
    this.bot.callbackQuery("withdraw", async (ctx: MyContext) => {
      const from = ctx.from;
      if (!from) return;
      const user = this.users.get(from.id);
      await ctx.answerCallbackQuery();

      if (user?.texasPlayerId) {
        ctx.session.tempPlayerId = user.texasPlayerId;
        ctx.session.step = "awaiting_withdraw_amount";
        await ctx.reply(
          `💸 **سحب رصيد من اللاعب:** \`${user.texasPlayerId}\`\n\nيرجى إرسال **المبلغ** المطلوب سحبه بالأرقام فقط:`,
          { parse_mode: "Markdown" }
        );
      } else {
        ctx.session.step = "awaiting_withdraw_player";
        await ctx.reply("💸 يرجى إرسال **معرف اللاعب (Player ID)** المطلوب السحب منه:");
      }
    });

    // استقبال الرسائل النصية
    this.bot.on("message:text", async (ctx: MyContext) => {
      const text = ctx.message?.text?.trim() || "";
      const step = ctx.session.step;

      if (step === "awaiting_deposit_player") {
        ctx.session.tempPlayerId = text;
        ctx.session.step = "awaiting_deposit_amount";
        await ctx.reply(`✅ تم تحديد معرف اللاعب: \`${text}\`\n\nأرسل الآن **المبلغ** المطلوب شحنه:`, {
          parse_mode: "Markdown",
        });
        return;
      }

      if (step === "awaiting_deposit_amount") {
        const amount = parseFloat(text);
        if (isNaN(amount) || amount <= 0) {
          await ctx.reply("❌ يرجى إدخال مبلغ صحيح بالأرقام (أكبر من 0):");
          return;
        }

        const playerId = ctx.session.tempPlayerId!;
        ctx.session.step = "idle";
        await ctx.reply(`⏳ جاري شحن ${amount} للمستخدم \`${playerId}\`...`, { parse_mode: "Markdown" });

        const result = await api.depositToPlayer({
          playerId,
          amount,
        });

        if (result.success) {
          await ctx.reply(
            `✅ **تم الإيداع بنجاح!**\n\n🆔 **اللاعب:** \`${playerId}\`\n💰 **المبلغ المودع:** ${amount}\n💳 **الرصيد الجديد:** ${result.balance ?? "تم التحديث"}`,
            { parse_mode: "Markdown" }
          );
        } else {
          await ctx.reply(`❌ فشل الإيداع:\n${result.message || "خطأ غير معروف"}`);
        }
        return;
      }

      if (step === "awaiting_withdraw_player") {
        ctx.session.tempPlayerId = text;
        ctx.session.step = "awaiting_withdraw_amount";
        await ctx.reply(`✅ تم تحديد معرف اللاعب: \`${text}\`\n\nأرسل الآن **المبلغ** المطلوب سحبه:`, {
          parse_mode: "Markdown",
        });
        return;
      }

      if (step === "awaiting_withdraw_amount") {
        const amount = parseFloat(text);
        if (isNaN(amount) || amount <= 0) {
          await ctx.reply("❌ يرجى إدخال مبلغ صحيح بالأرقام (أكبر من 0):");
          return;
        }

        const playerId = ctx.session.tempPlayerId!;
        ctx.session.step = "idle";
        await ctx.reply(`⏳ جاري سحب ${amount} من اللاعب \`${playerId}\`...`, { parse_mode: "Markdown" });

        const result = await api.withdrawFromPlayer({
          playerId,
          amount,
        });

        if (result.success) {
          await ctx.reply(
            `✅ **تم سحب الرصيد بنجاح!**\n\n🆔 **اللاعب:** \`${playerId}\`\n💸 **المبلغ المسحوب:** ${amount}\n💳 **الرصيد المتبقي:** ${result.balance ?? "تم التحديث"}`,
            { parse_mode: "Markdown" }
          );
        } else {
          await ctx.reply(`❌ فشل السحب:\n${result.message || "خطأ غير معروف"}`);
        }
        return;
      }
    });
  }

  public async start() {
    console.log("Texas4Win Bot is starting polling...");
    await this.bot.start();
  }
}
