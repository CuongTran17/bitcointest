# Transaction Detail Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a click-to-open transaction detail view that explains a selected Bitcoin transaction with decoded raw transaction data, wallet relationship metadata, inputs, outputs, confirmations, block data, and raw JSON.

**Architecture:** Bitcoin Core remains the source of truth for decoded transaction data via `getrawtransaction <txid> true`. SQLite metadata from `app_transactions` and `wallet_addresses` is merged into the detail response so the UI can show readable local wallet labels where known. The frontend keeps the existing single-page dashboard and opens a detail panel when the user selects a transaction from history.

**Tech Stack:** Python 3.14, FastAPI, Pydantic, SQLAlchemy, SQLite, pytest, React, Vite, TypeScript, Bitcoin Core v31.1 regtest.

**Spec:** Requirements approved in chat on 2026-08-20: `GET /transactions/detail/{txid}`, click from transaction history, show `from_wallet -> to_wallet`, status, confirmations, block data, vin/vout, locally recognized output wallets, and raw JSON toggle. Fee may be `null` when Bitcoin Core does not provide it directly.

## Global Constraints

- Keep Bitcoin Core as the source of truth for decoded transaction data, confirmations, block hash, block time, size, vsize, weight, inputs, and outputs.
- Keep SQLite limited to app metadata: local address ownership and app-created transfer relationships.
- Do not calculate or fake wallet balances in SQLite.
- Keep the existing transaction history endpoint backward-compatible.
- Keep the frontend as one dashboard screen; use an inline detail panel instead of adding routing.
- Use integer satoshis in backend application logic and formatted BTC strings in API responses.
- Unknown local wallet relationships must remain valid and render as `Unknown address`.
- Follow the existing FastAPI router/service/test style and React component/style conventions.

---

### Task 1: Add Bitcoin Core Raw Transaction RPC

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Create: `backend/tests/test_bitcoin_rpc.py`

**Interfaces:**
- Produces `BitcoinRpcClient.get_raw_transaction(txid: str, verbose: bool = True) -> dict[str, Any]`.
- Calls Bitcoin Core RPC method `getrawtransaction` with params `[txid, True]` by default.

- [ ] **Step 1: Write the failing RPC unit test**

Create `backend/tests/test_bitcoin_rpc.py`:

```python
from app.bitcoin_rpc import BitcoinRpcClient


def test_get_raw_transaction_calls_verbose_rpc(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"txid": "tx1", "vin": [], "vout": []}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_raw_transaction("tx1")

    assert result == {"txid": "tx1", "vin": [], "vout": []}
    assert calls == [("getrawtransaction", ["tx1", True], None)]
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_bitcoin_rpc.py -v
```

Expected: FAIL with `AttributeError` because `get_raw_transaction` does not exist.

- [ ] **Step 3: Implement the minimal RPC method**

Modify `backend/app/bitcoin_rpc.py`:

```python
    def get_raw_transaction(self, txid: str, verbose: bool = True) -> dict[str, Any]:
        return self.call("getrawtransaction", [txid, verbose])
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_bitcoin_rpc.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/bitcoin_rpc.py backend/tests/test_bitcoin_rpc.py
git commit -m "feat: add raw transaction rpc"
```

---

### Task 2: Add Transaction Detail Schemas And Service

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/transactions.py`
- Create: `backend/tests/test_transaction_detail.py`

**Interfaces:**
- Produces `TransactionInputRead(txid: str | None, vout: int | None, coinbase: str | None, sequence: int | None)`.
- Produces `TransactionOutputRead(n: int, value_btc: str, value_sats: int, address: str | None, wallet_name: str | None, script_type: str | None)`.
- Produces `TransactionDetailRead` with:
  - `txid: str`
  - `from_wallet: str | None`
  - `to_wallet: str | None`
  - `to_address: str | None`
  - `amount_btc: str | None`
  - `amount_sats: int | None`
  - `confirmations: int`
  - `status: str`
  - `blockhash: str | None`
  - `blocktime: int | None`
  - `time: int | None`
  - `size: int | None`
  - `vsize: int | None`
  - `weight: int | None`
  - `fee_btc: str | None`
  - `fee_sats: int | None`
  - `inputs: list[TransactionInputRead]`
  - `outputs: list[TransactionOutputRead]`
  - `raw: dict`
- Produces `get_transaction_detail(txid: str, db: Session) -> TransactionDetailRead`.

- [ ] **Step 1: Write the failing detail service test**

Create `backend/tests/test_transaction_detail.py`:

```python
from decimal import Decimal

