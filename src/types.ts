export interface AgentSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

export interface PlayerAccount {
  telegramId: number;
  telegramUsername?: string;
  fullName?: string;
  playerId: string;
  login: string;
  email: string;
  currency: string;
  createdAt: string;
}

export interface DepositRequest {
  id: string;
  telegramId: number;
  telegramUsername?: string;
  playerId: string;
  amount: number;
  method: "syriatel" | "sham";
  referenceNumber?: string;
  photoFileId?: string;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
  processedAt?: string;
  processedBy?: string;
  rejectReason?: string;
}

export interface WithdrawRequest {
  id: string;
  telegramId: number;
  telegramUsername?: string;
  playerId: string;
  amount: number;
  method: "syriatel" | "sham";
  accountDetails: string;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
  processedAt?: string;
  processedBy?: string;
  rejectReason?: string;
}

export interface ApiResponse<T = any> {
  status: boolean;
  html: string;
  result: T;
  notification: Array<{
    code: number;
    content: string;
    title: string;
    autoHideAfter: number;
    status: string;
  }>;
}
