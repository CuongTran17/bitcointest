import { useState } from "react";

type Props = {
  onSend: (address: string, amountBtc: string) => void;
};

export function SendPanel({ onSend }: Props) {
  const [address, setAddress] = useState("");
  const [amount, setAmount] = useState("1.00000000");

  return (
    <section className="panel">
      <h3>Send</h3>
      <input value={address} onChange={(event) => setAddress(event.target.value)} placeholder="bcrt1..." />
      <input
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
        type="number"
        min="0.00000001"
        step="0.00000001"
      />
      <button onClick={() => onSend(address, amount)}>Send BTC</button>
    </section>
  );
}
