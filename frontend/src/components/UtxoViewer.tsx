import type { UtxoSummary } from "../types";

type Props = {
  walletName: string;
  summary: UtxoSummary | null;
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

function walletLabel(walletName: string) {
  if (!walletName) {
    return "";
  }
  return walletName.charAt(0).toUpperCase() + walletName.slice(1);
}

export function UtxoViewer({ walletName, summary, loading, error, onRefresh }: Props) {
  return (
    <section className="panel utxo-viewer">
      <div className="detail-header">
        <div>
          <p className="label">Unspent outputs</p>
          <h3>UTXO Viewer ({walletLabel(walletName)})</h3>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {summary && (
        <div className="utxo-summary">
          <div>
            <span className="label">Total UTXOs</span>
            <p><strong>{summary.utxo_count}</strong></p>
          </div>
          <div>
            <span className="label">Confirmed</span>
            <p><strong>{summary.confirmed_count}</strong></p>
          </div>
          <div>
            <span className="label">Unconfirmed</span>
            <p><strong>{summary.unconfirmed_count}</strong></p>
          </div>
          <div>
            <span className="label">Total Amount</span>
            <p><strong>{summary.total_amount_btc} BTC</strong> ({summary.total_amount_sats} sats)</p>
          </div>
        </div>
      )}

      {loading && <p>Loading UTXOs...</p>}
      {!loading && error && <p className="error">{error}</p>}
      {!loading && !error && summary && summary.utxos.length === 0 && <p>No unspent outputs.</p>}
      {!loading && !error && summary && summary.utxos.length > 0 && (
        <div className="utxo-table-wrap">
          <table className="utxo-table">
            <thead>
              <tr>
                <th>Txid:Vout</th>
                <th>Address</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Spendable</th>
              </tr>
            </thead>
            <tbody>
              {summary.utxos.map((utxo) => (
                <tr key={`${utxo.txid}-${utxo.vout}`}>
                  <td className="utxo-txid" title={`${utxo.txid}:${utxo.vout}`}>
                    <code>{shortTxid(utxo.txid)}:{utxo.vout}</code>
                  </td>
                  <td className="utxo-address">
                    {utxo.address ? <code>{utxo.address}</code> : <span className="muted">No address</span>}
                  </td>
                  <td>
                    <strong>{utxo.amount_btc} BTC</strong>
                    <br />
                    <small className="muted">{utxo.amount_sats} sats</small>
                  </td>
                  <td>
                    <span className={utxo.confirmations > 0 ? "confirmed" : "pending"}>
                      {utxo.confirmations > 0 ? "confirmed" : "pending"}
                    </span>{" "}
                    ({utxo.confirmations} conf)
                  </td>
                  <td>
                    {utxo.spendable ? "spendable" : <span className="muted">watch-only</span>}
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
