import { useState } from "react";
import type { BlockDetail, BlockList } from "../types";

type Props = {
  blockList: BlockList | null;
  selectedBlock: BlockDetail | null;
  limit: number;
  loading: boolean;
  detailLoading: boolean;
  error: string;
  detailError: string;
  onLimitChange: (limit: number) => void;
  onRefresh: () => void;
  onSelectBlock: (blockRef: string) => void;
};

function shortHash(value: string | null) {
  if (!value) return "Not available";
  return value.length <= 18 ? value : `${value.slice(0, 10)}...${value.slice(-8)}`;
}

function formatTime(value: number | null) {
  return value ? new Date(value * 1000).toLocaleString() : "Not available";
}

export function BlockExplorer({
  blockList,
  selectedBlock,
  limit,
  loading,
  detailLoading,
  error,
  detailError,
  onLimitChange,
  onRefresh,
  onSelectBlock,
}: Props) {
  const [lookupInput, setLookupInput] = useState("");

  function handleLookupSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = lookupInput.trim();
    if (trimmed) {
      onSelectBlock(trimmed);
    }
  }

  return (
    <section className="panel block-explorer">
      <div className="detail-header">
        <div>
          <span className="label">Blockchain (Node-Wide)</span>
          <h3>Block Explorer</h3>
        </div>
        <button type="button" className="btn-secondary" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {blockList && (
        <div className="block-explorer-summary">
          <div className="summary-card">
            <span className="label">Chain Network</span>
            <p><strong>{blockList.chain}</strong></p>
          </div>
          <div className="summary-card">
            <span className="label">Current Tip Height</span>
            <p><strong>{blockList.tip_height}</strong></p>
          </div>
          <div className="summary-card">
            <span className="label">Tip Hash</span>
            <p title={blockList.tip_hash}><code>{shortHash(blockList.tip_hash)}</code></p>
          </div>
        </div>
      )}

      <div className="block-explorer-toolbar">
        <form className="block-lookup-form" onSubmit={handleLookupSubmit}>
          <input
            type="text"
            placeholder="Search by block height (e.g. 101) or 64-char hash..."
            value={lookupInput}
            onChange={(e) => setLookupInput(e.target.value)}
            aria-label="Block height or hash"
          />
          <button type="submit" disabled={!lookupInput.trim()}>
            Lookup
          </button>
        </form>

        <div className="block-limit-control">
          <label htmlFor="block-limit-select" className="label">Limit:</label>
          <select
            id="block-limit-select"
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {loading && <p className="muted">Loading blocks...</p>}
      {!loading && error && <p className="error">{error}</p>}
      {!loading && !error && blockList && blockList.blocks.length === 0 && (
        <p className="muted">No blocks found.</p>
      )}
      {!loading && !error && blockList && blockList.blocks.length > 0 && (
        <ul className="block-list">
          {blockList.blocks.map((block) => (
            <li key={block.hash}>
              <button
                type="button"
                className={`block-row ${selectedBlock?.hash === block.hash ? "selected" : ""}`}
                onClick={() => onSelectBlock(String(block.height))}
                aria-pressed={selectedBlock?.hash === block.hash}
              >
                <div>
                  <strong>Block #{block.height}</strong>
                  <br />
                  <small className="muted" title={block.hash}><code>{shortHash(block.hash)}</code></small>
                </div>
                <div>
                  <span>{formatTime(block.time)}</span>
                  <br />
                  <small className="muted">{block.transaction_count} txs · {block.size} bytes</small>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span className="badge badge-confirmed">{block.confirmations} conf</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {detailLoading && <p className="muted">Loading block detail...</p>}
      {!detailLoading && detailError && <p className="error">{detailError}</p>}
      {!detailLoading && !detailError && selectedBlock && (
        <div className="block-detail-section">
          <div className="detail-header">
            <div>
              <span className="label">Selected Block</span>
              <h3>Block #{selectedBlock.height}</h3>
            </div>
            <div className="block-nav-actions">
              {selectedBlock.previous_hash && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => onSelectBlock(selectedBlock.previous_hash!)}
                  title={selectedBlock.previous_hash}
                >
                  &larr; Prev Block
                </button>
              )}
              {selectedBlock.next_hash && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => onSelectBlock(selectedBlock.next_hash!)}
                  title={selectedBlock.next_hash}
                >
                  Next Block &rarr;
                </button>
              )}
            </div>
          </div>

          <dl className="block-detail-grid">
            <div>
              <dt>Hash</dt>
              <dd title={selectedBlock.hash}><code>{shortHash(selectedBlock.hash)}</code></dd>
            </div>
            <div>
              <dt>Confirmations</dt>
              <dd><span className="badge badge-confirmed">{selectedBlock.confirmations} conf</span></dd>
            </div>
            <div>
              <dt>Block Time</dt>
              <dd>{formatTime(selectedBlock.time)}</dd>
            </div>
            <div>
              <dt>Median Time</dt>
              <dd>{formatTime(selectedBlock.median_time)}</dd>
            </div>
            <div>
              <dt>Size / Weight</dt>
              <dd>{selectedBlock.size} B · wt {selectedBlock.weight}</dd>
            </div>
            <div>
              <dt>Difficulty</dt>
              <dd>{selectedBlock.difficulty}</dd>
            </div>
            <div>
              <dt>Merkle Root</dt>
              <dd title={selectedBlock.merkle_root}><code>{shortHash(selectedBlock.merkle_root)}</code></dd>
            </div>
            <div>
              <dt>Nonce / Bits</dt>
              <dd>{selectedBlock.nonce} · {selectedBlock.bits}</dd>
            </div>
            <div>
              <dt>Version / Chainwork</dt>
              <dd>{selectedBlock.version_hex} · {selectedBlock.chainwork}</dd>
            </div>
          </dl>

          <div>
            <h4>Transactions in Block ({selectedBlock.transaction_ids.length})</h4>
            <ul className="block-transactions">
              {selectedBlock.transaction_ids.map((txid, index) => (
                <li key={`${txid}-${index}`} className="block-txid" title={txid}>
                  <small className="muted">{index === 0 ? "Coinbase: " : `#${index}: `}</small>
                  <code>{shortHash(txid)}</code>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
