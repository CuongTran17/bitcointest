# Transaction Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show readable wallet-to-wallet transfers such as `Alice -> Bob` and expose transaction status, confirmations, time, block hash, address, amount, and txid in the local Bitcoin Bank.

**Architecture:** Bitcoin Core remains the source of truth for on-chain transaction data. SQLite adds two metadata tables: generated address ownership and app-created transaction relationships. The existing transaction endpoint merges Bitcoin Core `listtransactions` rows with this metadata, and the existing dashboard renders the richer result.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy, SQLite, pytest, React, Vite, TypeScript, Bitcoin Core v31.1 regtest.

**Spec:** `docs/superpowers/specs/2026-08-20-transaction-explorer-design.md`

## Global Constraints

- Keep Bitcoin Core regtest as the source of truth for balances, transaction state, confirmations, time, and block hash.
- Store BTC amounts in backend application logic as integer satoshis; expose formatted BTC strings plus satoshi values.
- Store only app metadata in SQLite; never calculate or fake wallet balances in SQLite.
- Treat an unmapped destination as a valid external address with `to_wallet: null`.
- Keep existing endpoints backward-compatible where possible and preserve the current faucet, send, mine, and balance flows.
- Use the existing test database fixture and existing component/style conventions.

---

### Task 1: Add Metadata Models And Test Fixture Coverage

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/tests/conftest.py` only if model imports are not already registered
- Create: `backend/tests/test_metadata_models.py`

**Interfaces:**
- Produces `WalletAddress` with `id`, `address`, `wallet_name`, and `created_at`.
- Produces `AppTransaction` with `id`, `txid`, `from_wallet`, nullable `to_wallet`, `to_address`, `amount_sats`, `created_at`, and nullable `updated_at`.
- `address` and `txid` are unique so retries cannot create duplicate metadata for the same blockchain object.

- [ ] **Step 1: Write failing model tests**

```python
from app.models import AppTransaction, WalletAddress


def test_metadata_models_have_unique_lookup_fields():
    assert WalletAddress.__table__.columns.address.unique is True
    assert AppTransaction.__table__.columns.txid.unique is True
    assert AppTransaction.__table__.columns.amount_sats.type.python_type is int
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_metadata_models.py -v`

Expected: FAIL because the two models do not exist.

- [ ] **Step 3: Add the two SQLAlchemy models**

Use timezone-aware UTC timestamps produced by `datetime.now(timezone.utc)`. Use `String(80)` for wallet names, `String(128)` for addresses and txids, `Integer` for satoshis, and nullable `String` fields for the optional receiver wallet and block hash.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_metadata_models.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models.py backend/tests/test_metadata_models.py backend/tests/conftest.py
git commit -m "feat: add transaction metadata models"
```

### Task 2: Persist Generated Address Ownership

**Files:**
- Modify: `backend/app/services/wallets.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_address_metadata.py`

**Interfaces:**
- `create_address(wallet_name: str, db: Session) -> AddressRead` calls Bitcoin Core first, then stores `WalletAddress(address, wallet_name)`.
- `find_wallet_by_address(address: str, db: Session) -> str | None` returns the mapped wallet or `None`.
- `POST /wallets/{wallet_name}/address` receives a database session through `Depends(get_db)` and keeps its current response shape.

- [ ] **Step 1: Write failing endpoint tests**

```python
def test_create_address_persists_owner(client, monkeypatch):
    class FakeRpc:
        def get_new_address(self, wallet):
            return "bcrt1qaliceaddress"

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeRpc())
    response = client.post("/wallets/alice/address")

    assert response.status_code == 201
    lookup = client.get("/addresses/bcrt1qaliceaddress")
    assert lookup.status_code == 200
    assert lookup.json() == {"address": "bcrt1qaliceaddress", "wallet_name": "alice"}
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_address_metadata.py -v`

Expected: FAIL because the address metadata is not stored and the lookup endpoint does not exist.

- [ ] **Step 3: Implement persistence and lookup**

Add `AddressOwnerRead` and a small `addresses` router with `GET /addresses/{address}`. Commit the database row only after `get_new_address` succeeds. Use a duplicate-safe lookup so repeated history reads never create rows.

