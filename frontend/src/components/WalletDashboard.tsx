import type { Balance } from "../types";

type Props = {
  walletName: string;
  balance: Balance | null;
};

export function WalletDashboard({ walletName, balance }: Props) {
  const capitalized = walletName ? walletName.charAt(0).toUpperCase() + walletName.slice(1) : "";
  return (
    <section className="panel balance-panel">
      <div className="balance-header">
        <div>
          <span className="label">Active Account</span>
          <h2>{capitalized}</h2>
        </div>
      </div>

      <div className="balance-stats-grid">
        <div className="stat-item">
          <span className="label">Confirmed Balance</span>
          <p className="balance-value-main">
            {balance ? balance.confirmed_balance_btc : "0.00000000"} <small style={{ fontSize: "16px", fontWeight: "600" }}>BTC</small>
          </p>
        </div>
        <div className="stat-item">
          <span className="label">Pending</span>
          <p className="balance-value-pending">
            {balance ? balance.unconfirmed_balance_btc : "0.00000000"} <small style={{ fontSize: "14px", fontWeight: "600" }}>BTC</small>
          </p>
        </div>
        <div className="stat-item">
          <span className="label">Total</span>
          <p className="balance-value-sub">
            {balance ? balance.total_balance_btc : "0.00000000"} <small style={{ fontSize: "14px", fontWeight: "600" }}>BTC</small>
          </p>
        </div>
      </div>
    </section>
  );
}