from app.models import AppTransaction, WalletAddress


def test_get_transaction_detail_merges_raw_transaction_with_app_metadata(client, monkeypatch):
    class FakeSendRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            return "tx1"

    class FakeRawRpc:
        def get_raw_transaction(self, txid: str, verbose: bool = True):
            assert txid == "tx1"
            assert verbose is True
            return {
                "txid": "tx1",
                "confirmations": 1,
                "blockhash": "blockhash1",
                "blocktime": 1787030000,
                "time": 1787030000,
                "size": 225,
                "vsize": 144,
                "weight": 573,
                "vin": [{"txid": "prevtx", "vout": 0, "sequence": 4294967295}],
                "vout": [
                    {
                        "n": 0,
                        "value": 2.0,
                        "scriptPubKey": {
                            "type": "witness_v0_keyhash",
                            "address": "bcrt1qbobaddress",
                        },
                    },
                    {
                        "n": 1,
                        "value": 7.9999859,
                        "scriptPubKey": {
                            "type": "witness_v0_keyhash",
                            "address": "bcrt1qchangeaddress",
                        },
                    },
                ],
            }

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeSendRpc())
    client.post(
        "/transactions/send",
        json={"from_wallet": "alice", "to_address": "bcrt1qbobaddress", "amount_btc": "2.00000000"},
    )

    from app.db import get_db

    db = next(client.app.dependency_overrides[get_db]())
    db.add(WalletAddress(address="bcrt1qbobaddress", wallet_name="bob"))
    db.commit()
    db.close()

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRawRpc())

    response = client.get("/transactions/detail/tx1")

    assert response.status_code == 200
    body = response.json()
    assert body["txid"] == "tx1"
    assert body["from_wallet"] == "alice"
    assert body["to_wallet"] == "bob"
    assert body["to_address"] == "bcrt1qbobaddress"
    assert body["amount_btc"] == "2.00000000"
    assert body["amount_sats"] == 200000000
    assert body["status"] == "confirmed"
    assert body["confirmations"] == 1
    assert body["blockhash"] == "blockhash1"
    assert body["size"] == 225
    assert body["vsize"] == 144
    assert body["weight"] == 573
    assert body["fee_btc"] is None
    assert body["fee_sats"] is None
    assert body["inputs"] == [{"txid": "prevtx", "vout": 0, "coinbase": None, "sequence": 4294967295}]
    assert body["outputs"][0] == {
        "n": 0,
        "value_btc": "2.00000000",
        "value_sats": 200000000,
        "address": "bcrt1qbobaddress",
        "wallet_name": "bob",
        "script_type": "witness_v0_keyhash",
    }
    assert body["raw"]["txid"] == "tx1"
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_transaction_detail.py -v
```

Expected: FAIL because `GET /transactions/detail/{txid}` and detail schemas do not exist.

- [ ] **Step 3: Add schema classes**

Modify `backend/app/schemas.py`:

```python
from typing import Any
```

Add after `TransactionRead`:

```python
class TransactionInputRead(BaseModel):
    txid: str | None = None
    vout: int | None = None
    coinbase: str | None = None
    sequence: int | None = None


class TransactionOutputRead(BaseModel):
    n: int
    value_btc: str
    value_sats: int
    address: str | None = None
    wallet_name: str | None = None
    script_type: str | None = None


class TransactionDetailRead(BaseModel):
    txid: str
    from_wallet: str | None = None
    to_wallet: str | None = None
    to_address: str | None = None
    amount_btc: str | None = None
    amount_sats: int | None = None
    confirmations: int
    status: str
    blockhash: str | None = None
    blocktime: int | None = None
    time: int | None = None
    size: int | None = None
    vsize: int | None = None
    weight: int | None = None
    fee_btc: str | None = None
    fee_sats: int | None = None
    inputs: list[TransactionInputRead]
    outputs: list[TransactionOutputRead]
    raw: dict[str, Any]
```

- [ ] **Step 4: Implement detail helpers and service**

Modify imports in `backend/app/services/transactions.py`:

```python
from typing import Any
from app.schemas import (
    FaucetRead,
    FaucetRequest,
    SendTransactionRead,
    SendTransactionRequest,
    TransactionDetailRead,
    TransactionInputRead,
    TransactionOutputRead,
    TransactionRead,
)
```

Add helpers:

```python
def read_app_transaction(db: Session, txid: str) -> AppTransaction | None:
    return db.query(AppTransaction).filter(AppTransaction.txid == txid).one_or_none()


