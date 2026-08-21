type Props = {
  address: string;
  onCreateAddress: () => void;
};

export function ReceivePanel({ address, onCreateAddress }: Props) {
  return (
    <section className="panel receive-panel">
      <div>
        <span className="label">Inbound</span>
        <h3>Receive</h3>
      </div>
      <div className="action-form">
        <button type="button" className="btn-secondary" onClick={onCreateAddress}>
          Generate Address
        </button>
        {address && (
          <div className="address-result">
            <span className="label">Generated Address:</span>
            <div style={{ marginTop: "4px" }}>
              <code>{address}</code>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
