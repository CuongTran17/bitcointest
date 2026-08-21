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

export type Utxo = {
  txid: string;
  vout: number;
  address: string | null;
  amount_btc: string;
  amount_sats: number;
  confirmations: number;
  spendable: boolean;
  solvable: boolean;
  safe: boolean;
};

export type UtxoSummary = {
  wallet_name: string;
  utxo_count: number;
  confirmed_count: number;
  unconfirmed_count: number;
  total_amount_btc: string;
  total_amount_sats: number;
  utxos: Utxo[];
};

export type MempoolTransaction = {
  txid: string;
  wtxid: string | null;
  vsize: number;
  weight: number;
  fee_btc: string;
  fee_sats: number;
  fee_rate_sat_vb: string | null;
  time: number | null;
  entry_height: number | null;
  confirmations: number;
  from_wallet: string | null;
  to_wallet: string | null;
  to_address: string | null;
  status: "pending";
  ancestor_count: number;
  descendant_count: number;
  depends: string[];
  spent_by: string[];
  replaceable: boolean;
  unbroadcast: boolean;
  output_addresses: string[];
};

export type MempoolSummary = {
  transaction_count: number;
  total_vsize: number;
  total_fee_btc: string;
  total_fee_sats: number;
  transactions: MempoolTransaction[];
};