def wallet_by_address_map(db: Session, addresses: list[str]) -> dict[str, str]:
    if not addresses:
        return {}
    return {
        row.address: row.wallet_name
        for row in db.query(WalletAddress).filter(WalletAddress.address.in_(addresses)).all()
    }


def output_address(vout: dict[str, Any]) -> str | None:
    script_pub_key = vout.get("scriptPubKey") or {}
    address = script_pub_key.get("address")
    if isinstance(address, str):
        return address
    addresses = script_pub_key.get("addresses")
    if isinstance(addresses, list) and addresses:
        first = addresses[0]
        return first if isinstance(first, str) else None
    return None


def decimal_from_rpc(value: object) -> Decimal:
    return Decimal(str(value))
```

Add service:

```python
def get_transaction_detail(txid: str, db: Session) -> TransactionDetailRead:
    raw = BitcoinRpcClient().get_raw_transaction(txid, verbose=True)
    metadata = read_app_transaction(db, txid)
    output_addresses = [address for address in (output_address(vout) for vout in raw.get("vout", [])) if address]
    wallet_map = wallet_by_address_map(db, output_addresses)

    inputs = [
        TransactionInputRead(
            txid=vin.get("txid"),
            vout=vin.get("vout"),
            coinbase=vin.get("coinbase"),
            sequence=vin.get("sequence"),
        )
        for vin in raw.get("vin", [])
    ]

    outputs = []
    for vout in raw.get("vout", []):
        value = decimal_from_rpc(vout.get("value", "0"))
        address = output_address(vout)
        script_pub_key = vout.get("scriptPubKey") or {}
        outputs.append(
            TransactionOutputRead(
                n=int(vout.get("n", 0)),
                value_btc=format_btc(value),
                value_sats=btc_to_sats(value),
                address=address,
                wallet_name=wallet_map.get(address) if address else None,
                script_type=script_pub_key.get("type"),
            )
        )

    confirmations = int(raw.get("confirmations", 0))
    fee = raw.get("fee")
    fee_decimal = decimal_from_rpc(fee) if fee is not None else None
    amount_btc = format_btc(Decimal(metadata.amount_sats) / Decimal("100000000")) if metadata else None

    return TransactionDetailRead(
        txid=raw["txid"],
        from_wallet=metadata.from_wallet if metadata else None,
        to_wallet=metadata.to_wallet if metadata else None,
        to_address=metadata.to_address if metadata else None,
        amount_btc=amount_btc,
        amount_sats=metadata.amount_sats if metadata else None,
        confirmations=confirmations,
        status="confirmed" if confirmations > 0 else "pending",
        blockhash=raw.get("blockhash"),
        blocktime=raw.get("blocktime"),
        time=raw.get("time"),
        size=raw.get("size"),
        vsize=raw.get("vsize"),
        weight=raw.get("weight"),
        fee_btc=format_btc(fee_decimal) if fee_decimal is not None else None,
        fee_sats=btc_to_sats(fee_decimal) if fee_decimal is not None else None,
        inputs=inputs,
        outputs=outputs,
        raw=raw,
    )
```

- [ ] **Step 5: Run the focused test and verify it passes after the route is added in Task 3**

Do not expect this task to pass until Task 3 registers the API route. Continue to Task 3 immediately.

---

### Task 3: Expose Transaction Detail Endpoint

**Files:**
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/tests/test_transaction_detail.py`

**Interfaces:**
- Produces `GET /transactions/detail/{txid}`.
- Returns `TransactionDetailRead`.
- Route must be declared before `GET /transactions/{wallet_name}` so `detail` is not treated as a wallet name.

- [ ] **Step 1: Add router test assertion for missing raw tx handling**

Extend `backend/tests/test_transaction_detail.py` with:

```python
def test_transaction_detail_propagates_bitcoin_rpc_error(client, monkeypatch):
    from app.bitcoin_rpc import BitcoinRpcError

    class FakeRpc:
        def get_raw_transaction(self, txid: str, verbose: bool = True):
            raise BitcoinRpcError("No such mempool or blockchain transaction", status_code=404)

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/transactions/detail/missingtx")

    assert response.status_code == 404
    assert response.json() == {"detail": "No such mempool or blockchain transaction"}
```

