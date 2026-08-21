import type { Transaction } from "../types";

type Props = {
  transactions: Transaction[];
  selectedTxid: string | null;
  onSelectTransaction: (txid: string) => void;
};

function walletLabel(walletName: string | null) {
  if (!walletName) {
    return "Unknown address";
  }
  return walletName.charAt(0).toUpperCase() + walletName.slice(1);
}

function shortTxid(txid: string) {
  if (txid.length <= 16) {
    return txid;
  }
  return `${txid.slice(0, 8)}...${txid.slice(-6)}`;
}

function confirmationLabel(confirmations: number) {
  return confirmations === 1 ? "1 confirmation" : `${confirmations} confirmations`;
}

export function TransactionHistory({ transactions, selectedTxid, onSelectTransaction }: Props) {
  return (
    <section className="panel history">
      <div>
        <span className="label">Activity</span>
        <h3>Recent Transactions</h3>
      </div>
      {transactions.length === 0 ? (
        <p className="muted">No transactions found for this wallet.</p>
      ) : (
        <ul>
          {transactions.map((tx) => (
            <li
              className={`history-item ${selectedTxid === tx.txid ? "selected" : ""}`}
              key={`${tx.txid}-${tx.category}-${tx.amount_sats}`}
            >
              <button
                className="history-button"
                type="button"
                onClick={() => onSelectTransaction(tx.txid)}
                aria-pressed={selectedTxid === tx.txid}
              >
                <div className="history-main">
                  <span className="direction">
                    {walletLabel(tx.from_wallet)} -&gt; {walletLabel(tx.to_wallet)}
                  </span>
                  <small className="muted">{tx.category}</small>
                </div>
                <div style={{ textAlign: "right" }}>
                  <strong>{tx.amount_btc} BTC</strong>
                </div>
                <div className="history-meta">
                  <span className={`badge ${tx.status === "confirmed" ? "badge-confirmed" : "badge-pending"}`}>
                    {tx.status}
                  </span>
                  <small className="muted">· {confirmationLabel(tx.confirmations)}</small>
                  {tx.blockhash && <small className="muted">· block {shortTxid(tx.blockhash)}</small>}
                </div>
                <div className="txid" title={tx.txid}>
                  <small className="muted">txid: <code>{shortTxid(tx.txid)}</code></small>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
