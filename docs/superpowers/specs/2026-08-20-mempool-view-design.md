# Mempool View Design

**Date:** 2026-08-20

## Goal

Add a node-wide Mempool View to Local Bitcoin Bank so users can see transactions that have been accepted by the local regtest node but are not yet included in a mined block.

## Scope

The view is global to the Bitcoin Core node, not limited to the selected wallet. Mempool membership belongs to the node, while wallet labels are optional application metadata.

The first version supports the current Alice, Bob, and Miner wallets and future dynamically created wallets without hardcoded names. It does not add transaction submission, replacement, eviction, package editing, or manual fee bumping.

## Data Sources and Enrichment

Bitcoin Core remains authoritative for current mempool membership and transaction policy data:

- `getrawmempool true` provides the current transaction set and fields such as vsize, weight, fee, time, entry height, ancestor/descendant counts, dependencies, and RBF/unbroadcast flags.
- `getrawtransaction <txid> true` provides decoded transaction output data for transactions currently in the mempool.

SQLite is used only for existing application metadata. `AppTransaction` supplies `from_wallet`, `to_wallet`, and the known recipient address when the transaction was created through the app. `WalletAddress` can map decoded output addresses to locally known wallet names. No mempool snapshot table is added.

Input ownership is not guessed from raw transaction inputs. A raw input contains a previous transaction outpoint, not the sender address. Therefore, transactions without app metadata may have `from_wallet: null` and `to_wallet: null` even when their decoded outputs are visible.

## Backend API

Endpoint:

```text
GET /mempool
```

Response shape:

```json
{
  "transaction_count": 1,
  "total_vsize": 141,
  "total_fee_btc": "0.00001000",
  "total_fee_sats": 1000,
  "transactions": [
    {
      "txid": "abc...",
      "wtxid": "def...",
      "vsize": 141,
      "weight": 564,
      "fee_btc": "0.00001000",
      "fee_sats": 1000,
      "fee_rate_sat_vb": "7.09219858",
      "time": 1787030000,
      "entry_height": 101,
      "confirmations": 0,
      "from_wallet": "alice",
      "to_wallet": "bob",
      "to_address": "bcrt1...",
      "status": "pending",
      "ancestor_count": 1,
      "descendant_count": 1,
      "depends": [],
      "spent_by": [],
      "replaceable": true,
      "unbroadcast": false,
      "output_addresses": ["bcrt1..."]
    }
  ]
}
```

Amounts use an 8-decimal BTC string and integer satoshis. Fee rate is calculated as `fee_sats / vsize` and returned as a decimal string; if vsize is missing or zero, it is `null`. `from_wallet`, `to_wallet`, `to_address`, and `wtxid` are nullable when Bitcoin Core or local metadata does not provide them. `output_addresses` may be empty for non-standard outputs.

Transactions are sorted by mempool entry time descending, then txid ascending for deterministic output. The summary total fee is the sum of each transaction's base fee, not ancestor or descendant fee totals.

The endpoint returns an empty successful response when the mempool is empty. Bitcoin Core RPC failures use the existing error handler and status mapping.

## Frontend Design

Add a global `Mempool View` section below the existing transaction history and UTXO Viewer. It is not tied to the selected wallet and remains visible while users switch Alice, Bob, and Miner.

The section contains:

- transaction count;
- total virtual size;
- total pending fees in BTC and satoshis;
- a refresh button;
- a pending transaction table with shortened txid, wallet direction, fee, fee rate, vsize, time, ancestor/descendant counts, and RBF state;
- an empty state when no transactions are waiting;
- an error state when Bitcoin Core is unavailable;
- a link-style action to open the existing or planned Transaction Detail view when a detail route is available.

Because the current Transaction Detail Page is planned but not necessarily implemented before Mempool View, the first implementation may render the txid as text with a `title` tooltip. It must keep the transaction id as a stable key and be ready for a later `onSelectTransaction(txid)` integration without changing the API shape.

The frontend fetches mempool data independently from the selected-wallet balance/history/UTXO refresh. It refreshes on initial load, after send, after faucet, after mine, and through the manual refresh button. Mining is expected to clear or reduce the mempool, which makes the demo visibly useful.

## Testing and Acceptance Criteria

Backend tests must verify:

- the RPC wrapper calls `getrawmempool` with verbose mode;
- decoded transaction enrichment calls `getrawtransaction` only for returned mempool txids;
- app metadata maps known `from_wallet`, `to_wallet`, and `to_address`;
- unknown transactions remain valid with nullable wallet labels;
- fee BTC to satoshi conversion and fee-rate calculation are exact;
- summary fee and vsize totals are correct;
- deterministic newest-first ordering is applied;
- an empty mempool returns zero totals and an empty list;
- Bitcoin Core errors reach the existing API error handler.

Frontend verification must include a successful production TypeScript build. The UI must compile and render loading, error, empty, and populated states without adding dependencies.

The feature is complete when a user can send a transaction, see it in Mempool View with `pending` and fee metadata, mine a block, refresh, and observe it disappear from the mempool while the transaction history shows confirmation.

## Out of Scope

- mempool transaction submission or raw transaction editing;
- RBF replacement and fee bumping;
- mempool package editing or eviction controls;
- persistent mempool history;
- arbitrary address ownership inference from previous transactions;
- block explorer and UTXO viewer changes beyond refresh integration.
