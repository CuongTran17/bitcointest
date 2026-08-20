# UTXO Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a wallet-scoped UTXO Viewer that reads the selected wallet's spendable and pending outputs from Bitcoin Core and displays exact BTC/satoshi totals in the existing dashboard.

**Architecture:** Bitcoin Core remains the source of truth through wallet-scoped `listunspent`. The backend adds a thin RPC wrapper, typed response models, a service that converts BTC amounts to satoshis and calculates summary counts, and a dedicated `/utxos/{wallet_name}` router. The frontend keeps data loading in `App.tsx` and uses a presentational `UtxoViewer` component that follows the existing selected-wallet and refresh flows.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy test fixtures, pytest, React, TypeScript, Vite, plain CSS, Bitcoin Core regtest RPC.

**Spec:** `docs/superpowers/specs/2026-08-20-utxo-viewer-design.md`

## Global Constraints

- Keep Bitcoin Core as the only source of current UTXO state; do not add a SQLite UTXO table.
- Use `listunspent` with `minconf=0` and `maxconf=9999999` so pending and confirmed outputs are visible.
- Use `Decimal` for BTC parsing and integer satoshis for application arithmetic; never use floating point in backend calculations.
- Keep `wallet_name` dynamic; do not hardcode Alice, Bob, or Miner in the endpoint or component.
- Return an empty successful summary for a wallet with no UTXOs.
- Preserve the pre-existing untracked `backend/package-lock.json`; do not add, delete, or modify it.
- Do not add dependencies.

---

### Task 1: Add RPC and UTXO response models

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_utxos.py`

**Interfaces:**
- Consumes: `BitcoinRpcClient.ensure_wallet_loaded(wallet)` and `BitcoinRpcClient.call(method, params, wallet)`.
- Produces: `BitcoinRpcClient.list_unspent(wallet: str, min_conf: int = 0, max_conf: int = 9999999) -> list[dict[str, Any]]`.
- Produces: `UtxoRead` and `UtxoSummaryRead` Pydantic models for the API and frontend.

- [ ] **Step 1: Write the failing RPC test**

Add this test to `backend/tests/test_utxos.py`:

```python
from app.bitcoin_rpc import BitcoinRpcClient


def test_list_unspent_uses_wallet_and_confirmation_range(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return [{"txid": "tx1", "vout": 0, "amount": "1.25000000", "confirmations": 0}]

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)
    monkeypatch.setattr(BitcoinRpcClient, "ensure_wallet_loaded", lambda self, wallet: None)

    result = BitcoinRpcClient().list_unspent("alice")

    assert result[0]["txid"] == "tx1"
    assert calls == [("listunspent", [0, 9999999, [], True], "alice")]
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_utxos.py::test_list_unspent_uses_wallet_and_confirmation_range -v
```

Expected: FAIL because `BitcoinRpcClient.list_unspent` does not exist.

- [ ] **Step 3: Implement the minimal RPC method**

Add this method to `BitcoinRpcClient` in `backend/app/bitcoin_rpc.py`:

```python
def list_unspent(
    self,
    wallet: str,
    min_conf: int = 0,
    max_conf: int = 9999999,
) -> list[dict[str, Any]]:
    self.ensure_wallet_loaded(wallet)
    return self.call(
        "listunspent",
        [min_conf, max_conf, [], True],
        wallet=wallet,
    )
```

- [ ] **Step 4: Add typed UTXO schemas**

Append to `backend/app/schemas.py`:

```python
class UtxoRead(BaseModel):
    txid: str
    vout: int
    address: str | None = None
    amount_btc: str
    amount_sats: int
    confirmations: int
    spendable: bool
    solvable: bool
    safe: bool


class UtxoSummaryRead(BaseModel):
    wallet_name: str
    utxo_count: int
    confirmed_count: int
    unconfirmed_count: int
    total_amount_btc: str
    total_amount_sats: int
    utxos: list[UtxoRead]
```

- [ ] **Step 5: Run the RPC test and the existing backend suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_utxos.py::test_list_unspent_uses_wallet_and_confirmation_range tests/test_health.py tests/test_wallets.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the RPC and schema slice**

```powershell
git add backend/app/bitcoin_rpc.py backend/app/schemas.py backend/tests/test_utxos.py
git commit -m "feat: add wallet UTXO RPC models"
```

### Task 2: Implement UTXO service and API endpoint

**Files:**
- Create: `backend/app/services/utxos.py`
- Create: `backend/app/routers/utxos.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_utxos.py`

**Interfaces:**
- Consumes: `BitcoinRpcClient.list_unspent`, `btc_to_sats`, `UtxoRead`, and `UtxoSummaryRead`.
- Produces: `list_utxos(wallet_name: str) -> UtxoSummaryRead`.
- Produces: `GET /utxos/{wallet_name}` with response model `UtxoSummaryRead`.

- [ ] **Step 1: Write failing service and endpoint tests**

Append to `backend/tests/test_utxos.py`:

```python
from decimal import Decimal

