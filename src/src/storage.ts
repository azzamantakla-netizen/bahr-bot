import fs from "fs";
import path from "path";
import { PlayerAccount, DepositRequest, WithdrawRequest } from "./types";

const DATA_DIR = path.join(process.cwd(), "data");

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const PLAYERS_FILE = path.join(DATA_DIR, "players.json");
const DEPOSITS_FILE = path.join(DATA_DIR, "deposits.json");
const WITHDRAWS_FILE = path.join(DATA_DIR, "withdraws.json");
const CONFIG_FILE = path.join(DATA_DIR, "config.json");

interface DynamicConfig {
  shamCashWallet: string;
  syriatelCashCode: string;
  minDeposit: number;
  minWithdraw: number;
  supportUsername: string;
  channelLink: string;
}

const DEFAULT_CONFIG: DynamicConfig = {
  shamCashWallet: process.env.SHAM_CASH_WALLET || "a18758d5324eb7595d4463ca355ad221",
  syriatelCashCode: process.env.SYRIATEL_CASH_CODE || "48122120",
  minDeposit: 10000,
  minWithdraw: 20000,
  supportUsername: "AzzamAntakla",
  channelLink: "https://t.me/texas4win",
};

class Storage {
  private players: Map<number, PlayerAccount> = new Map();
  private deposits: Map<string, DepositRequest> = new Map();
  private withdraws: Map<string, WithdrawRequest> = new Map();
  private config: DynamicConfig = { ...DEFAULT_CONFIG };

  constructor() {
    this.load();
  }

  private load() {
    try {
      if (fs.existsSync(PLAYERS_FILE)) {
        const raw = fs.readFileSync(PLAYERS_FILE, "utf-8");
        const list: PlayerAccount[] = JSON.parse(raw);
        list.forEach((p) => this.players.set(p.telegramId, p));
      }
      if (fs.existsSync(DEPOSITS_FILE)) {
        const raw = fs.readFileSync(DEPOSITS_FILE, "utf-8");
        const list: DepositRequest[] = JSON.parse(raw);
        list.forEach((d) => this.deposits.set(d.id, d));
      }
      if (fs.existsSync(WITHDRAWS_FILE)) {
        const raw = fs.readFileSync(WITHDRAWS_FILE, "utf-8");
        const list: WithdrawRequest[] = JSON.parse(raw);
        list.forEach((w) => this.withdraws.set(w.id, w));
      }
      if (fs.existsSync(CONFIG_FILE)) {
        const raw = fs.readFileSync(CONFIG_FILE, "utf-8");
        this.config = { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
      }
    } catch (e) {
      console.error("Error loading storage:", e);
    }
  }

  private savePlayers() {
    try {
      const arr = Array.from(this.players.values());
      fs.writeFileSync(PLAYERS_FILE, JSON.stringify(arr, null, 2));
    } catch (e) {
      console.error("Error saving players:", e);
    }
  }

  private saveDeposits() {
    try {
      const arr = Array.from(this.deposits.values());
      fs.writeFileSync(DEPOSITS_FILE, JSON.stringify(arr, null, 2));
    } catch (e) {
      console.error("Error saving deposits:", e);
    }
  }

  private saveWithdraws() {
    try {
      const arr = Array.from(this.withdraws.values());
      fs.writeFileSync(WITHDRAWS_FILE, JSON.stringify(arr, null, 2));
    } catch (e) {
      console.error("Error saving withdraws:", e);
    }
  }

  public saveConfig(cfg: Partial<DynamicConfig>) {
    this.config = { ...this.config, ...cfg };
    try {
      fs.writeFileSync(CONFIG_FILE, JSON.stringify(this.config, null, 2));
    } catch (e) {
      console.error("Error saving config:", e);
    }
  }

  public getConfig(): DynamicConfig {
    return this.config;
  }

  public getPlayerByTelegramId(telegramId: number): PlayerAccount | undefined {
    return this.players.get(telegramId);
  }

  public savePlayer(player: PlayerAccount): void {
    this.players.set(player.telegramId, player);
    this.savePlayers();
  }

  public getAllPlayers(): PlayerAccount[] {
    return Array.from(this.players.values());
  }

  public saveDeposit(deposit: DepositRequest): void {
    this.deposits.set(deposit.id, deposit);
    this.saveDeposits();
  }

  public getDeposit(id: string): DepositRequest | undefined {
    return this.deposits.get(id);
  }

  public saveWithdraw(withdraw: WithdrawRequest): void {
    this.withdraws.set(withdraw.id, withdraw);
    this.saveWithdraws();
  }

  public getWithdraw(id: string): WithdrawRequest | undefined {
    return this.withdraws.get(id);
  }
}

export const storage = new Storage();