- [ ] **Step 4: Run address tests and the existing wallet tests**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_address_metadata.py tests/test_wallets.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models.py backend/app/schemas.py backend/app/services/wallets.py backend/app/routers backend/tests/test_address_metadata.py
git commit -m "feat: map generated addresses to wallets"
```

### Task 3: Record Send And Faucet Relationships

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/transactions.py`
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/app/routers/faucet.py`
- Create: `backend/tests/test_transaction_metadata.py`

**Interfaces:**
- `record_app_transaction(db, txid, from_wallet, to_wallet, to_address, amount_sats) -> AppTransaction` writes one metadata row.
- `send_transaction(payload: SendTransactionRequest, db: Session) -> SendTransactionRead` resolves `to_wallet` from the address table after Bitcoin Core accepts the send.
- `fund_from_faucet(wallet_name: str, payload: FaucetRequest, db: Session) -> FaucetRead` records `miner -> wallet_name` after the send succeeds.
- `SendTransactionRead` adds nullable `to_wallet`; `FaucetRead` remains backward-compatible and adds no required field.

- [ ] **Step 1: Write failing known-recipient and unknown-recipient tests**

```python
def test_send_records_known_recipient(client, monkeypatch):
    # First create Bob's address through the API so ownership is real metadata.
    class FakeRpc:
        def get_new_address(self, wallet):
            return "bcrt1qbobaddress"

        def send_to_address(self, wallet, address, amount_btc):
            return "sendtxid"

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeRpc())
    client.post("/wallets/bob/address")
    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post("/transactions/send", json={
        "from_wallet": "alice",
        "to_address": "bcrt1qbobaddress",
        "amount_btc": "2.00000000",
    })

    assert response.json()["to_wallet"] == "bob"


def test_send_allows_unknown_recipient(client, monkeypatch):
    class FakeRpc:
        def send_to_address(self, wallet, address, amount_btc):
            return "external-txid"

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())
    response = client.post("/transactions/send", json={
        "from_wallet": "alice",
        "to_address": "bcrt1qexternaladdress",
        "amount_btc": "1.00000000",
    })

    assert response.status_code == 201
    assert response.json()["to_wallet"] is None
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_transaction_metadata.py -v`

Expected: FAIL because the response/schema/service do not yet include metadata.

- [ ] **Step 3: Implement the metadata write path**

Pass `Session` from the routers into the services. Resolve the recipient with `find_wallet_by_address`. Insert `AppTransaction` only after `send_to_address` succeeds. For faucet transactions, insert after the send and before/after mining; mining failure must not erase the accepted transaction.

- [ ] **Step 4: Run focused and existing transaction tests**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_transaction_metadata.py tests/test_transactions.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/schemas.py backend/app/services/transactions.py backend/app/routers backend/tests/test_transaction_metadata.py
git commit -m "feat: record wallet transfer metadata"
```

### Task 4: Enrich Transaction History From Bitcoin Core

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/transactions.py`
- Modify: `backend/tests/test_transactions.py`

**Interfaces:**
- `TransactionRead` adds `from_wallet: str | None` and `to_wallet: str | None` while retaining `category`, `address`, and all existing fields.
- `list_transactions(wallet_name: str, db: Session) -> list[TransactionRead]` merges `listtransactions` rows with `AppTransaction` rows by txid.

- [ ] **Step 1: Add failing enrichment assertions**

Extend the existing transaction history test with:

```python
assert response.json()[0]["from_wallet"] == "alice"
assert response.json()[0]["to_wallet"] == "bob"
assert response.json()[0]["status"] == "confirmed"
assert response.json()[0]["blockhash"] == "blockhash1"
```

Add a pending row assertion where `confirmations == 0`, `status == "pending"`, and `blockhash is None`.

- [ ] **Step 2: Run the test and verify it fails**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_transactions.py::test_list_transactions_returns_status_and_metadata -v`

Expected: FAIL because wallet relationship fields are missing.

- [ ] **Step 3: Implement the merge and status refresh**

Load metadata for the returned txids. Use Bitcoin Core’s current confirmations, time, and block hash on every request. Set `status` to `confirmed` when confirmations are greater than zero, otherwise `pending`. Use the signed RPC amount for the selected wallet, while the app metadata amount remains the positive transfer amount in satoshis.

