import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from "axios";
import { ApiResponse } from "./types";

export class Texas4WinApi {
  private client: AxiosInstance;
  private baseUrl: string;
  private username: string;
  private password: string;
  private parentId: string;
  private cookieJar: string = "";
  private isSignedIn: boolean = false;

  constructor() {
    let rawUrl = (process.env.API_BASE_URL || "https://agents.texas4win.com").trim();
    if (!rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
      rawUrl = `https://${rawUrl}`;
    }
    this.baseUrl = rawUrl.replace(/\/$/, "");

    this.username = process.env.AGENT_USERNAME || "Bero@yahoo.com";
    this.password = process.env.AGENT_PASSWORD || "Aazzam@318";
    this.parentId = process.env.PARENT_ID || "2688288";

    if (process.env.COOKIE) {
      this.cookieJar = process.env.COOKIE;
    }

    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://agents.texas4win.com",
        "Referer": "https://agents.texas4win.com/",
      },
      timeout: 30000,
      withCredentials: true,
    });

    const appendCookies = (setCookie: any) => {
      if (setCookie && Array.isArray(setCookie)) {
        const newCookies = setCookie.map((c: string) => c.split(";")[0]).join("; ");
        this.cookieJar = this.cookieJar ? `${this.cookieJar}; ${newCookies}` : newCookies;
      }
    };

    // حفظ وتحديث الكوكيز
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        appendCookies(response.headers["set-cookie"]);
        return response;
      },
      (error: any) => {
        appendCookies(error?.response?.headers?.["set-cookie"]);
        return Promise.reject(error);
      }
    );

    // إرفاق الكوكيز مع كل طلب
    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (this.cookieJar && config.headers) {
        config.headers.set("Cookie", this.cookieJar);
      }
      return config;
    });
  }

  /**
   * تسجيل الدخول في المنصة
   */
  public async signIn(): Promise<boolean> {
    try {
      console.log(`[BOT-API] Attempting agent sign in to: ${this.baseUrl}/global/api/User/signIn`);

      const response = await this.client.post<ApiResponse<{ type: number; message: string }>>(
        "/global/api/User/signIn",
        {
          username: this.username,
          password: this.password,
        }
      );

      console.log(`[BOT-API] SignIn Response Status:`, response.status, `Data:`, JSON.stringify(response.data));

      if (response.data && (response.data.status || response.data.result)) {
        this.isSignedIn = true;
        console.log(`[BOT-API] Signed in successfully!`);
        return true;
      }

      const notif = response.data?.notification?.[0]?.content;
      throw new Error(notif || "فشل التحقق من بيانات تسجيل الدخول في السيرفر");
    } catch (error: any) {
      const resp = error?.response;
      console.error(
        `[BOT-API] SignIn Error: HTTP ${resp?.status || "NO_RESPONSE"} |`,
        resp?.data ? JSON.stringify(resp.data) : error.message
      );

      try {
        const altResp = await this.client.post("/global/api/UserApi/signIn", {
          username: this.username,
          password: this.password,
        });
        if (altResp.data?.status) {
          this.isSignedIn = true;
          return true;
        }
      } catch (_) {}

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
  private async postAuth<T = any>(endpoint: string, body: any, isRetry = false): Promise<ApiResponse<T>> {
    if (!this.isSignedIn && !this.cookieJar) {
      await this.signIn();
    }

    try {
      console.log(`[BOT-API] Sending POST to: ${this.baseUrl}${endpoint}`);
      const res = await this.client.post<ApiResponse<T>>(endpoint, body);
      console.log(`[BOT-API] POST ${endpoint} Response:`, JSON.stringify(res.data));
      return res.data;
    } catch (error: any) {
      const status = error?.response?.status;
      console.error(`[BOT-API] POST ${endpoint} Error HTTP ${status}:`, error?.response?.data || error.message);

      if ((status === 403 || status === 401) && !isRetry) {
        console.warn(`[BOT-API] Re-authenticating agent session and retrying ${endpoint}...`);
        this.isSignedIn = false;
        await this.signIn();
        return this.postAuth<T>(endpoint, body, true);
      }
      throw error;
    }
  }

  /**
   * 1. إنشاء حساب جديد للاعب
   */
  public async registerPlayer(params: {
    login: string;
    password: string;
    email: string;
  }): Promise<{ success: boolean; message?: string }> {
    try {
      const res = await this.postAuth("/global/api/User/registerPlayer", {
        player: {
          login: params.login,
          password: params.password,
          email: params.email,
          parentId: this.parentId,
        },
      });

      if (res && (res.status || res.result)) {
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
   * 4. إيداع رصيد
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
   * 5. سحب رصيد
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
   * 6. أرصدة محافظ الوكيل
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
