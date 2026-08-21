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
          <p className="label">Blockchain</p>
          <h3>Block Explorer</h3>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {blockList && (
        <div className="block-explorer-summary">
          <div>
            <span className="label">Chain</span>
            <p><strong>{blockList.chain}</strong></p>
          </div>
          <div>
            <span className="label">Tip Height</span>
            <p><strong>{blockList.tip_height}</strong></p>
          </div>
          <div>
            <span className="label">Tip Hash</span>
            <p title={blockList.tip_hash}><strong>{shortHash(blockList.tip_hash)}</strong></p>
          </div>
        </div>
      )}

      <div className="block-explorer-toolbar">
        <form onSubmit={handleLookupSubmit} style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input
            type="text"
            placeholder="Search by block height or 64-char hash"
            value={lookupInput}
            onChange={(e) => setLookupInput(e.target.value)}
            aria-label="Block height or hash"
          />
          <button type="submit" disabled={!lookupInput.trim()}>
            Lookup
          </button>
        </form>

        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          <label htmlFor="block-limit-select" className="label">Limit:</label>
          <select
            id="block-limit-select"
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
            style={{ padding: "8px", borderRadius: "6px", border: "1px solid #ccd4dc" }}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {loading && <p>Loading blocks...</p>}
      {!loading && error && <p className="error">{error}</p>}
      {!loading && !error && blockList && blockList.blocks.length === 0 && (
        <p>No blocks found.</p>
      )}
      {!loading && !error && blockList && blockList.blocks.length > 0 && (
        <ul className="block-list">
          {blockList.blocks.map((block) => (
            <li key={block.hash}>
              <button
                type="button"
                className={`block-row ${selectedBlock?.hash === block.hash ? "selected" : ""}`}
                onClick={() => onSelectBlock(String(block.height))}
              >
                <div>
                  <strong>Block #{block.height}</strong>
                  <br />
                  <small className="muted" title={block.hash}>{shortHash(block.hash)}</small>
                </div>
                <div>
                  <span>{formatTime(block.time)}</span>
                  <br />
                  <small className="muted">{block.transaction_count} txs · {block.size} bytes</small>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span>{block.confirmations} conf</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {detailLoading && <p>Loading block detail...</p>}
      {!detailLoading && detailError && <p className="error">{detailError}</p>}
      {!detailLoading && !detailError && selectedBlock && (
        <div className="block-detail" style={{ marginTop: "20px", borderTop: "2px solid #edf1f5", paddingTop: "16px" }}>
          <div className="detail-header">
            <div>
              <p className="label">Selected block</p>
              <h3>Block #{selectedBlock.height}</h3>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              {selectedBlock.previous_hash && (
                <button
                  type="button"
                  onClick={() => onSelectBlock(selectedBlock.previous_hash!)}
                  title={selectedBlock.previous_hash}
                >
                  &larr; Prev Block
                </button>
              )}
              {selectedBlock.next_hash && (
                <button
                  type="button"
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
              <dd title={selectedBlock.hash}>{shortHash(selectedBlock.hash)}</dd>
            </div>
            <div>
              <dt>Confirmations</dt>
              <dd>{selectedBlock.confirmations}</dd>
            </div>
            <div>
              <dt>Time</dt>
              <dd>{formatTime(selectedBlock.time)}</dd>
            </div>
            <div>
              <dt>Median Time</dt>
              <dd>{formatTime(selectedBlock.median_time)}</dd>
            </div>
            <div>
              <dt>Size / Weight</dt>
              <dd>{selectedBlock.size} bytes · {selectedBlock.weight} weight</dd>
            </div>
            <div>
              <dt>Difficulty</dt>
              <dd>{selectedBlock.difficulty}</dd>
            </div>
            <div>
              <dt>Merkle Root</dt>
              <dd title={selectedBlock.merkle_root}>{shortHash(selectedBlock.merkle_root)}</dd>
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

          <div style={{ marginTop: "16px" }}>
            <h4>Transactions in Block ({selectedBlock.transaction_ids.length})</h4>
            <ul className="block-transactions">
              {selectedBlock.transaction_ids.map((txid, index) => (
                <li key={`${txid}-${index}`} className="block-txid" title={txid}>
                  <code>{index === 0 ? "Coinbase: " : `${index}. `}{shortHash(txid)}</code>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
