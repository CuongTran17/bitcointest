# UTXO Viewer Design

**Date:** 2026-08-20

## Goal

Add a wallet-scoped UTXO Viewer to Local Bitcoin Bank. The selected wallet in the existing dashboard should show the unspent transaction outputs currently controlled by that Bitcoin Core wallet, including confirmation state, value, address, and transaction reference.

## Scope

The first version is wallet-scoped and uses the existing selected-wallet flow for Alice, Bob, Miner, and future dynamically created wallets. It does not scan arbitrary addresses and does not add wallet creation in this feature.

The API must accept any valid `wallet_name` rather than hardcoding the three current demo wallets. When a future wallet is loaded in Bitcoin Core and exposed by the user list, the same endpoint and UI must work without feature-specific changes.

## Backend Design

Bitcoin Core is the source of truth. The backend adds a thin RPC method around `listunspent` and does not copy UTXOs into SQLite.

Endpoint:

```text
GET /utxos/{wallet_name}
```

The service first verifies that the wallet is loaded with the existing `ensure_wallet_loaded` behavior. It then calls `listunspent` for confirmations from `0` through `9999999`, so pending and confirmed outputs are both visible. The result is sorted deterministically with confirmed outputs first, then newest block height, then value descending, then `txid` and `vout`.

Response shape:

```json
{
  "wallet_name": "alice",
  "utxo_count": 2,
  "confirmed_count": 1,
  "unconfirmed_count": 1,
  "total_amount_btc": "8.50000000",
  "total_amount_sats": 850000000,
  "utxos": [
    {
      "txid": "abc...",
      "vout": 0,
      "address": "bcrt1...",
      "amount_btc": "8.00000000",
      "amount_sats": 800000000,
      "confirmations": 1,
      "blockhash": "000...",
      "blockheight": 101,
      "spendable": true,
      "solvable": true,
      "safe": true
    }
  ]
}
```

`address`, `blockhash`, and `blockheight` are nullable because Bitcoin Core can return UTXOs without an address or block data. Amounts are represented as an 8-decimal string and integer satoshis; application code must not use floating point for BTC arithmetic.

An unloaded wallet returns HTTP 404 through the existing Bitcoin Core wallet validation. Bitcoin Core failures continue to surface as the existing RPC error response. An empty wallet is a successful response with zero counts, zero totals, and an empty `utxos` array.

## Frontend Design

Add a `UTXO Viewer` section to the existing single-page dashboard below the transaction history. It follows the selected wallet automatically and refreshes whenever the selected wallet changes or a send, faucet, or mining action completes.

The section contains:

- total UTXO count;
- confirmed and unconfirmed counts;
- total value in BTC and satoshis;
- a refresh button with loading and error states;
- a responsive table/list showing shortened txid, vout, address, value, confirmations, block height, and spendable state;
- an empty state for wallets with no UTXOs;
- a compact message when an output has no address.

The frontend continues using the existing `API_BASE`, fetch helper, selected wallet, and plain CSS design system. No new dependency is required. The table must remain readable on narrow screens by allowing horizontal scrolling or switching rows to a stacked layout.

## Testing and Acceptance Criteria

Backend tests must verify:

- the RPC wrapper calls `listunspent` with the wallet context and confirmation range;
- BTC values are converted exactly to satoshis;
- confirmed and unconfirmed counts and totals are calculated correctly;
- nullable address and block fields are accepted;
- output ordering is deterministic;
- an unloaded wallet returns 404;
- an empty result returns zero totals and an empty list.

Frontend verification must include a successful production TypeScript build. The UI must compile with the selected-wallet refresh flow and render loading, error, empty, and populated states.

The feature is complete when a user can fund or send coins, mine or leave a transaction pending, switch between Alice/Bob/Miner, and see the corresponding UTXO set update without manually entering an address.

## Out of Scope

- arbitrary-address UTXO lookup using `scantxoutset`;
- historical UTXO snapshots;
- coin selection or manual UTXO spending;
- wallet creation and wallet loading UI;
- block explorer and mempool views.
