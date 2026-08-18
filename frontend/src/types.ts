export type User = {
  id: number;
  name: string;
  wallet_name: string;
};

export type Balance = {
  wallet_name: string;
  confirmed_balance_btc: string;
  unconfirmed_balance_btc: string;
  total_balance_btc: string;
  confirmed_balance_sats: number;
  unconfirmed_balance_sats: number;
  total_balance_sats: number;
};

export type Address = {
  wallet_name: string;
  address: string;
};

export type Transaction = {
  txid: string;
  category: string;
  amount_btc: string;
  amount_sats: number;
  confirmations: number;
  status: "pending" | "confirmed";
  time: number | null;
  blockhash: string | null;
  address: string | null;
};
