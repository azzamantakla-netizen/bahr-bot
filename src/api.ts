import axios from "axios";
import { ApiResponse } from "./types";

export class Texas4WinApi {
  private baseUrl: string;
  private username: string;
  private password: string;
  private parentId: string;
  private cookieJar: string = "";
  private isSignedIn: boolean = false;
  private scraperApiKey: string = "";
  private sessionId: string = "";

  constructor() {
    let rawUrl = (process.env.API_BASE_URL || "https://agents.texas4win.com").trim();
    if (!rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
      rawUrl = `https://${rawUrl}`;
    }
    this.baseUrl = rawUrl.replace(/\/$/, "");

    this.username = process.env.AGENT_USERNAME || "Bero@yahoo.com";
    this.password = process.env.AGENT_PASSWORD || "Aazzam@318";
    this.parentId = process.env.PARENT_ID || "2688288";
    this.scraperApiKey = (process.env.SCRAPER_API_KEY || "00acfebcc34a0df66a59f0abddf28243").trim();
    this.sessionId = `sess_${Math.floor(100000 + Math.random() * 900000)}`;

    if (process.env.COOKIE) {
      this.cookieJar = process.env.COOKIE;
    }
  }

  /**
   * استخراج وتحديث الكوكيز من ردود السيرفر
   */
  private updateCookies(setCookieHeader: any) {
    if (!setCookieHeader) return;
    const cookiesArray = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
    const cookieMap = new Map<string, string>();

    if (this.cookieJar) {
      this.cookieJar.split(";").forEach((pair) => {
        const [k, ...v] = pair.split("=");
        if (k && v.length > 0) {
          cookieMap.set(k.trim(), v.join("=").trim());
        }
      });
    }

    cookiesArray.forEach((header) => {
      const part = header.split(";")[0].trim();
      const [k, ...v] = part.split("=");
      if (k && v.length > 0) {
        cookieMap.set(k.trim(), v.join("=").trim());
      }
    });

    const combined: string[] = [];
    cookieMap.forEach((v, k) => combined.push(`${k}=${v}`));
    this.cookieJar = combined.join("; ");
  }

