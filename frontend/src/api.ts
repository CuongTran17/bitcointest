import type { Address, Balance, Transaction, TransactionDetail, User } from "./types";

const API_BASE = "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getUsers(): Promise<User[]> {
  return request<User[]>("/users");
}

export function createUser(name: string, walletName: string): Promise<User> {
  return request<User>("/users", {
    method: "POST",
    body: JSON.stringify({ name, wallet_name: walletName })
  });
}

export function getBalance(walletName: string): Promise<Balance> {
  return request<Balance>(`/wallets/${walletName}/balance`);
}

export function createAddress(walletName: string): Promise<Address> {
  return request<Address>(`/wallets/${walletName}/address`, { method: "POST" });
}

export function sendTransaction(fromWallet: string, toAddress: string, amountBtc: string) {
  return request("/transactions/send", {
    method: "POST",
    body: JSON.stringify({ from_wallet: fromWallet, to_address: toAddress, amount_btc: amountBtc })
  });
}

export function fundFromFaucet(walletName: string, amountBtc = "10.00000000") {
  return request(`/faucet/${walletName}`, {
    method: "POST",
    body: JSON.stringify({ amount_btc: amountBtc })
  });
}

export function mineBlocks(walletName = "miner", blockCount = 1) {
  return request("/mine", {
    method: "POST",
    body: JSON.stringify({ wallet_name: walletName, block_count: blockCount })
  });
}

export function getTransactions(walletName: string): Promise<Transaction[]> {
  return request<Transaction[]>(`/transactions/${walletName}`);
}

export function getTransactionDetail(txid: string): Promise<TransactionDetail> {
  return request<TransactionDetail>(`/transactions/detail/${txid}`);
}
