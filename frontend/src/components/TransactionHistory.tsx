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
      <h3>Recent transactions</h3>
      <ul>
        {transactions.map((tx) => (
          <li
            className={`history-item ${tx.status} ${selectedTxid === tx.txid ? "selected" : ""}`}
            key={`${tx.txid}-${tx.category}-${tx.amount_sats}`}
          >
            <button className="history-button" type="button" onClick={() => onSelectTransaction(tx.txid)}>
              <div className="history-main">
                <span className="direction">
                  {walletLabel(tx.from_wallet)} -&gt; {walletLabel(tx.to_wallet)}
                </span>
                <small>{tx.category}</small>
              </div>
              <strong>{tx.amount_btc} BTC</strong>
              <small className="history-meta">
                {tx.status} · {confirmationLabel(tx.confirmations)}
                {tx.blockhash ? ` · block ${shortTxid(tx.blockhash)}` : ""}
              </small>
              <small className="txid" title={tx.txid}>
                txid: {shortTxid(tx.txid)}
              </small>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