- [ ] **Step 4: Run the complete backend suite**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -v`

Expected: all backend tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/schemas.py backend/app/services/transactions.py backend/app/routers/transactions.py backend/tests/test_transactions.py
git commit -m "feat: enrich transaction history with wallet relationships"
```

### Task 5: Render Sender And Receiver In The Frontend

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/components/TransactionHistory.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/App.tsx` only if refresh/error handling needs the updated response

**Interfaces:**
- `Transaction` adds `from_wallet: string | null` and `to_wallet: string | null`.
- The transaction history displays direction, `From`, `To`, amount, status, confirmations, and a shortened txid with the full txid available through the native `title` tooltip.

- [ ] **Step 1: Update TypeScript contract and write the component expectation**

Represent an unknown wallet as `null`, render it as `Unknown address`, and keep pending rows visually distinct from confirmed rows.

- [ ] **Step 2: Implement the compact history table/list**

For each transaction render:

```text
Alice -> Bob
2.00000000 BTC
confirmed · 1 confirmation
txid: abc123...
```

For a receive row, render the mapped sender if known or `Unknown address`. Keep the existing mobile-friendly stacked layout rather than introducing a wide desktop-only table.

- [ ] **Step 3: Build the frontend**

Run: `cd frontend; npm.cmd run build`

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src
git commit -m "feat: show wallet transfer direction in history"
```

### Task 6: Document And Verify The End-To-End Demo

**Files:**
- Modify: `README.md`
- Modify: `backend/tests/test_transaction_metadata.py` if the final demo response needs a regression assertion

**Interfaces:**
- Documentation explains the address-first interaction: Bob creates an address, Alice sends to it, then mining changes the status.
- Documentation explains that the app can identify wallets only for addresses generated and stored by this app.

- [ ] **Step 1: Add the enriched demo flow to README**

Document this exact sequence:

```text
1. Select Bob and click New address.
2. Copy Bob’s bcrt1 address.
3. Select Alice and send 2 BTC to that address.
4. Select Bob and observe `Alice -> Bob`, pending, and 0 confirmations.
5. Click Mine 1 block.
6. Refresh or switch wallets and observe confirmed, 1 confirmation, and a block hash.
7. Open the txid tooltip/value when debugging the transaction.
```

Include the unknown-address behavior and the backend endpoint `GET /transactions/{wallet_name}`.

- [ ] **Step 2: Run backend tests**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -v`

Expected: all tests pass.

- [ ] **Step 3: Build frontend**

Run: `cd frontend; npm.cmd run build`

Expected: build succeeds.

- [ ] **Step 4: Manually verify the regtest flow**

With Bitcoin Core, backend, and frontend running, create Bob’s address, send from Alice, inspect pending history, mine one block, and inspect confirmed history. Verify that a faucet transaction displays `miner -> alice` and that an external/unmapped address displays `Unknown address`.

- [ ] **Step 5: Commit**

```powershell
git add README.md backend/tests/test_transaction_metadata.py
git commit -m "docs: add transaction explorer demo flow"
```

## Final Verification

- [ ] `cd backend; .\.venv\Scripts\python.exe -m pytest -v` passes.
- [ ] `cd frontend; npm.cmd run build` passes.
- [ ] `POST /wallets/bob/address` creates and remembers Bob’s address.
- [ ] `POST /transactions/send` returns `to_wallet: "bob"` for Bob’s stored address.
- [ ] `GET /transactions/alice` shows `from_wallet: "alice"`, `to_wallet: "bob"`, and pending status before mining.
- [ ] After `POST /mine`, the same transaction shows confirmed status, updated confirmations, and a block hash.
- [ ] Faucet history identifies `miner -> alice`.
- [ ] Unknown external destinations remain valid and show `to_wallet: null`.

## Self-Review

- Spec coverage: address ownership, transaction metadata, known/unknown recipients, faucet metadata, pending/confirmed enrichment, frontend display, documentation, and verification are covered by Tasks 1-6.
- Placeholder scan: all implementation steps contain concrete files, interfaces, commands, or expected behavior.
- Type consistency: `to_wallet` is nullable in both backend schema and frontend type; `amount_sats` remains an integer; history keeps the existing `status`, `confirmations`, `time`, and `blockhash` fields.
