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
  from_wallet: string | null;
  to_wallet: string | null;
  category: string;
  amount_btc: string;
  amount_sats: number;
  confirmations: number;
  status: "pending" | "confirmed";
  time: number | null;
  blockhash: string | null;
  address: string | null;
};

export type TransactionInput = {
  txid: string | null;
  vout: number | null;
  coinbase: string | null;
  sequence: number | null;
};

export type TransactionOutput = {
  n: number;
  value_btc: string;
  value_sats: number;
  address: string | null;
  wallet_name: string | null;
  script_type: string | null;
};

export type TransactionDetail = {
  txid: string;
  from_wallet: string | null;
  to_wallet: string | null;
  to_address: string | null;
  amount_btc: string | null;
  amount_sats: number | null;
  confirmations: number;
  status: "pending" | "confirmed";
  blockhash: string | null;
  blocktime: number | null;
  time: number | null;
  size: number | null;
  vsize: number | null;
  weight: number | null;
  fee_btc: string | null;
  fee_sats: number | null;
  inputs: TransactionInput[];
  outputs: TransactionOutput[];
  raw: Record<string, unknown>;
};
