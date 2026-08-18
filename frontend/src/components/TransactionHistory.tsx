import type { Transaction } from "../types";

type Props = {
  transactions: Transaction[];
};

export function TransactionHistory({ transactions }: Props) {
  return (
    <section className="panel history">
      <h3>Recent transactions</h3>
      <ul>
        {transactions.map((tx) => (
          <li key={`${tx.txid}-${tx.category}-${tx.amount_sats}`}>
            <span>{tx.category}</span>
            <strong>{tx.amount_btc} BTC</strong>
            <small>
              {tx.status} - {tx.confirmations} confirmations
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
}
