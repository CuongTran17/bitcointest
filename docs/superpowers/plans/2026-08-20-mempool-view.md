# Mempool View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a node-wide Mempool View that shows pending regtest transactions, fee metadata, dependency counts, and known local wallet relationships.

**Architecture:** Bitcoin Core remains authoritative through node-level `getrawmempool true` and decoded `getrawtransaction <txid> true` calls. SQLite is read only for existing `AppTransaction` and `WalletAddress` metadata; no mempool snapshot is persisted. The frontend loads a global mempool summary independently from the selected wallet and refreshes it after initial load, send, faucet, mine, and manual refresh.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest, React, TypeScript, Vite, plain CSS, Bitcoin Core regtest RPC.

**Spec:** `docs/superpowers/specs/2026-08-20-mempool-view-design.md`

## Global Constraints

- Mempool scope is node-wide; do not add a `wallet_name` path parameter.
- Use `getrawmempool` with verbose mode and `getrawtransaction` with verbose mode for returned mempool txids.
- Treat Bitcoin Core as the source of current mempool state; do not create a SQLite mempool table or cache.
- Use `Decimal` and integer satoshis for fee totals and fee rates; do not use floating point in backend calculations.
- Do not infer sender ownership from raw transaction inputs; only use existing app metadata for wallet labels.
- Keep unknown transactions valid with nullable wallet fields and an empty or partial address list.
- Preserve the pre-existing untracked `backend/package-lock.json`; do not add, delete, or modify it.
- Do not add dependencies.

---

### Task 1: Add mempool RPC methods and response schemas

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_mempool.py`

**Interfaces:**
- Consumes: `BitcoinRpcClient.call(method, params, wallet)`.
- Produces: `get_raw_mempool(verbose: bool = True) -> dict[str, dict[str, Any]]`.
- Produces: `get_raw_transaction(txid: str, verbose: bool = True) -> dict[str, Any]`.
- Produces: `MempoolTransactionRead` and `MempoolSummaryRead` schemas.

- [ ] **Step 1: Write failing RPC wrapper tests**

Create `backend/tests/test_mempool.py` with:

```python
from app.bitcoin_rpc import BitcoinRpcClient


def test_get_raw_mempool_requests_verbose_node_data(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"tx1": {"vsize": 141}}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_raw_mempool()

    assert result == {"tx1": {"vsize": 141}}
    assert calls == [("getrawmempool", [True], None)]