- [ ] **Step 2: Run the focused endpoint tests and verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_transaction_detail.py -v
```

Expected: FAIL because route is not registered.

- [ ] **Step 3: Add endpoint before wallet history route**

Modify `backend/app/routers/transactions.py` imports:

```python
from app.schemas import SendTransactionRead, SendTransactionRequest, TransactionDetailRead, TransactionRead
```

Add before `@router.get("/{wallet_name}")`:

```python
@router.get("/detail/{txid}", response_model=TransactionDetailRead)
def get_transaction_detail(txid: str, db: Session = Depends(get_db)):
    return transaction_service.get_transaction_detail(txid, db)
```

- [ ] **Step 4: Run focused and full backend tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_transaction_detail.py tests/test_transactions.py -v
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/schemas.py backend/app/services/transactions.py backend/app/routers/transactions.py backend/tests/test_transaction_detail.py
git commit -m "feat: add transaction detail api"
```

---

### Task 4: Add Frontend Transaction Detail Contract And API

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`

**Interfaces:**
- Produces `TransactionInput`, `TransactionOutput`, and `TransactionDetail` TypeScript types mirroring the backend response.
- Produces `getTransactionDetail(txid: string): Promise<TransactionDetail>`.

- [ ] **Step 1: Add TypeScript types**

Modify `frontend/src/types.ts` after `Transaction`:

```typescript
export type TransactionInput = {
  txid: string | null;
  vout: number | null;
  coinbase: string | null;
  sequence: number | null;
};

export type TransactionOutput = {
  n: number;
  value_btc: string;
  value_sats: number;
  address: string | null;
  wallet_name: string | null;
  script_type: string | null;
};

export type TransactionDetail = {
  txid: string;
  from_wallet: string | null;
  to_wallet: string | null;
  to_address: string | null;
  amount_btc: string | null;
  amount_sats: number | null;
  confirmations: number;
  status: "pending" | "confirmed";
  blockhash: string | null;
  blocktime: number | null;
  time: number | null;
  size: number | null;
  vsize: number | null;
  weight: number | null;
  fee_btc: string | null;
  fee_sats: number | null;
  inputs: TransactionInput[];
  outputs: TransactionOutput[];
  raw: Record<string, unknown>;
};
```

- [ ] **Step 2: Add API function**

Modify `frontend/src/api.ts` import:

```typescript
import type { Address, Balance, Transaction, TransactionDetail, User } from "./types";
```

Add:

```typescript
export function getTransactionDetail(txid: string): Promise<TransactionDetail> {
  return request<TransactionDetail>(`/transactions/detail/${txid}`);
}
```

- [ ] **Step 3: Build frontend**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat: add transaction detail frontend contract"
```

---

### Task 5: Make Transaction History Selectable

**Files:**
- Modify: `frontend/src/components/TransactionHistory.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- `TransactionHistory` consumes `onSelectTransaction: (txid: string) => void` and `selectedTxid: string | null`.
- Clicking a history row calls `onSelectTransaction(tx.txid)`.
- Selected row has a visible active state.

- [ ] **Step 1: Update component props and click behavior**

Modify `frontend/src/components/TransactionHistory.tsx`:

```typescript
type Props = {
  transactions: Transaction[];
  selectedTxid: string | null;
  onSelectTransaction: (txid: string) => void;
};
```

Change the list item opening tag to:

```tsx
<li
  className={`history-item ${tx.status} ${selectedTxid === tx.txid ? "selected" : ""}`}
  key={`${tx.txid}-${tx.category}-${tx.amount_sats}`}
>
  <button className="history-button" type="button" onClick={() => onSelectTransaction(tx.txid)}>
```

Move the existing row contents inside the button and close `</button>` before `</li>`.

- [ ] **Step 2: Wire App state**

Modify `frontend/src/App.tsx` imports:

```typescript
import { ..., getTransactionDetail, ... } from "./api";
import type { Balance, Transaction, TransactionDetail, User } from "./types";
```

Add state:

```typescript
const [selectedTxid, setSelectedTxid] = useState<string | null>(null);
const [transactionDetail, setTransactionDetail] = useState<TransactionDetail | null>(null);
const [detailLoading, setDetailLoading] = useState(false);
```

Add handler:

```typescript
async function handleSelectTransaction(txid: string) {
  setSelectedTxid(txid);
  setDetailLoading(true);
  try {
    setTransactionDetail(await getTransactionDetail(txid));
  } catch (error) {
    setMessage(error instanceof Error ? error.message : "Failed to load transaction detail");
  } finally {
    setDetailLoading(false);
  }
}
```

Update `TransactionHistory`:

```tsx
<TransactionHistory
  transactions={transactions}
  selectedTxid={selectedTxid}
  onSelectTransaction={handleSelectTransaction}
