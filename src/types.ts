export interface UserState {
  telegramId: number;
  first_name?: string;
  username?: string;
  texasPlayerId?: string;
  texasUsername?: string;
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
