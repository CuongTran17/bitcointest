# Block Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a node-wide Block Explorer that lists recent active-chain blocks, opens block details by height or hash, and displays the transaction ids included in each block.

**Architecture:** Bitcoin Core remains the source of truth through `getblockchaininfo`, `getblockhash`, and `getblock` at verbosity 1. The backend exposes separate list and detail responses without persisting blocks or decoding every transaction. The frontend owns recent-block loading and selected-block detail state independently from the selected wallet, and refreshes the explorer after mining.

**Tech Stack:** FastAPI, Pydantic, pytest, React, TypeScript, Vite, plain CSS, Bitcoin Core regtest RPC.

**Spec:** `docs/superpowers/specs/2026-08-20-block-explorer-design.md`

## Global Constraints

- Read block state directly from Bitcoin Core; do not add a SQLite block/index table.
- Use `getblock` verbosity `1`; transaction detail remains a separate feature.
- Keep the latest-block limit bounded to `1..100`, defaulting to `20`.
- Accept block references only as a non-negative decimal height or a 64-character hexadecimal hash.
- Use integer heights and sizes; do not use floating point for block metadata.
- Return blocks newest first and keep ordering deterministic.
- Do not hardcode Alice, Bob, or Miner into block APIs or UI logic.
- Preserve the pre-existing untracked `backend/package-lock.json`; do not add, delete, or modify it.
- Do not add dependencies.

---

### Task 1: Add block RPC methods and response schemas

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_blocks.py`

**Interfaces:**
- Consumes: `BitcoinRpcClient.call` and existing `get_blockchain_info`.
- Produces: `get_block_hash(height: int) -> str`.
- Produces: `get_block(block_hash: str, verbosity: int = 1) -> dict[str, Any]`.
- Produces: `BlockSummaryRead`, `BlockListRead`, and `BlockDetailRead` schemas.

- [ ] **Step 1: Write failing RPC wrapper tests**

Create `backend/tests/test_blocks.py` with:

```python
import pytest

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError


def test_get_block_hash_calls_height_rpc(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return "0000000000000000000000000000000000000000000000000000000000000001"

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_block_hash(101)

    assert result.endswith("0001")
    assert calls == [("getblockhash", [101], None)]


def test_get_block_calls_metadata_verbosity(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"hash": "block1", "height": 101, "tx": ["tx1"]}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_block("block1")

    assert result["height"] == 101
    assert calls == [("getblock", ["block1", 1], None)]


def test_block_not_found_errors_are_translated_to_404(monkeypatch):
    def fake_call(self, method, params=None, wallet=None):
        raise BitcoinRpcError("{'code': -8, 'message': 'Block height out of range'}")

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    with pytest.raises(BitcoinRpcError) as error:
        BitcoinRpcClient().get_block_hash(999999)

    assert error.value.status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_blocks.py::test_get_block_hash_calls_height_rpc tests/test_blocks.py::test_get_block_calls_metadata_verbosity tests/test_blocks.py::test_block_not_found_errors_are_translated_to_404 -v
```

Expected: FAIL because `get_block_hash` and `get_block` do not exist.

- [ ] **Step 3: Implement the RPC methods**

Add to `BitcoinRpcClient` in `backend/app/bitcoin_rpc.py`:

```python
def get_block_hash(self, height: int) -> str:
    try:
        return self.call("getblockhash", [height])
    except BitcoinRpcError as exc:
        if "Block height out of range" in exc.message:
            raise BitcoinRpcError(exc.message, status_code=404) from exc
        raise


def get_block(self, block_hash: str, verbosity: int = 1) -> dict[str, Any]:
    try:
        return self.call("getblock", [block_hash, verbosity])
    except BitcoinRpcError as exc:
        if "Block not found" in exc.message:
            raise BitcoinRpcError(exc.message, status_code=404) from exc
        raise
```

Keep these calls node-level by omitting the wallet argument. The existing `call` method must remain unchanged: only these block-specific wrappers translate the two Bitcoin Core not-found messages to 404; transport and unrelated RPC errors remain 502.

- [ ] **Step 4: Add block schemas**

Append to `backend/app/schemas.py`:

```python
class BlockSummaryRead(BaseModel):
    height: int
    hash: str
    confirmations: int
    time: int
    size: int
    weight: int
    transaction_count: int
    previous_hash: str | None = None
    next_hash: str | None = None


class BlockListRead(BaseModel):
    chain: str
    tip_height: int
    tip_hash: str
    blocks: list[BlockSummaryRead]


class BlockDetailRead(BlockSummaryRead):
    version: int
    version_hex: str
    merkle_root: str
    median_time: int
    nonce: int
    bits: str
    difficulty: str
    chainwork: str
    transaction_ids: list[str]
```

`difficulty` is a string in the application response so the frontend does not rely on binary floating-point formatting. The service formats the RPC value with a stable decimal representation.

- [ ] **Step 5: Run focused and existing tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_blocks.py::test_get_block_hash_calls_height_rpc tests/test_blocks.py::test_get_block_calls_metadata_verbosity tests/test_blocks.py::test_block_not_found_errors_are_translated_to_404 tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the RPC and schema slice**

```powershell
git add backend/app/bitcoin_rpc.py backend/app/schemas.py backend/tests/test_blocks.py
git commit -m "feat: add block RPC models"
```

### Task 2: Implement block list/detail service and API routes

**Files:**
- Create: `backend/app/services/blocks.py`
- Create: `backend/app/routers/blocks.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_blocks.py`

**Interfaces:**
- Consumes: `get_blockchain_info`, `get_block_hash`, `get_block`, and block schemas.
- Produces: `list_blocks(limit: int = 20) -> BlockListRead`.
- Produces: `get_block_detail(block_ref: str) -> BlockDetailRead`.
- Produces: `GET /blocks?limit=20` and `GET /blocks/{block_ref}`.

- [ ] **Step 1: Write failing list/detail endpoint tests**

Append to `backend/tests/test_blocks.py`:

```python
from fastapi.testclient import TestClient


BLOCK_101 = "0000000000000000000000000000000000000000000000000000000000000101"
BLOCK_100 = "0000000000000000000000000000000000000000000000000000000000000100"


def test_list_blocks_returns_newest_first_with_tip_metadata(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_blockchain_info(self):
            return {"chain": "regtest", "blocks": 101, "bestblockhash": BLOCK_101}

        def get_block_hash(self, height: int):
            return BLOCK_101 if height == 101 else BLOCK_100

        def get_block(self, block_hash: str, verbosity: int = 1):
            height = 101 if block_hash == BLOCK_101 else 100
            return {
                "hash": block_hash,
                "confirmations": 1 if height == 101 else 2,
                "height": height,
                "time": 1787030000 + height,
                "size": 285,
                "weight": 1140,
                "tx": [f"tx-{height}"],
                "previousblockhash": BLOCK_100 if height == 101 else None,
                "nextblockhash": BLOCK_101 if height == 100 else None,
            }

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/blocks?limit=2")

    assert response.status_code == 200
    assert response.json() == {
        "chain": "regtest",
        "tip_height": 101,
        "tip_hash": BLOCK_101,
        "blocks": [
            {
                "height": 101,
                "hash": BLOCK_101,
                "confirmations": 1,
                "time": 1787030101,
                "size": 285,
                "weight": 1140,
                "transaction_count": 1,
                "previous_hash": BLOCK_100,
                "next_hash": None,
            },
            {
                "height": 100,
                "hash": BLOCK_100,
                "confirmations": 2,
                "time": 1787030100,
                "size": 285,
                "weight": 1140,
                "transaction_count": 1,
                "previous_hash": None,
                "next_hash": BLOCK_101,
            },
        ],
    }


def test_block_detail_accepts_height_and_hash(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_block_hash(self, height: int):
            assert height == 101
            return BLOCK_101

        def get_block(self, block_hash: str, verbosity: int = 1):
            assert block_hash == BLOCK_101
            assert verbosity == 1
            return {
                "hash": BLOCK_101,
                "confirmations": 1,
                "height": 101,
                "time": 1787030000,
                "size": 285,
                "weight": 1140,
                "tx": ["coinbase-tx", "transfer-tx"],
                "previousblockhash": BLOCK_100,
                "nextblockhash": None,
                "version": 536870912,
                "versionHex": "20000000",
                "merkleroot": "merkle-root",
                "mediantime": 1787029990,
                "nonce": 42,
                "bits": "207fffff",
                "difficulty": 4.656542373906925e-10,
                "chainwork": "0002",
            }

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    by_height = client.get("/blocks/101")
    by_hash = client.get(f"/blocks/{BLOCK_101}")

    assert by_height.status_code == 200
    assert by_hash.status_code == 200
    assert by_height.json() == by_hash.json()
    assert by_height.json()["transaction_ids"] == ["coinbase-tx", "transfer-tx"]
    assert by_height.json()["difficulty"] == "0.000000000465654237"


def test_block_detail_rejects_invalid_reference(client: TestClient):
    response = client.get("/blocks/not-a-height-or-hash")

    assert response.status_code == 422


def test_block_detail_returns_404_for_missing_block(client: TestClient, monkeypatch):
    from app.bitcoin_rpc import BitcoinRpcError

    class FakeRpc:
        def get_block_hash(self, height: int):
            raise BitcoinRpcError("Block height out of range", status_code=404)

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/blocks/999999")

    assert response.status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_blocks.py::test_list_blocks_returns_newest_first_with_tip_metadata tests/test_blocks.py::test_block_detail_accepts_height_and_hash -v
```

Expected: FAIL because the service and routes are not registered.

- [ ] **Step 3: Implement block normalization and reference parsing**

Create `backend/app/services/blocks.py`:

```python
import re
from decimal import Decimal

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError
from app.schemas import BlockDetailRead, BlockListRead, BlockSummaryRead

BLOCK_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def format_difficulty(value: object) -> str:
    return f"{Decimal(str(value)):.18f}".rstrip("0").rstrip(".") or "0"


def summary_from_raw(raw: dict) -> BlockSummaryRead:
    return BlockSummaryRead(
        height=int(raw["height"]),
        hash=raw["hash"],
        confirmations=int(raw.get("confirmations", 0)),
        time=int(raw["time"]),
        size=int(raw["size"]),
        weight=int(raw["weight"]),
        transaction_count=len(raw.get("tx", [])),
        previous_hash=raw.get("previousblockhash"),
        next_hash=raw.get("nextblockhash"),
    )


def resolve_block_hash(rpc: BitcoinRpcClient, block_ref: str) -> str:
    if re.fullmatch(r"[0-9]+", block_ref):
        return rpc.get_block_hash(int(block_ref))
    if BLOCK_HASH_PATTERN.fullmatch(block_ref):
        return block_ref
    raise BitcoinRpcError(
        "Block reference must be a non-negative height or 64-character hash",
        status_code=422,
    )


def list_blocks(limit: int = 20) -> BlockListRead:
    rpc = BitcoinRpcClient()
    info = rpc.get_blockchain_info()
    tip_height = int(info["blocks"])
    first_height = max(0, tip_height - limit + 1)
    blocks = []
    for height in range(tip_height, first_height - 1, -1):
        block_hash = info["bestblockhash"] if height == tip_height else rpc.get_block_hash(height)
        blocks.append(summary_from_raw(rpc.get_block(block_hash, verbosity=1)))
    return BlockListRead(
        chain=info["chain"],
        tip_height=tip_height,
        tip_hash=info["bestblockhash"],
        blocks=blocks,
    )


def get_block_detail(block_ref: str) -> BlockDetailRead:
    rpc = BitcoinRpcClient()
    block_hash = resolve_block_hash(rpc, block_ref)
    raw = rpc.get_block(block_hash, verbosity=1)
    summary = summary_from_raw(raw)
    return BlockDetailRead(
        **summary.model_dump(),
        version=int(raw["version"]),
        version_hex=raw["versionHex"],
        merkle_root=raw["merkleroot"],
        median_time=int(raw["mediantime"]),
        nonce=int(raw["nonce"]),
        bits=raw["bits"],
        difficulty=format_difficulty(raw["difficulty"]),
        chainwork=raw["chainwork"],
        transaction_ids=list(raw.get("tx", [])),
    )
```

`limit` is validated by the FastAPI query parameter. If Bitcoin Core returns a not-found error, its existing `BitcoinRpcError` status must remain 404; do not convert RPC connection failures into 404.

- [ ] **Step 4: Add routes and register the router**

Create `backend/app/routers/blocks.py`:

```python
from fastapi import APIRouter, Query

from app.schemas import BlockDetailRead, BlockListRead
from app.services import blocks as block_service

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.get("", response_model=BlockListRead)
def list_blocks(limit: int = Query(default=20, ge=1, le=100)):
    return block_service.list_blocks(limit)


@router.get("/{block_ref}", response_model=BlockDetailRead)
def get_block_detail(block_ref: str):
    return block_service.get_block_detail(block_ref)
```

Modify `backend/app/main.py` to import `blocks` from `app.routers` and register `app.include_router(blocks.router)`. Registering the collection route as `""` keeps `/blocks?limit=20` distinct from `/blocks/{block_ref}`.

- [ ] **Step 5: Add limit validation and RPC failure tests**

Append:

```python
def test_list_blocks_rejects_out_of_range_limit(client: TestClient):
    assert client.get("/blocks?limit=0").status_code == 422
    assert client.get("/blocks?limit=101").status_code == 422


def test_list_blocks_returns_rpc_error(client: TestClient, monkeypatch):
    from app.bitcoin_rpc import BitcoinRpcError

    class FakeRpc:
        def get_blockchain_info(self):
            raise BitcoinRpcError("Bitcoin Core unavailable", status_code=502)

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/blocks")

    assert response.status_code == 502
    assert response.json() == {"detail": "Bitcoin Core unavailable"}
```

- [ ] **Step 6: Run focused and full backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_blocks.py -v
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit the backend slice**

```powershell
git add backend/app/bitcoin_rpc.py backend/app/schemas.py backend/app/services/blocks.py backend/app/routers/blocks.py backend/app/main.py backend/tests/test_blocks.py
git commit -m "feat: expose block explorer API"
```

### Task 3: Add frontend block types, API client, and explorer component

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/components/BlockExplorer.tsx`

**Interfaces:**
- Consumes: `GET /blocks?limit={limit}` and `GET /blocks/{block_ref}`.
- Produces: `BlockSummary`, `BlockList`, `BlockDetail`, `getBlocks(limit)`, `getBlockDetail(blockRef)`, and a presentational `BlockExplorer` component.

- [ ] **Step 1: Add TypeScript types and API functions**

Append to `frontend/src/types.ts`:

```typescript
export type BlockSummary = {
  height: number;
  hash: string;
  confirmations: number;
  time: number;
  size: number;
  weight: number;
  transaction_count: number;
  previous_hash: string | null;
  next_hash: string | null;
};

export type BlockList = {
  chain: string;
  tip_height: number;
  tip_hash: string;
  blocks: BlockSummary[];
};

export type BlockDetail = BlockSummary & {
  version: number;
  version_hex: string;
  merkle_root: string;
  median_time: number;
  nonce: number;
  bits: string;
  difficulty: string;
  chainwork: string;
  transaction_ids: string[];
};
```

Update `frontend/src/api.ts` imports and add:

```typescript
export function getBlocks(limit = 20): Promise<BlockList> {
  return request<BlockList>(`/blocks?limit=${limit}`);
}


export function getBlockDetail(blockRef: string): Promise<BlockDetail> {
  return request<BlockDetail>(`/blocks/${encodeURIComponent(blockRef)}`);
}
```

- [ ] **Step 2: Create the presentational explorer component**

Create `frontend/src/components/BlockExplorer.tsx` with props:

```typescript
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
```

Render a `section` with class `panel block-explorer` containing:

- heading `Block Explorer`;
- chain, tip height, and shortened tip hash;
- a bounded numeric input or select for `limit` with values `10`, `20`, `50`, `100`;
- a `Refresh` button;
- loading, error, and empty states;
- newest-first block rows as buttons so users can select a block;
- selected block metadata and a transaction id list when `selectedBlock` is available.

Use helpers:

```typescript
function shortHash(value: string | null) {
  if (!value) return "Not available";
  return value.length <= 18 ? value : `${value.slice(0, 10)}...${value.slice(-8)}`;
}


function formatTime(value: number | null) {
  return value ? new Date(value * 1000).toLocaleString() : "Not available";
}
```

Use `title={fullHash}` on shortened hashes and txids. Transaction ids remain text in this task; do not create a fake route for Transaction Detail.

- [ ] **Step 3: Build the frontend**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 4: Commit the frontend component slice**

```powershell
git add frontend/src/types.ts frontend/src/api.ts frontend/src/components/BlockExplorer.tsx
git commit -m "feat: add block explorer component"
```

### Task 4: Integrate block loading, selection, mining refresh, and responsive styles

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `getBlocks`, `getBlockDetail`, `BlockList`, `BlockDetail`, and `BlockExplorer`.
- Produces: initial latest-block loading, selected-block detail loading, manual refresh, limit changes, and refresh after mining.

- [ ] **Step 1: Add block state and loaders to `App.tsx`**

Update imports:

```typescript
import { getBlockDetail, getBlocks } from "./api";
import { BlockExplorer } from "./components/BlockExplorer";
import type { BlockDetail, BlockList } from "./types";
```

Add state:

```typescript
const [blockList, setBlockList] = useState<BlockList | null>(null);
const [selectedBlock, setSelectedBlock] = useState<BlockDetail | null>(null);
const [blockLimit, setBlockLimit] = useState(20);
const [blockLoading, setBlockLoading] = useState(false);
const [blockDetailLoading, setBlockDetailLoading] = useState(false);
const [blockError, setBlockError] = useState("");
const [blockDetailError, setBlockDetailError] = useState("");
```

Add loaders:

```typescript
async function selectBlock(blockRef: string) {
  setBlockDetailLoading(true);
  setBlockDetailError("");
  try {
    setSelectedBlock(await getBlockDetail(blockRef));
  } catch (error) {
    setBlockDetailError((error as Error).message);
  } finally {
    setBlockDetailLoading(false);
  }
}


async function refreshBlocks(limit = blockLimit) {
  setBlockLoading(true);
  setBlockError("");
  try {
    const result = await getBlocks(limit);
    setBlockList(result);
    if (result.blocks.length > 0) {
      await selectBlock(String(result.blocks[0].height));
    } else {
      setSelectedBlock(null);
    }
  } catch (error) {
    setBlockError((error as Error).message);
  } finally {
    setBlockLoading(false);
  }
}
```

Call `refreshBlocks()` during initial setup and after `handleMine`. Do not call it from the wallet switch callback. When the limit changes, update `blockLimit` and call `refreshBlocks(nextLimit)` so the selected newest block remains valid.

- [ ] **Step 2: Render the explorer**

Place after the Mempool View integration, or after `TransactionHistory` if the preceding planned views are not yet present:

```tsx
<BlockExplorer
  blockList={blockList}
  selectedBlock={selectedBlock}
  limit={blockLimit}
  loading={blockLoading}
  detailLoading={blockDetailLoading}
  error={blockError}
  detailError={blockDetailError}
  onLimitChange={(nextLimit) => {
    setBlockLimit(nextLimit);
    refreshBlocks(nextLimit).catch(() => undefined);
  }}
  onRefresh={() => refreshBlocks().catch(() => undefined)}
  onSelectBlock={(blockRef) => selectBlock(blockRef).catch(() => undefined)}
/>
```

- [ ] **Step 3: Add responsive block explorer styles**

Add to `frontend/src/styles.css`:

```css
.block-explorer {
  margin-top: 16px;
}

.block-explorer-toolbar,
.block-explorer-summary,
.block-detail-grid {
  display: grid;
  gap: 12px;
}

.block-explorer-toolbar {
  align-items: end;
  grid-template-columns: 1fr auto auto;
  margin: 16px 0;
}

.block-explorer-summary {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.block-list {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
}

.block-row {
  background: #f8fafc;
  border: 1px solid #dde3ea;
  color: #1d2730;
  display: grid;
  gap: 4px;
  grid-template-columns: auto 1fr auto;
  text-align: left;
  width: 100%;
}

.block-row.selected {
  border-color: #1f6feb;
}

.block-detail-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 16px;
}

.block-hash,
.block-txid {
  max-width: 280px;
  overflow-wrap: anywhere;
}

.block-transactions {
  display: grid;
  gap: 6px;
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
}

@media (max-width: 720px) {
  .block-explorer-toolbar,
  .block-explorer-summary,
  .block-detail-grid {
    grid-template-columns: 1fr;
  }

  .block-row {
    grid-template-columns: 1fr;
  }
}
```

Reuse existing `.panel`, `.muted`, `small`, and button styles. Keep the block list and detail inside one panel; do not create nested decorative cards.

- [ ] **Step 4: Run the production build**

Run:

```powershell
npm.cmd run build
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 5: Commit the integration slice**

```powershell
git add frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat: integrate block explorer refresh flow"
```

### Task 5: Document the block explorer and complete verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `GET /blocks`, `GET /blocks/{block_ref}`, and the existing mining flow.
- Produces: reproducible API commands, web demo instructions, and final acceptance evidence.

- [ ] **Step 1: Add block API examples**

After the existing UTXO and mempool examples in `README.md`, add:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/blocks?limit=20"
Invoke-RestMethod "http://127.0.0.1:8000/blocks/101"

$latestBlocks = Invoke-RestMethod "http://127.0.0.1:8000/blocks?limit=1"
$latestBlocks.blocks[0].hash
Invoke-RestMethod "http://127.0.0.1:8000/blocks/$($latestBlocks.blocks[0].hash)"
```

Document that height and hash lookup return the same block detail, and that the detail endpoint lists txids without decoding their full inputs/outputs.

- [ ] **Step 2: Add the web demo flow**

Add:

```text
1. Open the web app and scroll to Block Explorer.
2. Confirm the current regtest tip height and newest block are visible.
3. Select a recent block and inspect its hash, time, size, weight, merkle root, nonce, and transaction ids.
4. Click Mine 1 block.
5. Refresh Block Explorer and verify the tip height increases by one.
6. Select the new block and inspect its coinbase transaction id.
7. Use the block limit control to compare the latest 10 and latest 20 blocks.
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
2. Verify the explorer loads without selecting a wallet.
3. Select a block by clicking its row and verify the detail area updates.
4. Confirm full hashes are available through hover titles while shortened values keep the layout readable.
5. Mine one block, refresh, and verify the new tip appears first.
6. Temporarily stop Bitcoin Core, refresh, and verify the explorer shows an error state instead of crashing.

- [ ] **Step 5: Commit documentation**

```powershell
git add README.md
git commit -m "docs: document block explorer usage"
```

## Final Acceptance Checklist

- [ ] `GET /blocks?limit=20` returns newest active-chain blocks.
- [ ] `GET /blocks/{height}` and `GET /blocks/{hash}` return the same detail.
- [ ] Block detail includes metadata and transaction ids.
- [ ] Invalid references return 422.
- [ ] Missing blocks return 404.
- [ ] RPC failures reach the existing error handler.
- [ ] Mining refreshes the explorer and shows the new tip.
- [ ] The limit is bounded and works for 10, 20, 50, and 100.
- [ ] The frontend remains readable on narrow screens.
- [ ] Backend tests and frontend build pass.
- [ ] README includes API and web demo instructions.