from fastapi.testclient import TestClient


def test_get_utxos_returns_exact_summary_and_sorted_outputs(client: TestClient, monkeypatch):
    class FakeRpc:
        def list_unspent(self, wallet: str, min_conf: int = 0, max_conf: int = 9999999):
            assert wallet == "alice"
            assert (min_conf, max_conf) == (0, 9999999)
            return [
                {
                    "txid": "pending-small",
                    "vout": 1,
                    "amount": "0.50000001",
                    "confirmations": 0,
                    "spendable": True,
                    "solvable": True,
                    "safe": True,
                },
                {
                    "txid": "confirmed-large",
                    "vout": 0,
                    "address": "bcrt1qalice",
                    "amount": "2.50000000",
                    "confirmations": 1,
                    "spendable": True,
                    "solvable": True,
                    "safe": True,
                },
                {
                    "txid": "confirmed-small",
                    "vout": 0,
                    "address": "bcrt1qother",
                    "amount": "1.00000000",
                    "confirmations": 1,
                    "spendable": False,
                    "solvable": True,
                    "safe": False,
                },
            ]

    monkeypatch.setattr("app.services.utxos.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/utxos/alice")

    assert response.status_code == 200
    assert response.json() == {
        "wallet_name": "alice",
        "utxo_count": 3,
        "confirmed_count": 2,
        "unconfirmed_count": 1,
        "total_amount_btc": "4.00000001",
        "total_amount_sats": 400000001,
        "utxos": [
            {
                "txid": "confirmed-large",
                "vout": 0,
                "address": "bcrt1qalice",
                "amount_btc": "2.50000000",
                "amount_sats": 250000000,
                "confirmations": 1,
                "spendable": True,
                "solvable": True,
                "safe": True,
            },
            {
                "txid": "confirmed-small",
                "vout": 0,
                "address": "bcrt1qother",
                "amount_btc": "1.00000000",
                "amount_sats": 100000000,
                "confirmations": 1,
                "spendable": False,
                "solvable": True,
                "safe": False,
            },
            {
                "txid": "pending-small",
                "vout": 1,
                "address": None,
                "amount_btc": "0.50000001",
                "amount_sats": 50000001,
                "confirmations": 0,
                "spendable": True,
                "solvable": True,
                "safe": True,
            },
        ],
    }


def test_get_utxos_returns_empty_summary(client: TestClient, monkeypatch):
    class FakeRpc:
        def list_unspent(self, wallet: str, min_conf: int = 0, max_conf: int = 9999999):
            return []

    monkeypatch.setattr("app.services.utxos.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/utxos/bob")

    assert response.status_code == 200
    assert response.json() == {
        "wallet_name": "bob",
        "utxo_count": 0,
        "confirmed_count": 0,
        "unconfirmed_count": 0,
        "total_amount_btc": "0.00000000",
        "total_amount_sats": 0,
        "utxos": [],
    }
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_utxos.py::test_get_utxos_returns_exact_summary_and_sorted_outputs tests/test_utxos.py::test_get_utxos_returns_empty_summary -v
```

Expected: FAIL because the service and router are not registered.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/utxos.py`:

```python
from decimal import Decimal

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.schemas import UtxoRead, UtxoSummaryRead


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def list_utxos(wallet_name: str) -> UtxoSummaryRead:
    rows = BitcoinRpcClient().list_unspent(wallet_name, min_conf=0, max_conf=9999999)
    normalized = []
    for row in rows:
        amount = Decimal(str(row["amount"]))
        normalized.append(
            UtxoRead(
                txid=row["txid"],
                vout=int(row["vout"]),
                address=row.get("address"),
                amount_btc=format_btc(amount),
                amount_sats=btc_to_sats(amount),
                confirmations=int(row.get("confirmations", 0)),
                spendable=bool(row.get("spendable", False)),
                solvable=bool(row.get("solvable", False)),
                safe=bool(row.get("safe", False)),
            )
        )

    normalized.sort(
        key=lambda item: (
            item.confirmations == 0,
            -item.amount_sats,
            item.txid,
            item.vout,
        )
    )
    confirmed_count = sum(item.confirmations > 0 for item in normalized)
    total_sats = sum(item.amount_sats for item in normalized)
    return UtxoSummaryRead(
        wallet_name=wallet_name,
        utxo_count=len(normalized),
        confirmed_count=confirmed_count,
        unconfirmed_count=len(normalized) - confirmed_count,
        total_amount_btc=format_btc(Decimal(total_sats) / Decimal("100000000")),
        total_amount_sats=total_sats,
        utxos=normalized,
    )
```