  /**
   * تنفيذ طلب موجه مع الحفاظ التام على الهيدرز والكوكيز
   */
  private async executeRequest<T = any>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    const targetUrl = `${this.baseUrl}${endpoint}`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json;charset=UTF-8",
      "Accept": "application/json, text/plain, */*",
      "X-Requested-With": "XMLHttpRequest",
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
      "Origin": "https://agents.texas4win.com",
      "Referer": "https://agents.texas4win.com/",
    };

    if (this.cookieJar) {
      headers["Cookie"] = this.cookieJar;
    }

    if (this.scraperApiKey) {
      const scraperUrl = `http://api.scraperapi.com/?api_key=${this.scraperApiKey}&url=${encodeURIComponent(
        targetUrl
      )}&keep_headers=true&session_number=${this.sessionId}`;

      const res = await axios.post<ApiResponse<T>>(scraperUrl, body, {
        headers,
        timeout: 45000,
      });

      this.updateCookies(res.headers["set-cookie"]);
      return res.data;
    } else {
      const res = await axios.post<ApiResponse<T>>(targetUrl, body, {
        headers,
        timeout: 45000,
        withCredentials: true,
      });

      this.updateCookies(res.headers["set-cookie"]);
      return res.data;
    }
  }

  /**
   * تسجيل الدخول في المنصة
   */
  public async signIn(): Promise<boolean> {
    try {
      console.log(`[BOT-API] Attempting agent sign in to: ${this.baseUrl}/global/api/User/signIn via ScraperAPI`);

      const data = await this.executeRequest<{ type: number; message: string }>("/global/api/User/signIn", {
        username: this.username,
        password: this.password,
      });

      console.log(`[BOT-API] SignIn Response:`, JSON.stringify(data));

      if (data && (data.status || data.result)) {
        this.isSignedIn = true;
        console.log(`[BOT-API] Signed in successfully! Session Cookies:`, this.cookieJar);
        return true;
      }

      const notif = data?.notification?.[0]?.content;
      throw new Error(notif || "فشل التحقق من بيانات تسجيل الدخول في السيرفر");
    } catch (error: any) {
      const resp = error?.response;
      console.error(
        `[BOT-API] SignIn Error: HTTP ${resp?.status || "NO_RESPONSE"} |`,
        resp?.data ? JSON.stringify(resp.data) : error.message
      );

      const msg =
        resp?.data?.notification?.[0]?.content ||
        (resp?.status === 403 ? "حماية Cloudflare منعت تسجيل الدخول (403)" : null) ||
        error.message ||
        "تعذر تسجيل الدخول في سيرفر الوكالة";

      throw new Error(msg);
    }
  }

  /**
   * إرسال طلب موثق
   */
  private async postAuth<T = any>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    if (!this.isSignedIn || !this.cookieJar) {
      await this.signIn();
    }

    try {
      console.log(`[BOT-API] Sending POST to: ${this.baseUrl}${endpoint} Body:`, JSON.stringify(body));
      const data = await this.executeRequest<T>(endpoint, body);
      console.log(`[BOT-API] POST ${endpoint} Response:`, JSON.stringify(data));
      return data;
    } catch (error: any) {
      const status = error?.response?.status;
      console.error(`[BOT-API] POST ${endpoint} Error HTTP ${status}:`, error?.response?.data || error.message);
      throw error;
    }
  }

  /**
   * 1. إنشاء حساب جديد للاعب (Register Player)
   */
  public async registerPlayer(params: {
    login: string;
    password: string;
    email: string;
  }): Promise<{ success: boolean; message?: string }> {
    try {
      const login = String(params.login).trim();
      const password = String(params.password).trim();
      const email = String(params.email).trim().toLowerCase();
      const parentId = String(this.parentId).trim();

      const res = await this.postAuth("/global/api/User/registerPlayer", {
        player: {
          login,
          password,
          email,
          parentId,
        },
      });

      if (res && (res.status === true || (res.result && typeof res.result === "object"))) {
        return { success: true };
      }

      return {
        success: false,
        message: res?.notification?.[0]?.content || "تعذر إنشاء الحساب في السيرفر",
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.notification?.[0]?.content || error.message || "خطأ أثناء إنشاء الحساب",
      };
    }
  }

  /**
   * 2. البحث عن بيانات اللاعب
   */
  public async getPlayerInfo(search: {
    playerId?: string;
    userName?: string;
  }): Promise<{
    playerId: string;
    username: string;
    currency: string;
    registerDate: string;
  } | null> {
    try {
      const filter: any = {
        withoutTotalCount: {
          action: "=",
          value: true,
        },
      };

      if (search.playerId) {
        filter.playerId = {
          action: "=",
          value: String(search.playerId),
          valueLabel: String(search.playerId),
        };
      } else if (search.userName) {
        filter.userName = {
          action: "like",
          value: search.userName,
          valueLabel: search.userName,
        };
      }

      let res: ApiResponse<any> = await this.postAuth("/global/api/User/getPlayers", {
        start: 0,
        limit: 20,
        filter,
        isNextPage: false,
      });

      if (!res?.status) {
        res = await this.postAuth("/global/api/User/getPlayersForCurrentAgent", {
          start: 0,
          limit: 20,
          filter,
          isNextPage: false,
        });
      }

      const records = res.result?.records || (Array.isArray(res.result) ? res.result : []);
      if (res.status && records.length > 0) {
        const record = records[0];
        return {
          playerId: String(record.playerId || record.id),
          username: record.username || record.login,
          currency: record.currency || record.currencyCode || "NSP",
          registerDate: record.registerDate || "",
        };
      }

      return null;
    } catch (error: any) {
      console.error("getPlayerInfo error:", error?.response?.data || error.message);
      return null;
    }
  }

  /**
   * 3. جلب رصيد اللاعب
   */
  public async getPlayerBalance(playerId: string): Promise<{
    balance: number;
    currencyCode: string;
  } | null> {
    try {
      let res = await this.postAuth<any>("/global/api/User/getPlayerBalanceById", {
        playerId: String(playerId),
      });

      if (!res?.status) {
        res = await this.postAuth<any>("/global/api/User/getPlayerBalance", {
          playerId: String(playerId),
        });
      }

      if (res.status && Array.isArray(res.result) && res.result.length > 0) {
        const mainWallet =
          res.result.find((w: { balance: number; currencyCode: string; main: boolean }) => w.main) || res.result[0];
        return {
          balance: Number(mainWallet.balance) || 0,
          currencyCode: mainWallet.currencyCode || "NSP",
        };
      } else if (res.status && typeof res.result?.balance !== "undefined") {
        return {
          balance: Number(res.result.balance) || 0,
          currencyCode: res.result.currencyCode || "NSP",
        };
      }

      return null;
    } catch (error: any) {
      console.error("getPlayerBalance error:", error?.response?.data || error.message);
      return null;
    }
  }

  /**
   * 4. إيداع وشحن رصيد للاعب
   */
  public async depositToPlayer(params: {
    playerId: string;
    amount: number;
    currencyCode?: string;
    comment?: string | null;
  }): Promise<{
    success: boolean;
    balance?: number;
    message?: string;
  }> {
    try {
      const currency = params.currencyCode || process.env.DEFAULT_CURRENCY || "NSP";
      const res = await this.postAuth<{ balance: number; currencyCode: string }>(
        "/global/api/User/depositToPlayer",
        {
          amount: Math.abs(params.amount),
          comment: params.comment || null,
          playerId: String(params.playerId),
          currencyCode: currency,
          moneyStatus: 5,
        }
      );

      if (res.status && res.result) {
        return {
          success: true,
          balance: res.result.balance,
        };
      }

      return {
        success: false,
        message: res.notification?.[0]?.content || "تعذر تنفيذ الإيداع للاعب",
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.notification?.[0]?.content || error.message || "خطأ أثناء الإيداع",
      };
    }
  }

  /**
   * 5. سحب رصيد من اللاعب
   */
  public async withdrawFromPlayer(params: {
    playerId: string;
    amount: number;
    currencyCode?: string;
    comment?: string | null;
  }): Promise<{
    success: boolean;
    balance?: number;
    message?: string;
  }> {
    try {
      const currency = params.currencyCode || process.env.DEFAULT_CURRENCY || "NSP";

      const res = await this.postAuth<{ balance: number; currencyCode: string }>(
        "/global/api/User/withdrawFromPlayer",
        {
          amount: Math.abs(params.amount),
          comment: params.comment || null,
          playerId: String(params.playerId),
          currencyCode: currency,
          moneyStatus: 5,
        }
      );

      if (res.status && res.result) {
        return {
          success: true,
          balance: res.result.balance,
        };
      }

      return {
        success: false,
        message: res.notification?.[0]?.content || "تعذر تنفيذ سحب الرصيد من اللاعب",
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.notification?.[0]?.content || error.message || "خطأ أثناء السحب",
      };
    }
  }

  /**
   * 6. أرصدة محافظ وخزينة الوكيل
   */
  public async getAgentWallets(): Promise<
    Array<{
      currencyCode: string;
      currencyName: string;
      availableWallet: string;
      balance: string;
      credit: string;
    }>
  > {
    try {
      const res = await this.postAuth<any[]>("/global/api/User/getAgentAllWallets", {});
      if (res.status && Array.isArray(res.result)) {
        return res.result;
      }
      return [];
    } catch (error: any) {
      return [];
    }
  }
}

export const api = new Texas4WinApi();
export default api;
