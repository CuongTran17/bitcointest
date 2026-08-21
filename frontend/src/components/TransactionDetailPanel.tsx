import type { TransactionDetail } from "../types";

type Props = {
  detail: TransactionDetail | null;
  loading: boolean;
};

function walletLabel(walletName: string | null) {
  if (!walletName) {
    return "Unknown address";
  }
  return walletName.charAt(0).toUpperCase() + walletName.slice(1);
}

function shortHash(value: string | null) {
  if (!value) {
    return "Not available";
  }
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 10)}...${value.slice(-8)}`;
}

function formatTime(value: number | null) {
  if (!value) {
    return "Not available";
  }
  return new Date(value * 1000).toLocaleString();
}

export function TransactionDetailPanel({ detail, loading }: Props) {
  if (loading) {
    return (
      <section className="panel transaction-detail">
        <div>
          <span className="label">Transaction Detail</span>
          <h3>Loading...</h3>
        </div>
        <p className="muted">Fetching raw transaction data from Bitcoin Core...</p>
      </section>
    );
  }

  if (!detail) {
    return null;
  }

  return (
    <section className="panel transaction-detail">
      <div className="detail-header">
        <div>
          <span className="label">Transaction Detail</span>
          <h3>
            {walletLabel(detail.from_wallet)} -&gt; {walletLabel(detail.to_wallet)}
          </h3>
        </div>
        <div>
          <strong style={{ fontSize: "18px" }}>{detail.amount_btc ?? "Unknown"} BTC</strong>
        </div>
      </div>

      <dl className="detail-grid">
        <div>
          <dt>Status</dt>
          <dd>
            <span className={`badge ${detail.status === "confirmed" ? "badge-confirmed" : "badge-pending"}`}>
              {detail.status}
            </span>{" "}
            ({detail.confirmations} conf)
          </dd>
        </div>
        <div>
          <dt>Block</dt>
          <dd title={detail.blockhash ?? undefined}>{shortHash(detail.blockhash)}</dd>
        </div>
        <div>
          <dt>Time</dt>
          <dd>{formatTime(detail.blocktime ?? detail.time)}</dd>
        </div>
        <div>
          <dt>Fee</dt>
          <dd>{detail.fee_btc ? `${detail.fee_btc} BTC` : "Not available"}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{detail.size ?? "?"} B · vsize {detail.vsize ?? "?"} · weight {detail.weight ?? "?"}</dd>
        </div>
        <div>
          <dt>Txid</dt>
          <dd title={detail.txid}><code>{shortHash(detail.txid)}</code></dd>
        </div>
      </dl>

      <div className="detail-columns">
        <div>
          <h4>Inputs ({detail.inputs.length})</h4>
          <ul className="detail-list">
            {detail.inputs.map((input, index) => (
              <li key={`${input.txid ?? input.coinbase ?? "input"}-${index}`}>
                {input.coinbase ? (
                  <span><strong>coinbase</strong></span>
                ) : (
                  <span title={input.txid ?? undefined}>
                    <code>{shortHash(input.txid)}:{input.vout ?? "?"}</code>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4>Outputs ({detail.outputs.length})</h4>
          <ul className="detail-list">
            {detail.outputs.map((output) => (
              <li key={output.n}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong>{output.value_btc} BTC</strong>
                  <small className="muted">{walletLabel(output.wallet_name)}</small>
                </div>
                <code>{output.address ?? "No address"}</code>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <details>
        <summary>View Raw JSON</summary>
        <pre>{JSON.stringify(detail.raw, null, 2)}</pre>
      </details>
    </section>
  );
}