/>
```

- [ ] **Step 3: Add button styles without changing layout**

Modify `frontend/src/styles.css`:

```css
.history-button {
  align-items: center;
  background: transparent;
  color: inherit;
  display: grid;
  gap: 4px;
  grid-template-columns: 1fr auto;
  padding: 0;
  text-align: left;
  width: 100%;
}

.history-button:hover .direction,
.history-item.selected .direction {
  text-decoration: underline;
}

.history-item.selected {
  background: #f8fafc;
}
```

- [ ] **Step 4: Build frontend**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/App.tsx frontend/src/components/TransactionHistory.tsx frontend/src/styles.css
git commit -m "feat: make transactions selectable"
```

---

### Task 6: Render Transaction Detail Panel

**Files:**
- Create: `frontend/src/components/TransactionDetailPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- `TransactionDetailPanel` consumes:

```typescript
type Props = {
  detail: TransactionDetail | null;
  loading: boolean;
};
```

- Renders nothing when `detail` is `null` and `loading` is false.
- Renders loading copy when `loading` is true.
- Renders wallet direction, status, confirmations, blockhash, time, size/vsize/weight, fee or `Not available`, inputs, outputs, and a collapsible raw JSON section.

- [ ] **Step 1: Create the detail component**

Create `frontend/src/components/TransactionDetailPanel.tsx`:

```tsx
import type { TransactionDetail } from "../types";

type Props = {
  detail: TransactionDetail | null;
  loading: boolean;
};

function walletLabel(walletName: string | null) {
  if (!walletName) {
    return "Unknown address";
  }
  return walletName.charAt(0).toUpperCase() + walletName.slice(1);
}

function shortHash(value: string | null) {
  if (!value) {
    return "Not available";
  }
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 10)}...${value.slice(-8)}`;
}

function formatTime(value: number | null) {
  if (!value) {
    return "Not available";
  }
  return new Date(value * 1000).toLocaleString();
}

export function TransactionDetailPanel({ detail, loading }: Props) {
  if (loading) {
    return (
      <section className="panel transaction-detail">
        <h3>Transaction detail</h3>
        <p className="muted">Loading transaction detail...</p>
      </section>
    );
  }

  if (!detail) {
    return null;
  }

  return (
    <section className="panel transaction-detail">
      <div className="detail-header">
        <div>
          <p className="label">Transaction detail</p>
          <h3>
            {walletLabel(detail.from_wallet)} -&gt; {walletLabel(detail.to_wallet)}
          </h3>
        </div>
        <strong>{detail.amount_btc ?? "Unknown"} BTC</strong>
      </div>

      <dl className="detail-grid">
        <div>
          <dt>Status</dt>
          <dd>{detail.status} · {detail.confirmations} confirmations</dd>
        </div>
        <div>
          <dt>Block</dt>
          <dd title={detail.blockhash ?? undefined}>{shortHash(detail.blockhash)}</dd>
        </div>
        <div>
          <dt>Time</dt>
          <dd>{formatTime(detail.blocktime ?? detail.time)}</dd>
        </div>
        <div>
          <dt>Fee</dt>
          <dd>{detail.fee_btc ? `${detail.fee_btc} BTC` : "Not available"}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{detail.size ?? "?"} bytes · vsize {detail.vsize ?? "?"} · weight {detail.weight ?? "?"}</dd>
        </div>
        <div>
          <dt>Txid</dt>
          <dd title={detail.txid}>{shortHash(detail.txid)}</dd>
        </div>
      </dl>

      <div className="detail-columns">
        <div>
          <h4>Inputs</h4>
          <ul className="detail-list">
            {detail.inputs.map((input, index) => (
              <li key={`${input.txid ?? input.coinbase ?? "input"}-${index}`}>
                {input.coinbase ? (
                  <span>coinbase</span>
                ) : (
                  <span title={input.txid ?? undefined}>{shortHash(input.txid)}:{input.vout ?? "?"}</span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4>Outputs</h4>
          <ul className="detail-list">
            {detail.outputs.map((output) => (
              <li key={output.n}>
                <strong>{output.value_btc} BTC</strong>
                <span>{walletLabel(output.wallet_name)}</span>
                <code>{output.address ?? "No address"}</code>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <details>
        <summary>Raw JSON</summary>
        <pre>{JSON.stringify(detail.raw, null, 2)}</pre>
      </details>
    </section>
  );
}
```

