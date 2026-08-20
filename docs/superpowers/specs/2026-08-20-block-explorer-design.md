# Block Explorer Design

**Date:** 2026-08-20

## Goal

Add a local regtest Block Explorer that lets users browse the newest blocks, inspect block metadata by height or hash, and see the transaction ids included in each block.

## Scope

The first version is node-wide and reads the active chain directly from Bitcoin Core. It includes:

- a latest-block list with a configurable bounded limit;
- block lookup by numeric height or 64-character block hash;
- block metadata such as height, hash, time, size, weight, difficulty, nonce, merkle root, confirmations, and chain links;
- the transaction ids included in a block;
- frontend refresh after mining;
- stable txid display ready to connect to the Transaction Detail Page.

It does not persist blocks in SQLite, decode every transaction inside the block, scan forks, or add reorg management. Bitcoin Core remains the source of truth.

## Data Sources

The backend uses these node-level RPCs:

- `getblockchaininfo` to read the active chain, current tip height, and tip hash;
- `getblockhash height` to resolve a numeric height to the active-chain block hash;
- `getblock blockhash 1` to read block metadata and transaction ids.

Block verbosity `1` is intentional. Verbosity `2` would decode every transaction and duplicate the responsibility of the Transaction Detail feature. The explorer links/display txids, while transaction decoding remains a separate endpoint.

## Backend API

Latest blocks:

```text
GET /blocks?limit=20
```

The limit defaults to `20` and is constrained to `1..100`. Blocks are returned newest first. When the chain has fewer blocks than the requested limit, the response contains all available blocks.

Response shape:

```json
{
  "chain": "regtest",
  "tip_height": 101,
  "tip_hash": "000...",
  "blocks": [
    {
      "height": 101,
      "hash": "000...",
      "confirmations": 1,
      "time": 1787030000,
      "size": 285,
      "weight": 1140,
      "transaction_count": 1,
      "previous_hash": "000...",
      "next_hash": null
    }
  ]
}
```

Block detail:

```text
GET /blocks/{block_ref}
```

`block_ref` accepts either a non-negative decimal height or a 64-character hexadecimal block hash. A height is resolved through `getblockhash` before calling `getblock`.

The detail response includes all list fields plus `version`, `version_hex`, `merkle_root`, `median_time`, `nonce`, `bits`, `difficulty`, `chainwork`, and `transaction_ids`.

Invalid references return HTTP 422. A valid but unavailable height/hash returns HTTP 404 through the existing `BitcoinRpcError` handler. An RPC connection failure remains a 502 error.

## Frontend Design

Add a global `Block Explorer` section below the existing Mempool View. It is independent of the selected wallet.

The section contains:

- chain name, current tip height, and shortened tip hash;
- a limit selector or bounded numeric control for recent blocks;
- a refresh button with loading and error states;
- a newest-first block list showing height, shortened hash, time, transaction count, size, weight, confirmations, and previous/next links;
- a selected-block detail area showing the full block metadata;
- transaction ids in the selected block, rendered as stable text with a title tooltip until Transaction Detail navigation is available;
- an empty/initial state for a node that cannot yet provide block data.

Mining must refresh the explorer so a newly mined block becomes the selected newest block. Switching wallets must not reload the explorer because blocks are global.

The layout must remain usable on narrow screens. Long hashes and txids must wrap or be shortened with the full value available through a `title` attribute. No new frontend dependency is required.

## Testing and Acceptance Criteria

Backend tests must verify:

- RPC wrappers call `getblockchaininfo`, `getblockhash`, and `getblock` with the expected parameters;
- latest-block listing resolves the active tip and returns newest-first blocks;
- the limit is bounded and passed into the service correctly;
- height and hash references resolve to the same block detail response;
- detail includes transaction ids and block metadata;
- invalid references return 422;
- unavailable blocks return 404;
- an RPC failure reaches the existing error handler.

Frontend verification must include a successful production TypeScript build. The UI must compile and render loading, error, empty, recent-block, selected-detail, and transaction-list states.

The feature is complete when a user can mine a block, refresh Block Explorer, see the new height/hash/time, select the block, and inspect its included txids.

## Out of Scope

- persistent block/index tables;
- full transaction decoding inside block responses;
- fork/reorg visualization;
- arbitrary chain navigation beyond height/hash lookup;
- block submission, mining controls beyond the existing Mine action;
- transaction detail implementation itself.
