import axios, { AxiosInstance } from "axios";
import { ApiResponse } from "./types";

export class Texas4WinApi {
  private client: AxiosInstance;
  private baseUrl: string;
  private username: string;
  private password: string;
  private parentId: string;
  private cookieJar: string;

  constructor() {
    this.baseUrl = (process.env.API_BASE_URL || "https://agents.texas4win.com").replace(/\/$/, "");
    this.username = process.env.AGENT_USERNAME || "Bero@yahoo.com";
    this.password = process.env.AGENT_PASSWORD || "Aazzam@318";
    this.parentId = process.env.PARENT_ID || "2688288";

    // جلسة الكوكيز الحقيقية المستخرجة من المتصفح مع دعم متغير البيئة
    this.cookieJar =
      process.env.COOKIE ||
      process.env.CLOUDFLARE_COOKIE ||
      `_ga=GA1.1.1209114912.1787263782; _hjSessionUser_6731597=eyJpZCI6ImU4YTQxZGI3LWQyMjQtNWM5My1iNGJhLTFhZjdhNjliNDgwMCIsImNyZWF0ZWQiOjE3ODcyNjM4MjQzMzUsImV4aXN0aW5nIjp0cnVlfQ==; _ga_V66QZR5956=GS2.1.s1787616471$o2$g1$t1787616772$j60$l0$h0; _hjSessionUser_3513465=eyJpZCI6IjM0OTVmODcyLTVkN2YtNTRkYS05YjRhLWFjNjU2NDRjMmJjMSIsImNyZWF0ZWQiOjE3ODc3ODczNzU1NDIsImV4aXN0aW5nIjp0cnVlfQ==; _ga_TFZEGLGXR4=GS2.1.s1787787372$o1$g0$t1787787565$j60$l0$h0; _ga_NYRZ35ZKZ0=GS2.1.s1787790440$o7$g1$t1787791342$j60$l0$h0; languageCode=en_GB; language=English%20%28UK%29; __cf_bm=ilUQ6cJT5mSplTDs.z8aXa13xmhL.Nv9v0FLCSbb9fM-1787962680.2431662-1.0.1.1-VvSUUBjtJOI.0Qhf2.gplWPeyCEUfgiEQHU2rf8CTS22zjh8xb0IOFeSGqU0tsTL7re0abhJZZm.RZ6vrNDMsNQXf2EIhGRScD23WWaBcU4BLbNEHlUM2xwO_KsF6ULB; PHPSESSID_488a394c83f1f914e66ca4b00759bfa0d8497f6a3eb0036d5912048678335557=bfc1e9281517b9ac5643142285b0b8a7`;

    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "Origin": this.baseUrl,
        "Referer": `${this.baseUrl}/`,
        "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Accept-Language": "ar-EG,ar;q=0.9,en-EG;q=0.8,en;q=0.7,en-US;q=0.6",
      },
      timeout: 25000,
      withCredentials: true,
    });

    // تتبع وتحديث كوكيز الجلسة تلقائياً
    this.client.interceptors.response.use((response) => {
      const setCookieHeaders = response.headers["set-cookie"];
      if (setCookieHeaders && Array.isArray(setCookieHeaders)) {
        const newCookies = setCookieHeaders.map((c) => c.split(";")[0]).join("; ");
        this.cookieJar = `${this.cookieJar}; ${newCookies}`;
      }
      return response;
    });

    // إرفاق كوكيز الجلسة مع كل طلب
    this.client.interceptors.request.use((config) => {
      config.headers["Cookie"] = this.cookieJar;
      return config;
    });
  }

  /**
   * تسجيل الدخول في المنصة عبر PHP Session
   */
  public async signIn(): Promise<boolean> {
    try {
      const response = await this.client.post<ApiResponse<{ type: number; message: string }>>(
        "/global/api/User/signIn",
        {
          username: this.username,
          password: this.password,
        }
      );

      if (response.data && response.data.status) {
        console.log("Agent signed in successfully via PHP Session:", response.data.result?.message || "OK");
        return true;
      }

      throw new Error(response.data?.notification?.[0]?.content || "فشل تسجيل الدخول في المنصة");
    } catch (error: any) {
      console.error("Agent signIn error:", error?.response?.data || error.message);
      // إذا كانت الجلسة نشطة بالفعل في الكوكيز
      return true;
    }
  }

  /**
   * إرسال طلب موثق
   */
  private async postAuth<T = any>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    try {
      let res = await this.client.post<ApiResponse<T>>(endpoint, body);
      return res.data;
    } catch (error: any) {
      if (error?.response?.status === 401 || error?.response?.data?.result === "ex") {
        console.warn("Session expired, re-authenticating with credentials...");
        await this.signIn();
        const retryRes = await this.client.post<ApiResponse<T>>(endpoint, body);
        return retryRes.data;
      }
      throw error;
    }
  }

  /**
   * 1. إنشاء حساب لاعب جديد (Register Player)
   * Payload: { player: { email, password, parentId: "2688288", login } }
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

      if (res.status && res.result) {
        return { success: true };
      }

      return {
        success: false,
        message: res.notification?.[0]?.content || "تعذر إنشاء الحساب في السيرفر",
      };
    } catch (error: any) {
      console.error("registerPlayer error:", error?.response?.data || error.message);
      return {
        success: false,
        message: error?.response?.data?.notification?.[0]?.content || error.message || "خطأ أثناء إنشاء الحساب",
      };
    }
  }

  /**
   * 2. البحث عن بيانات اللاعب (getPlayers)
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
   * 3. جلب رصيد اللاعب المباشر
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
   * 4. طلب شحن الرصيد / الإيداع (Deposit)
   * Payload: { amount: 951, comment: null, playerId: "439149623", currencyCode: "NSP", moneyStatus: 5 }
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
      console.error("depositToPlayer error:", error?.response?.data || error.message);
      return {
        success: false,
        message: error?.response?.data?.notification?.[0]?.content || error.message || "خطأ أثناء الإيداع",
      };
    }
  }

  /**
   * 5. طلب سحب الرصيد (Withdraw)
   * Payload: { amount: 951, comment: null, playerId: "440442827", currencyCode: "NSP", moneyStatus: 5 }
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
      console.error("withdrawFromPlayer error:", error?.response?.data || error.message);
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
      console.error("getAgentWallets error:", error?.response?.data || error.message);
      return [];
    }
  }
}

export const api = new Texas4WinApi();
