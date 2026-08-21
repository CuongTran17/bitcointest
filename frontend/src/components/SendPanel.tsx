import { useState } from "react";

type Props = {
  onSend: (address: string, amountBtc: string) => void;
};

export function SendPanel({ onSend }: Props) {
  const [address, setAddress] = useState("");
  const [amount, setAmount] = useState("1.00000000");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (address.trim() && amount.trim()) {
      onSend(address.trim(), amount.trim());
    }
  }

  return (
    <section className="panel send-panel">
      <div>
        <span className="label">Outbound</span>
        <h3>Send</h3>
      </div>
      <form className="action-form" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="send-to-address" className="label">Recipient Address</label>
          <input
            id="send-to-address"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder="bcrt1..."
            required
          />
        </div>
        <div>
          <label htmlFor="send-amount-btc" className="label">Amount (BTC)</label>
          <input
            id="send-amount-btc"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            type="number"
            min="0.00000001"
            step="0.00000001"
            required
          />
        </div>
        <button type="submit" disabled={!address.trim() || !amount.trim()}>
          Send BTC
        </button>
      </form>
    </section>
  );
}
