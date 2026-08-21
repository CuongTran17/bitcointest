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
        <h3>Transaction detail</h3>
        <p className="muted">Loading transaction detail...</p>
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
          <p className="label">Transaction detail</p>
          <h3>
            {walletLabel(detail.from_wallet)} -&gt; {walletLabel(detail.to_wallet)}
          </h3>
        </div>
        <strong>{detail.amount_btc ?? "Unknown"} BTC</strong>
      </div>

      <dl className="detail-grid">
        <div>
          <dt>Status</dt>
          <dd>{detail.status} · {detail.confirmations} confirmations</dd>
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
          <dd>{detail.size ?? "?"} bytes · vsize {detail.vsize ?? "?"} · weight {detail.weight ?? "?"}</dd>
        </div>
        <div>
          <dt>Txid</dt>
          <dd title={detail.txid}>{shortHash(detail.txid)}</dd>
        </div>
      </dl>

      <div className="detail-columns">
        <div>
          <h4>Inputs</h4>
          <ul className="detail-list">
            {detail.inputs.map((input, index) => (
              <li key={`${input.txid ?? input.coinbase ?? "input"}-${index}`}>
                {input.coinbase ? (
                  <span>coinbase</span>
                ) : (
                  <span title={input.txid ?? undefined}>{shortHash(input.txid)}:{input.vout ?? "?"}</span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4>Outputs</h4>
          <ul className="detail-list">
            {detail.outputs.map((output) => (
              <li key={output.n}>
                <strong>{output.value_btc} BTC</strong>
                <span>{walletLabel(output.wallet_name)}</span>
                <code>{output.address ?? "No address"}</code>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <details>
        <summary>Raw JSON</summary>
        <pre>{JSON.stringify(detail.raw, null, 2)}</pre>
      </details>
    </section>
  );
}