- [ ] **Step 4: Add the router and register it**

Create `backend/app/routers/utxos.py`:

```python
from fastapi import APIRouter

from app.schemas import UtxoSummaryRead
from app.services import utxos as utxo_service

router = APIRouter(prefix="/utxos", tags=["utxos"])


@router.get("/{wallet_name}", response_model=UtxoSummaryRead)
def get_utxos(wallet_name: str):
    return utxo_service.list_utxos(wallet_name)
```

Modify `backend/app/main.py` to import `utxos` from `app.routers` and call `app.include_router(utxos.router)` alongside the existing routers.

- [ ] **Step 5: Add the unloaded-wallet regression test**

Append:

```python
from app.bitcoin_rpc import BitcoinRpcError


def test_get_utxos_returns_404_for_unloaded_wallet(client: TestClient, monkeypatch):
    class FakeRpc:
        def list_unspent(self, wallet: str, min_conf: int = 0, max_conf: int = 9999999):
            raise BitcoinRpcError("Bitcoin wallet 'ghost' is not loaded", status_code=404)

    monkeypatch.setattr("app.services.utxos.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/utxos/ghost")

    assert response.status_code == 404
```

- [ ] **Step 6: Run the focused and full backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_utxos.py -v
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit the backend slice**

```powershell
git add backend/app/bitcoin_rpc.py backend/app/schemas.py backend/app/services/utxos.py backend/app/routers/utxos.py backend/app/main.py backend/tests/test_utxos.py
git commit -m "feat: expose wallet UTXO endpoint"
```

### Task 3: Add frontend UTXO types, API client, and viewer component

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/components/UtxoViewer.tsx`

**Interfaces:**
- Consumes: `GET /utxos/{wallet_name}`.
- Produces: `Utxo`, `UtxoSummary`, `getUtxos(walletName: string): Promise<UtxoSummary>`, and a presentational `UtxoViewer` component.

- [ ] **Step 1: Add TypeScript types and API function**

Add to `frontend/src/types.ts`:

```typescript
export type Utxo = {
  txid: string;
  vout: number;
  address: string | null;
  amount_btc: string;
  amount_sats: number;
  confirmations: number;
  spendable: boolean;
  solvable: boolean;
  safe: boolean;
};

export type UtxoSummary = {
  wallet_name: string;
  utxo_count: number;
  confirmed_count: number;
  unconfirmed_count: number;
  total_amount_btc: string;
  total_amount_sats: number;
  utxos: Utxo[];
};
```

Update the import in `frontend/src/api.ts` and add:

```typescript
export function getUtxos(walletName: string): Promise<UtxoSummary> {
  return request<UtxoSummary>(`/utxos/${walletName}`);
}
```

- [ ] **Step 2: Create the viewer component**

Create `frontend/src/components/UtxoViewer.tsx` with props:

```typescript
type Props = {
  walletName: string;
  summary: UtxoSummary | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
};
```

Render a `section` with heading `UTXO Viewer`, the selected wallet name, a refresh button, summary values, and one row per UTXO. Use a `shortTxid` helper that shows the first 8 and last 6 characters, and display `No address` when `address === null`. Display status labels using only existing data: `confirmed` when `confirmations > 0`, otherwise `pending`; display `spendable` or `watch-only` from the boolean.

The component must render these states:

```tsx
{loading && <p>Loading UTXOs...</p>}
{!loading && error && <p className="error">{error}</p>}
{!loading && !error && summary && summary.utxos.length === 0 && <p>No unspent outputs.</p>}
{!loading && !error && summary && summary.utxos.length > 0 && (
  <div className="utxo-table-wrap">...</div>
)}
```

Keep the component presentational: it must not call `fetch` directly.

- [ ] **Step 3: Build the frontend to verify types fail or pass cleanly**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: PASS after the type imports and component JSX are valid. If TypeScript reports missing imports, fix only the new UTXO types/API references.

- [ ] **Step 4: Commit the frontend component slice**

```powershell
git add frontend/src/types.ts frontend/src/api.ts frontend/src/components/UtxoViewer.tsx
git commit -m "feat: add UTXO viewer component"
```

### Task 4: Integrate selected-wallet refresh flow and responsive styling

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `getUtxos`, `UtxoSummary`, and `UtxoViewer`.
- Produces: selected-wallet UTXO data that refreshes after wallet selection, faucet, send, mine, and manual refresh.

- [ ] **Step 1: Add UTXO state and loading helper in App**

Update imports in `frontend/src/App.tsx`:

```typescript
import { getUtxos } from "./api";
import { UtxoViewer } from "./components/UtxoViewer";
import type { UtxoSummary } from "./types";
```

Add state:

```typescript
const [utxoSummary, setUtxoSummary] = useState<UtxoSummary | null>(null);
const [utxoLoading, setUtxoLoading] = useState(false);
const [utxoError, setUtxoError] = useState("");
```

Add:

```typescript
async function refreshUtxos(walletName = selectedWallet) {
  setUtxoLoading(true);
  setUtxoError("");
  try {
    setUtxoSummary(await getUtxos(walletName));
  } catch (error) {
    setUtxoError((error as Error).message);
  } finally {
    setUtxoLoading(false);
  }
}
```

Call `refreshUtxos(walletName)` in the selected-wallet callback and call `refreshUtxos()` after `refresh()` in `handleSend`, `handleFaucet`, and `handleMine`. Call it during initial setup after `refresh("alice")`. Keep the selected wallet argument explicit so a quick wallet switch cannot load one wallet's UTXOs into another wallet's view.

- [ ] **Step 2: Render the viewer**

Place this after `<TransactionHistory transactions={transactions} />`:

```tsx
<UtxoViewer
  walletName={selectedWallet}
  summary={utxoSummary}
  loading={utxoLoading}
  error={utxoError}
  onRefresh={() => refreshUtxos().catch(() => undefined)}
