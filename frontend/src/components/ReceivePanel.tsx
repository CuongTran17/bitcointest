type Props = {
  address: string;
  onCreateAddress: () => void;
};

export function ReceivePanel({ address, onCreateAddress }: Props) {
  return (
    <section className="panel">
      <h3>Receive</h3>
      <button onClick={onCreateAddress}>New address</button>
      {address && <code>{address}</code>}
    </section>
  );
}
