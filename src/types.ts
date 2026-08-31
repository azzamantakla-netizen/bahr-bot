export interface UserState {
  telegramId: number;
  first_name?: string;
  username?: string;
  texasPlayerId?: string;
  texasUsername?: string;
}

export interface PlayerAccount {
  telegramId: number;
  login: string;
  playerId: string;
  createdAt: string;
}

export interface DepositRequest {
  id: string;
  telegramId: number;
  playerId: string;
  amount: number;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
}

export interface WithdrawRequest {
  id: string;
  telegramId: number;
  playerId: string;
  amount: number;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
}

export interface ApiResponse<T = any> {
  status: boolean;
  html?: string;
  result?: T;
  notification?: Array<{
    type?: number;
    title?: string;
    content: string;
  }>;
}