- [ ] **Step 2: Render the panel in App**

Modify `frontend/src/App.tsx`:

```typescript
import { TransactionDetailPanel } from "./components/TransactionDetailPanel";
```

Add below `TransactionHistory`:

```tsx
<TransactionDetailPanel detail={transactionDetail} loading={detailLoading} />
```

- [ ] **Step 3: Add panel styles**

Modify `frontend/src/styles.css`:

```css
.transaction-detail {
  margin-top: 16px;
}

.detail-header,
.detail-columns {
  display: grid;
  gap: 16px;
  grid-template-columns: 1fr 1fr;
}

.detail-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

.detail-grid div,
.detail-list li {
  border-top: 1px solid #edf1f5;
  display: grid;
  gap: 4px;
  padding-top: 10px;
}

dt {
  color: #637083;
  font-size: 13px;
}

dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.detail-list {
  display: grid;
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
}

pre {
  background: #101820;
  border-radius: 6px;
  color: #e8eef5;
  max-height: 360px;
  overflow: auto;
  padding: 12px;
}

@media (max-width: 720px) {
  .detail-header,
  .detail-columns,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 4: Build frontend**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/App.tsx frontend/src/components/TransactionDetailPanel.tsx frontend/src/styles.css
git commit -m "feat: show transaction detail panel"
```

---

### Task 7: Document And Verify Detail Flow

**Files:**
- Modify: `README.md`

**Interfaces:**
- Documentation explains how to click a transaction row and what the detail fields mean.
- Documentation includes the direct API command for `GET /transactions/detail/{txid}`.

- [ ] **Step 1: Add README detail instructions**

Add to the web demo section after the existing transaction history steps:

```markdown
14. Click the transaction row in `Recent transactions`.
15. Review `Inputs`, `Outputs`, `Block`, `Size`, and `Raw JSON`.

The detail panel uses Bitcoin Core `getrawtransaction` data. Wallet names appear only when the app has local metadata for that txid or output address. Fee may show `Not available` for transactions where Bitcoin Core does not return fee directly.
```

Add to API section:

```powershell
$history = Invoke-RestMethod http://127.0.0.1:8000/transactions/alice
$txid = $history[0].txid
Invoke-RestMethod "http://127.0.0.1:8000/transactions/detail/$txid"
```

- [ ] **Step 2: Run full backend tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Build frontend**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build succeeds.

- [ ] **Step 4: Manual regtest check**

With Bitcoin Core, backend, and frontend running:

```text
1. Select Bob and create a new address.
2. Select Alice and send 2 BTC to Bob's address.
3. Click the new history row.
4. Verify the detail panel shows Alice -> Bob, one input, outputs, raw JSON, and pending status.
5. Click Mine 1 block.
6. Click the row again and verify confirmed status, confirmations, and block hash.
```

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs: add transaction detail demo"
```

---

## Final Verification

- [ ] `cd backend; .\.venv\Scripts\python.exe -m pytest -v` passes.
- [ ] `cd frontend; npm.cmd run build` passes.
- [ ] `GET /transactions/detail/{txid}` returns decoded raw transaction data.
- [ ] Detail response includes app metadata for known transactions: `from_wallet`, `to_wallet`, `to_address`, `amount_btc`, and `amount_sats`.
- [ ] Detail response marks transactions as `pending` when confirmations are `0`.
- [ ] Detail response marks transactions as `confirmed` when confirmations are greater than `0`.
- [ ] Outputs include `wallet_name` when the output address is known by the app.
- [ ] Clicking a transaction row opens the detail panel.
- [ ] Raw JSON is visible behind a collapsible section.
- [ ] Unknown fee renders as `Not available`.

## Self-Review

- Spec coverage: The plan covers backend RPC access, detail schemas, API endpoint, metadata merge, frontend contract, selectable history rows, detail panel rendering, README updates, and verification.
- Placeholder scan: all tasks include concrete files, interfaces, code snippets, commands, and expected results.
- Type consistency: backend `TransactionDetailRead` fields match frontend `TransactionDetail`; route `/transactions/detail/{txid}` is declared before `/transactions/{wallet_name}` to avoid path conflicts; nullable wallet and fee fields are consistently represented as `None`/`null`.
