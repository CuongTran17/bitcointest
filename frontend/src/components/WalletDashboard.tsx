import type { Balance } from "../types";

type Props = {
  walletName: string;
  balance: Balance | null;
};

export function WalletDashboard({ walletName, balance }: Props) {
  return (
    <section className="panel balance-panel">
      <p className="label">Wallet</p>
      <h2>{walletName}</h2>
      <p className="balance">{balance ? balance.confirmed_balance_btc : "0.00000000"} confirmed BTC</p>
      <p className="pending">{balance ? balance.unconfirmed_balance_btc : "0.00000000"} pending BTC</p>
      <p className="muted">{balance ? balance.total_balance_btc : "0.00000000"} total BTC</p>
    </section>
  );
}
