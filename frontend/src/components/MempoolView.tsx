import type { MempoolSummary } from "../types";

type Props = {
  summary: MempoolSummary | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
};

function shortTxid(txid: string) {
  if (txid.length <= 14) {
    return txid;
  }
  return `${txid.slice(0, 8)}...${txid.slice(-6)}`;
}

function walletLabel(walletName: string | null) {
  if (!walletName) {
    return "Unknown";
  }
  return walletName.charAt(0).toUpperCase() + walletName.slice(1);
}

function formatTime(value: number | null) {
  if (!value) {
    return "Not available";
  }
  return new Date(value * 1000).toLocaleString();
}

export function MempoolView({ summary, loading, error, onRefresh }: Props) {
  return (
    <section className="panel mempool-view">
      <div className="detail-header">
        <div>
          <p className="label">Node mempool</p>
          <h3>Mempool View</h3>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {summary && (
        <div className="mempool-summary">
          <div>
            <span className="label">Transactions</span>
            <p><strong>{summary.transaction_count}</strong></p>
          </div>
          <div>
            <span className="label">Total vsize</span>
            <p><strong>{summary.total_vsize} vB</strong></p>
          </div>
          <div>
            <span className="label">Total Fee (BTC)</span>
            <p><strong>{summary.total_fee_btc} BTC</strong></p>
          </div>
          <div>
            <span className="label">Total Fee (Sats)</span>
            <p><strong>{summary.total_fee_sats} sats</strong></p>
          </div>
        </div>
      )}

      {loading && <p>Loading mempool transactions...</p>}
      {!loading && error && <p className="error">{error}</p>}
      {!loading && !error && summary && summary.transactions.length === 0 && (
        <p>No pending transactions in mempool.</p>
      )}
      {!loading && !error && summary && summary.transactions.length > 0 && (
        <div className="mempool-table-wrap">
          <table className="mempool-table">
            <thead>
              <tr>
                <th>Txid</th>
                <th>Transfer</th>
                <th>Fee</th>
                <th>Fee Rate</th>
                <th>Size</th>
                <th>Time</th>
                <th>Dependencies</th>
                <th>RBF</th>
              </tr>
            </thead>
            <tbody>
              {summary.transactions.map((tx) => (
                <tr key={tx.txid}>
                  <td className="mempool-txid" title={tx.txid}>
                    <code>{shortTxid(tx.txid)}</code>
                  </td>
                  <td>
                    <strong>
                      {walletLabel(tx.from_wallet)} -&gt; {walletLabel(tx.to_wallet)}
                    </strong>
                    {tx.to_address && (
                      <div className="mempool-address">
                        <small className="muted"><code>{tx.to_address}</code></small>
                      </div>
                    )}
                  </td>
                  <td>
                    <strong>{tx.fee_btc} BTC</strong>
                    <br />
                    <small className="muted">{tx.fee_sats} sats</small>
                  </td>
                  <td>
                    {tx.fee_rate_sat_vb ? `${tx.fee_rate_sat_vb} sat/vB` : "Not available"}
                  </td>
                  <td>
                    {tx.vsize} vB
                    <br />
                    <small className="muted">wt {tx.weight}</small>
                  </td>
                  <td>
                    <small>{formatTime(tx.time)}</small>
                  </td>
                  <td>
                    <small>
                      Ancestors: {tx.ancestor_count}
                      <br />
                      Descendants: {tx.descendant_count}
                    </small>
                  </td>
                  <td>
                    <small className="muted">{tx.replaceable ? "RBF" : "No RBF"}</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