/>
```

- [ ] **Step 3: Add responsive UTXO styles**

Add styles in `frontend/src/styles.css` for:

```css
.utxo-viewer {
  margin-top: 16px;
}

.utxo-summary {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.utxo-table-wrap {
  overflow-x: auto;
}

.utxo-table {
  border-collapse: collapse;
  min-width: 760px;
  width: 100%;
}

.utxo-table th,
.utxo-table td {
  border-top: 1px solid #edf1f5;
  padding: 10px 8px;
  text-align: left;
  vertical-align: top;
}

.utxo-address,
.utxo-txid {
  max-width: 220px;
  overflow-wrap: anywhere;
}

.error {
  color: #b42318;
}

@media (max-width: 720px) {
  .utxo-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

Use existing button, panel, muted, and code styles where possible. Do not add a new visual dependency or a second card nested inside the viewer panel.

- [ ] **Step 4: Run the production build**

Run:

```powershell
npm.cmd run build
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 5: Commit the integration slice**

```powershell
git add frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat: integrate wallet UTXO refresh flow"
```

### Task 5: Document the UTXO demo and complete verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the shipped `GET /utxos/{wallet_name}` endpoint and existing web demo flow.
- Produces: reproducible PowerShell commands and acceptance evidence for the UTXO Viewer.

- [ ] **Step 1: Add API documentation**

After the existing transaction history API examples in `README.md`, add:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/utxos/alice
Invoke-RestMethod http://127.0.0.1:8000/utxos/bob
```

Document the important response fields:

```json
{
  "wallet_name": "bob",
  "utxo_count": 1,
  "confirmed_count": 1,
  "unconfirmed_count": 0,
  "total_amount_btc": "2.00000000",
  "total_amount_sats": 200000000
}
```

Explain that the viewer includes pending outputs with zero confirmations, and that a wallet with no UTXOs returns zero totals. Mention that block height/hash are intentionally not part of this view because `listunspent` supplies confirmations rather than stable block metadata.

- [ ] **Step 2: Extend the web demo flow**

Add to the numbered demo flow:

```text
14. Select Bob and inspect UTXO Viewer after the transfer is confirmed.
15. Observe the total amount, satoshi value, txid/vout, confirmations, address, and spendable state.
16. Select Alice and compare that her change output appears as a different UTXO.
17. Click Refresh after sending or mining to reload the current wallet UTXO set.
```

- [ ] **Step 3: Run all verification commands**

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
2. Select Alice and verify the viewer loads.
3. Click `Faucet 10 BTC`; verify Alice's UTXO total changes.
4. Select Bob, generate an address, and send 2 BTC from Alice to Bob.
5. Select Bob before mining; verify a pending UTXO with zero confirmations is visible.
6. Mine one block; click Refresh; verify the same UTXO is confirmed.
7. Select Miner and verify its UTXOs are different from Bob's.

- [ ] **Step 5: Commit the documentation and verification update**

```powershell
git add README.md
git commit -m "docs: document UTXO viewer usage"
```

## Final Acceptance Checklist

- [ ] `GET /utxos/{wallet_name}` works for any loaded wallet name.
- [ ] Unloaded wallets return 404 through the existing RPC error handling.
- [ ] Pending and confirmed outputs are both returned.
- [ ] BTC and satoshi totals are exact and consistent.
- [ ] Empty wallets render a zero-value empty state.
- [ ] The selected-wallet switch refreshes the UTXO set.
- [ ] Faucet, send, and mine actions refresh the UTXO set.
- [ ] The frontend remains usable on narrow screens.
- [ ] Backend tests and frontend build pass.
- [ ] README includes setup/demo/API instructions.