def test_get_raw_transaction_requests_verbose_mempool_transaction(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"txid": "tx1", "vout": []}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_raw_transaction("tx1")

    assert result == {"txid": "tx1", "vout": []}
    assert calls == [("getrawtransaction", ["tx1", True], None)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_mempool.py::test_get_raw_mempool_requests_verbose_node_data tests/test_mempool.py::test_get_raw_transaction_requests_verbose_mempool_transaction -v
```

Expected: FAIL because the two RPC methods do not exist.

- [ ] **Step 3: Implement the RPC methods**

Add to `BitcoinRpcClient` in `backend/app/bitcoin_rpc.py`:

```python
def get_raw_mempool(self, verbose: bool = True) -> dict[str, dict[str, Any]]:
    return self.call("getrawmempool", [verbose])


def get_raw_transaction(self, txid: str, verbose: bool = True) -> dict[str, Any]:
    return self.call("getrawtransaction", [txid, verbose])
```

These methods intentionally do not pass a wallet name because mempool and raw transaction RPCs are node-level calls.

- [ ] **Step 4: Add Pydantic response models**

Append to `backend/app/schemas.py`:

```python
class MempoolTransactionRead(BaseModel):
    txid: str
    wtxid: str | None = None
    vsize: int
    weight: int
    fee_btc: str
    fee_sats: int
    fee_rate_sat_vb: str | None = None
    time: int | None = None
    entry_height: int | None = None
    confirmations: int
    from_wallet: str | None = None
    to_wallet: str | None = None
    to_address: str | None = None
    status: str
    ancestor_count: int
    descendant_count: int
    depends: list[str]
    spent_by: list[str]
    replaceable: bool
    unbroadcast: bool
    output_addresses: list[str]


class MempoolSummaryRead(BaseModel):
    transaction_count: int
    total_vsize: int
    total_fee_btc: str
    total_fee_sats: int
    transactions: list[MempoolTransactionRead]
```

- [ ] **Step 5: Run the RPC tests and existing backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mempool.py::test_get_raw_mempool_requests_verbose_node_data tests/test_mempool.py::test_get_raw_transaction_requests_verbose_mempool_transaction tests/test_health.py tests/test_transactions.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the RPC and schema slice**

```powershell
git add backend/app/bitcoin_rpc.py backend/app/schemas.py backend/tests/test_mempool.py
git commit -m "feat: add mempool RPC models"
```

### Task 2: Implement mempool enrichment service and API endpoint

**Files:**
- Create: `backend/app/services/mempool.py`
- Create: `backend/app/routers/mempool.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_mempool.py`

**Interfaces:**
- Consumes: `BitcoinRpcClient.get_raw_mempool`, `BitcoinRpcClient.get_raw_transaction`, `AppTransaction`, `WalletAddress`, and `MempoolSummaryRead`.
- Produces: `list_mempool_transactions(db: Session) -> MempoolSummaryRead`.
- Produces: `GET /mempool` with response model `MempoolSummaryRead`.

- [ ] **Step 1: Write the failing endpoint test for known and unknown transactions**

Append to `backend/tests/test_mempool.py`:

```python
from decimal import Decimal

from fastapi.testclient import TestClient


def test_mempool_returns_fee_summary_and_known_wallet_metadata(client: TestClient, monkeypatch):
    class FakeAddressRpc:
        def get_new_address(self, wallet: str):
            assert wallet == "bob"
            return "bcrt1qbobaddress"

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeAddressRpc())
    assert client.post("/wallets/bob/address").status_code == 201

    class FakeSendRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            assert wallet == "alice"
            assert address == "bcrt1qbobaddress"
            assert amount_btc == Decimal("2.00000000")
            return "known-tx"

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeSendRpc())
    assert client.post(
        "/transactions/send",
        json={
            "from_wallet": "alice",
            "to_address": "bcrt1qbobaddress",
            "amount_btc": "2.00000000",
        },
    ).status_code == 201

    class FakeMempoolRpc:
        def get_raw_mempool(self, verbose: bool = True):
            assert verbose is True
            return {
                "unknown-tx": {
                    "wtxid": "unknown-wtx",
                    "vsize": 100,
                    "weight": 400,
                    "fees": {"base": "0.00002000"},
                    "time": 1787030001,
                    "height": 102,
                    "ancestorcount": 1,
                    "descendantcount": 1,
                    "depends": [],
                    "spentby": [],
                    "bip125-replaceable": False,
                    "unbroadcast": False,
                },
                "known-tx": {
                    "wtxid": "known-wtx",
                    "vsize": 141,
                    "weight": 564,
                    "fees": {"base": "0.00001000"},
                    "time": 1787030000,
                    "height": 101,
                    "ancestorcount": 1,
                    "descendantcount": 2,
                    "depends": ["parent-tx"],
                    "spentby": ["child-tx"],
                    "bip125-replaceable": True,
                    "unbroadcast": False,
                },
            }

        def get_raw_transaction(self, txid: str, verbose: bool = True):
            assert verbose is True
            return {
                "txid": txid,
                "vout": [
                    {
                        "value": "2.00000000",
                        "scriptPubKey": {
                            "addresses": [
                                "bcrt1qbobaddress" if txid == "known-tx" else "bcrt1qexternal"
                            ]
                        },
                    }
                ],
            }

    monkeypatch.setattr("app.services.mempool.BitcoinRpcClient", lambda: FakeMempoolRpc())

    response = client.get("/mempool")

    assert response.status_code == 200
    payload = response.json()
    assert payload["transaction_count"] == 2
    assert payload["total_vsize"] == 241
    assert payload["total_fee_btc"] == "0.00003000"
    assert payload["total_fee_sats"] == 3000
    assert [item["txid"] for item in payload["transactions"]] == ["unknown-tx", "known-tx"]
    known = payload["transactions"][1]
    assert known["from_wallet"] == "alice"
    assert known["to_wallet"] == "bob"
    assert known["to_address"] == "bcrt1qbobaddress"
    assert known["fee_sats"] == 1000
    assert known["fee_rate_sat_vb"] == "7.09219858"
    assert known["status"] == "pending"
    assert known["output_addresses"] == ["bcrt1qbobaddress"]
    assert payload["transactions"][0]["from_wallet"] is None
    assert payload["transactions"][0]["to_wallet"] is None


