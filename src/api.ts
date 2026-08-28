import axios, { AxiosInstance } from "axios";
import { AgentSession, ApiResponse } from "./types";

export class Texas4WinApi {
  private client: AxiosInstance;
  private session: AgentSession | null = null;
  private baseUrl: string;
  private username: string;
  private password: string;
  private parentId: string;

  constructor() {
    this.baseUrl = (process.env.API_BASE_URL || "https://agents.texas4win.com").replace(/\/$/, "");
    this.username = process.env.AGENT_USERNAME || "Bero@yahoo.com";
    this.password = process.env.AGENT_PASSWORD || "Aazzam@318";
    this.parentId = process.env.PARENT_ID || "2688288";

    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      },
      timeout: 20000,
    });
  }

  /**
   * تسجيل الدخول وجلب accessToken و refreshToken
   */
  public async signIn(): Promise<AgentSession> {
    try {
      const response = await this.client.post<ApiResponse<{ accessToken: string; refreshToken: string }>>(
        "/global/api/UserApi/signIn",
        {
          username: this.username,
          password: this.password,
        }
      );

      if (response.data && response.data.status && response.data.result?.accessToken) {
        this.session = {
          accessToken: response.data.result.accessToken,
          refreshToken: response.data.result.refreshToken,
          expiresAt: Date.now() + 50 * 60 * 1000,
        };
        return this.session;
      }

      throw new Error(response.data.notification?.[0]?.content || "فشل تسجيل دخول الوكيل في المنصة");
    } catch (error: any) {
      console.error("Agent signIn error:", error?.response?.data || error.message);
      throw new Error(error?.response?.data?.notification?.[0]?.content || "تعذر الاتصال بسيرفر الوكالة (Sign In)");
    }
  }

  /**
   * تجديد التوكن التلقائي (Token Rotation)
   */
  public async refreshToken(): Promise<AgentSession> {
    if (!this.session?.refreshToken) {
      return this.signIn();
    }

    try {
      const response = await this.client.post<ApiResponse<{ accessToken: string; refreshToken: string }>>(
        "/global/api/UserApi/refreshToken",
        {
          refreshToken: this.session.refreshToken,
        }
      );

      if (response.data && response.data.status && response.data.result?.accessToken) {
        this.session = {
          accessToken: response.data.result.accessToken,
          refreshToken: response.data.result.refreshToken,
          expiresAt: Date.now() + 50 * 60 * 1000,
        };
        return this.session;
      }

      return this.signIn();
    } catch (error) {
      console.warn("Refresh token expired, re-authenticating with credentials...");
      return this.signIn();
    }
  }

  private async getValidToken(): Promise<string> {
    if (!this.session || Date.now() >= this.session.expiresAt) {
      if (this.session?.refreshToken) {
        await this.refreshToken();
      } else {
        await this.signIn();
      }
    }
    return this.session!.accessToken;
  }

  private async postAuth<T = any>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    let token = await this.getValidToken();

    try {
      let res = await this.client.post<ApiResponse<T>>(endpoint, body, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.data && res.data.result === "ex") {
        console.warn("Access token invalid/expired (result=ex), rotating token...");
        await this.refreshToken();
        token = this.session!.accessToken;
        res = await this.client.post<ApiResponse<T>>(endpoint, body, {
          headers: { Authorization: `Bearer ${token}` },
        });
      }

      return res.data;
    } catch (error: any) {
      if (error?.response?.status === 401 || error?.response?.data?.result === "ex") {
        console.warn("HTTP 401 received, re-authenticating...");
        await this.signIn();
        token = this.session!.accessToken;
        const retryRes = await this.client.post<ApiResponse<T>>(endpoint, body, {
          headers: { Authorization: `Bearer ${token}` },
        });
        return retryRes.data;
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
      const res = await this.postAuth("/global/api/UserApi/registerPlayer", {
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

      const res = await this.postAuth<{ records: any[]; totalRecordsCount: string }>(
        "/global/api/UserApi/getPlayersForCurrentAgent",
        {
          start: 0,
          limit: 20,
          filter,
          isNextPage: false,
        }
      );

      if (res.status && res.result?.records && res.result.records.length > 0) {
        const record = res.result.records[0];
        return {
          playerId: String(record.playerId),
          username: record.username,
          currency: record.currency || "USD",
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
      const res = await this.postAuth<Array<{ balance: number; currencyCode: string; main: boolean }>>(
        "/global/api/UserApi/getPlayerBalanceById",
        {
          playerId: String(playerId),
        }
      );

      if (res.status && Array.isArray(res.result) && res.result.length > 0) {
        const mainWallet = res.result.find((w) => w.main) || res.result[0];
        return {
          balance: Number(mainWallet.balance) || 0,
          currencyCode: mainWallet.currencyCode || "USD",
        };
      }

      return null;
    } catch (error: any) {
      console.error("getPlayerBalance error:", error?.response?.data || error.message);
      return null;
    }
  }

  /**
   * 4. إيداع رصيد للاعب
   */
  public async depositToPlayer(params: {
    playerId: string;
    amount: number;
    currencyCode?: string;
    comment?: string;
  }): Promise<{
    success: boolean;
    balance?: number;
    message?: string;
  }> {
    try {
      const currency = params.currencyCode || process.env.DEFAULT_CURRENCY || "USD";
      const res = await this.postAuth<{ balance: number; currencyCode: string }>(
        "/global/api/UserApi/depositToPlayer",
        {
          amount: Math.abs(params.amount),
          comment: params.comment || "Deposit via Telegram Bot",
          playerId: String(params.playerId),
          currencyCode: currency,
          currency: currency,
          moneyStatus: 3,
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
   * 5. سحب رصيد من اللاعب
   */
  public async withdrawFromPlayer(params: {
    playerId: string;
    amount: number;
    currencyCode?: string;
    comment?: string;
  }): Promise<{
    success: boolean;
    balance?: number;
    message?: string;
  }> {
    try {
      const currency = params.currencyCode || process.env.DEFAULT_CURRENCY || "USD";
      const negativeAmount = -Math.abs(params.amount);

      const res = await this.postAuth<{ balance: number; currencyCode: string }>(
        "/global/api/UserApi/withdrawFromPlayer",
        {
          amount: negativeAmount,
          comment: params.comment || "Withdrawal via Telegram Bot",
          playerId: String(params.playerId),
          currencyCode: currency,
          currency: currency,
          moneyStatus: 3,
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
   * 6. جلب أرصدة خزينة ومحافظ الوكيل
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
      const res = await this.postAuth<any[]>("/global/api/UserApi/getAgentAllWallets", {});
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