def test_mempool_returns_empty_summary(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_raw_mempool(self, verbose: bool = True):
            return {}

    monkeypatch.setattr("app.services.mempool.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/mempool")

    assert response.status_code == 200
    assert response.json() == {
        "transaction_count": 0,
        "total_vsize": 0,
        "total_fee_btc": "0.00000000",
        "total_fee_sats": 0,
        "transactions": [],
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mempool.py::test_mempool_returns_fee_summary_and_known_wallet_metadata tests/test_mempool.py::test_mempool_returns_empty_summary -v
```

Expected: FAIL because the mempool service and route do not exist.

- [ ] **Step 3: Implement normalization helpers and enrichment service**

Create `backend/app/services/mempool.py`:

```python
from decimal import Decimal

from sqlalchemy.orm import Session

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.models import AppTransaction, WalletAddress
from app.schemas import MempoolSummaryRead, MempoolTransactionRead


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def format_fee_rate(fee_sats: int, vsize: int) -> str | None:
    if vsize <= 0:
        return None
    return f"{Decimal(fee_sats) / Decimal(vsize):.8f}"


def output_addresses(raw_transaction: dict) -> list[str]:
    addresses = []
    for output in raw_transaction.get("vout", []):
        for address in output.get("scriptPubKey", {}).get("addresses", []):
            if address not in addresses:
                addresses.append(address)
    return addresses


def list_mempool_transactions(db: Session) -> MempoolSummaryRead:
    rpc = BitcoinRpcClient()
    raw_entries = rpc.get_raw_mempool(verbose=True)
    if not raw_entries:
        return MempoolSummaryRead(
            transaction_count=0,
            total_vsize=0,
            total_fee_btc="0.00000000",
            total_fee_sats=0,
            transactions=[],
        )

    txids = list(raw_entries)
    metadata_by_txid = {
        row.txid: row
        for row in db.query(AppTransaction).filter(AppTransaction.txid.in_(txids)).all()
    }
    known_addresses = {
        row.address: row.wallet_name
        for row in db.query(WalletAddress).all()
    }

    transactions = []
    for txid, entry in raw_entries.items():
        fee_value = entry.get("fees", {}).get("base", entry.get("fee", "0"))
        fee_btc = Decimal(str(fee_value))
        fee_sats = btc_to_sats(fee_btc)
        vsize = int(entry.get("vsize", 0))
        raw_transaction = rpc.get_raw_transaction(txid, verbose=True)
        addresses = output_addresses(raw_transaction)
        metadata = metadata_by_txid.get(txid)
        mapped_wallets = {known_addresses[address] for address in addresses if address in known_addresses}
        to_wallet = metadata.to_wallet if metadata is not None else next(iter(sorted(mapped_wallets)), None)
        to_address = metadata.to_address if metadata is not None else (addresses[0] if addresses else None)
        transactions.append(
            MempoolTransactionRead(
                txid=txid,
                wtxid=entry.get("wtxid"),
                vsize=vsize,
                weight=int(entry.get("weight", 0)),
                fee_btc=format_btc(fee_btc),
                fee_sats=fee_sats,
                fee_rate_sat_vb=format_fee_rate(fee_sats, vsize),
                time=entry.get("time"),
                entry_height=entry.get("height"),
                confirmations=0,
                from_wallet=metadata.from_wallet if metadata is not None else None,
                to_wallet=to_wallet,
                to_address=to_address,
                status="pending",
                ancestor_count=int(entry.get("ancestorcount", 0)),
                descendant_count=int(entry.get("descendantcount", 0)),
                depends=list(entry.get("depends", [])),
                spent_by=list(entry.get("spentby", [])),
                replaceable=bool(entry.get("bip125-replaceable", False)),
                unbroadcast=bool(entry.get("unbroadcast", False)),
                output_addresses=addresses,
            )
        )

    transactions.sort(key=lambda item: (-(item.time or 0), item.txid))
    total_fee_sats = sum(item.fee_sats for item in transactions)
    return MempoolSummaryRead(
        transaction_count=len(transactions),
        total_vsize=sum(item.vsize for item in transactions),
        total_fee_btc=format_btc(Decimal(total_fee_sats) / Decimal("100000000")),
        total_fee_sats=total_fee_sats,
        transactions=transactions,
    )
```

The `metadata.to_wallet` value takes precedence over output address inference because it records the application's explicit recipient mapping. Address inference is only a fallback for transactions without app metadata.

- [ ] **Step 4: Add the router and register it**

Create `backend/app/routers/mempool.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import MempoolSummaryRead
from app.services import mempool as mempool_service

router = APIRouter(prefix="/mempool", tags=["mempool"])


@router.get("", response_model=MempoolSummaryRead)
def get_mempool(db: Session = Depends(get_db)):
    return mempool_service.list_mempool_transactions(db)
```

Modify `backend/app/main.py` to import `mempool` from `app.routers` and register `app.include_router(mempool.router)`.

- [ ] **Step 5: Add the RPC error regression test**

Append:

```python
from app.bitcoin_rpc import BitcoinRpcError


def test_mempool_rpc_error_uses_existing_error_handler(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_raw_mempool(self, verbose: bool = True):
            raise BitcoinRpcError("Bitcoin Core unavailable", status_code=502)

    monkeypatch.setattr("app.services.mempool.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/mempool")

    assert response.status_code == 502
    assert response.json() == {"detail": "Bitcoin Core unavailable"}
```

- [ ] **Step 6: Run focused and full backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mempool.py -v
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit the backend slice**

```powershell
git add backend/app/bitcoin_rpc.py backend/app/schemas.py backend/app/services/mempool.py backend/app/routers/mempool.py backend/app/main.py backend/tests/test_mempool.py
git commit -m "feat: expose mempool API"
```

### Task 3: Add frontend mempool types, API client, and presentational component

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/components/MempoolView.tsx`

**Interfaces:**
- Consumes: `GET /mempool`.
- Produces: `MempoolTransaction`, `MempoolSummary`, `getMempool(): Promise<MempoolSummary>`, and a presentational `MempoolView` component.

- [ ] **Step 1: Add TypeScript types and API function**

Append to `frontend/src/types.ts`:

```typescript
export type MempoolTransaction = {
  txid: string;
  wtxid: string | null;
  vsize: number;
  weight: number;
  fee_btc: string;
  fee_sats: number;
  fee_rate_sat_vb: string | null;
  time: number | null;
  entry_height: number | null;
  confirmations: number;
  from_wallet: string | null;
  to_wallet: string | null;
  to_address: string | null;
  status: "pending";
  ancestor_count: number;
  descendant_count: number;
  depends: string[];
  spent_by: string[];
  replaceable: boolean;
  unbroadcast: boolean;
  output_addresses: string[];
};

export type MempoolSummary = {
  transaction_count: number;
  total_vsize: number;
  total_fee_btc: string;
  total_fee_sats: number;
  transactions: MempoolTransaction[];
};
```

Update the import in `frontend/src/api.ts` and add:

```typescript
export function getMempool(): Promise<MempoolSummary> {
  return request<MempoolSummary>("/mempool");
}
```

- [ ] **Step 2: Create the presentational component**

Create `frontend/src/components/MempoolView.tsx` with:

```typescript
type Props = {
  summary: MempoolSummary | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
};
```

The component must render:

- a `section` with class `panel mempool-view`;
- heading `Mempool View` and a `Refresh` button;
- summary values for transaction count, total vsize, total fee BTC, and total fee sats;
- a loading message, error message, and empty state;
- a responsive table for populated data with shortened txid, `from_wallet -> to_wallet`, status, fee, fee rate, vsize, time, ancestor/descendant counts, and `RBF`/`No RBF`.

Use `Unknown` for null wallet labels, `Not available` for null fee rate, and `title={tx.txid}` on the shortened txid. Render `to_address` below the direction only when it is non-null. Keep the txid as text for now; do not invent a transaction-detail route before that feature is implemented.

- [ ] **Step 3: Build the frontend**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 4: Commit the component slice**

```powershell
git add frontend/src/types.ts frontend/src/api.ts frontend/src/components/MempoolView.tsx
git commit -m "feat: add mempool view component"
```

### Task 4: Integrate global refresh flow and responsive styling

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `getMempool`, `MempoolSummary`, and `MempoolView`.
- Produces: global mempool data that refreshes independently from selected-wallet data.

- [ ] **Step 1: Add mempool state and loader in `App.tsx`**

Update imports:

```typescript
import { getMempool } from "./api";
import { MempoolView } from "./components/MempoolView";
import type { MempoolSummary } from "./types";
```

Add state:

```typescript
const [mempoolSummary, setMempoolSummary] = useState<MempoolSummary | null>(null);
const [mempoolLoading, setMempoolLoading] = useState(false);
const [mempoolError, setMempoolError] = useState("");
```

Add:

```typescript
async function refreshMempool() {
  setMempoolLoading(true);
  setMempoolError("");
  try {
    setMempoolSummary(await getMempool());
  } catch (error) {
    setMempoolError((error as Error).message);
  } finally {
    setMempoolLoading(false);
  }
}
```

Call `refreshMempool()` during initial setup after the default users and first wallet refresh. Call it after `refresh()` in `handleSend`, `handleFaucet`, and `handleMine`. Do not call it from the wallet-switch callback because the mempool is global and should not reload three times while switching wallets.

- [ ] **Step 2: Render the view below the UTXO Viewer**

Place after the UTXO Viewer integration from the UTXO plan:

```tsx
<MempoolView
  summary={mempoolSummary}
  loading={mempoolLoading}
  error={mempoolError}
  onRefresh={() => refreshMempool().catch(() => undefined)}
/>
```

If the UTXO Viewer has not yet been implemented in the working tree, place Mempool View after `TransactionHistory` and keep the component independent; do not duplicate or remove UTXO code.

- [ ] **Step 3: Add styles for summary and horizontally scrollable table**

Add to `frontend/src/styles.css`:

```css
.mempool-view {
  margin-top: 16px;
}

.mempool-summary {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 16px 0;
}

.mempool-table-wrap {
  overflow-x: auto;
}

.mempool-table {
  border-collapse: collapse;
  min-width: 940px;
  width: 100%;
}

.mempool-table th,
.mempool-table td {
  border-top: 1px solid #edf1f5;
  padding: 10px 8px;
  text-align: left;
  vertical-align: top;
}

.mempool-txid,
.mempool-address {
  max-width: 220px;
  overflow-wrap: anywhere;
}

.mempool-pending {
  color: #b45309;
  font-weight: 700;
}

@media (max-width: 720px) {
  .mempool-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

Reuse existing `.panel`, `.muted`, `small`, and button styles. Keep the table inside one panel and use horizontal scrolling on narrow screens rather than allowing columns to overlap.

- [ ] **Step 4: Run the production build**

Run:

```powershell
npm.cmd run build
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 5: Commit the integration slice**

```powershell
git add frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat: refresh mempool with wallet actions"
```

### Task 5: Document the mempool demo and complete verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `GET /mempool` and the existing send/mine demo flow.
- Produces: reproducible API commands, UI instructions, and final acceptance evidence.

- [ ] **Step 1: Add the API example**

After the existing transaction and UTXO API examples in `README.md`, add:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/mempool
```

Document these response fields: `transaction_count`, `total_vsize`, `total_fee_btc`, `total_fee_sats`, `txid`, `fee_rate_sat_vb`, `time`, `ancestor_count`, `descendant_count`, `from_wallet`, `to_wallet`, and `status`.

- [ ] **Step 2: Extend the web demo flow**

Add a short flow:

```text
1. Select Alice and ensure she has confirmed BTC.
2. Select Bob, generate a new address, and copy it.
3. Select Alice, send 2 BTC to Bob, and do not mine yet.
4. Open Mempool View and observe the pending transaction, fee, fee rate, vsize, and Alice -> Bob labels.
5. Click Mine 1 block.
6. Refresh Mempool View and observe that the transaction is gone.
7. Open transaction history and observe the same txid with confirmed status.
```

Explain that Mempool View is node-wide and that transactions without app metadata may show `Unknown` wallet labels.

- [ ] **Step 3: Run the full verification commands**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
cd ..\frontend
npm.cmd run build
cd ..
git diff --check
git status --short --branch
```

Expected:

- all backend tests PASS;
- frontend production build PASS;
- `git diff --check` produces no whitespace errors;
- the only unrelated untracked path remains `backend/package-lock.json`.

- [ ] **Step 4: Perform a manual regtest smoke test**

With Bitcoin Core, backend, and frontend running:

1. Open `http://127.0.0.1:5173`.
2. Confirm Mempool View starts with an empty state or current pending transactions.
3. Send Alice-to-Bob without mining and verify a pending row appears.
4. Confirm the fee and fee rate are displayed as non-empty values.
5. Mine one block and click Refresh.
6. Verify the pending row disappears and transaction history shows confirmation.
7. Stop Bitcoin Core temporarily, refresh, and verify the UI shows an error instead of crashing.

- [ ] **Step 5: Commit documentation**

```powershell
git add README.md
git commit -m "docs: document mempool view usage"
```

## Final Acceptance Checklist

- [ ] `GET /mempool` returns current node-wide mempool data.
- [ ] Verbose mempool and decoded transaction RPC calls are covered by tests.
- [ ] Known app transactions show wallet relationship metadata.
- [ ] Unknown transactions remain valid with nullable wallet labels.
- [ ] Fees and fee rates use exact satoshi/Decimal calculations.
- [ ] Empty mempool renders a clean empty state.
- [ ] Send, faucet, mine, initial load, and manual refresh update the view.
- [ ] Mining removes confirmed transactions from the mempool view.
- [ ] Backend tests and frontend build pass.
- [ ] README includes API and web demo instructions.
