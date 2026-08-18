# Local Bitcoin Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Bitcoin transfer app where Alice, Bob, and a miner wallet can create regtest addresses, send BTC, mine confirmations, and view balances through a FastAPI backend and React frontend.

**Architecture:** The app uses Bitcoin Core regtest as the source of truth for balances, transactions, blocks, and confirmations. FastAPI exposes small HTTP endpoints that wrap Bitcoin Core JSON-RPC and stores only app-owned metadata in SQLite. The miner wallet acts as a local faucet: it receives mined coinbase rewards, funds Alice, and mines confirmation blocks so the UI can show pending transactions becoming confirmed.

**Tech Stack:** Bitcoin Core v31.1 regtest, Python 3.12, FastAPI, Pydantic, SQLAlchemy, SQLite, pytest, httpx, React, Vite, TypeScript.

**Spec:** `C:\Users\Lenovo\.codex\attachments\05228430-a7f7-4a87-9abd-21486bcca116\pasted-text.txt`

## Global Constraints

- Run Bitcoin Core locally in `regtest`, not mainnet and not testnet.
- Use one Bitcoin Core node with multiple wallets for the MVP: `alice`, `bob`, and `miner`.
- Use Bitcoin Core JSON-RPC for balance, UTXO, transaction, block, and confirmation data.
- SQLite stores app metadata only: users, wallet names, contacts, and transaction notes.
- Do not fake Bitcoin balances in SQLite.
- Treat `miner` as the local faucet wallet; demo funding must be `miner -> Alice -> Bob`, not `Alice -> Bob` from an empty Alice wallet.
- Return confirmed and unconfirmed balance separately so the demo shows pending transactions before mining and confirmed transactions after mining.
- Use `Decimal` for BTC amounts in backend application code and expose both formatted BTC strings and integer satoshi values in API responses.
- Backend must be usable without the frontend through documented HTTP endpoints.
- Keep the MVP to these core flows: create user, create wallet mapping, verify Bitcoin wallet exists, get receiving address, get balance, faucet fund, send BTC, mine block, view transaction history.
- Enable CORS for the local Vite frontend origin `http://127.0.0.1:5173`.
- Use clear local development defaults for RPC: host `127.0.0.1`, port `18443`, user `bitcoinuser`, password `bitcoinpass`.
- Never hard-code production secrets; local defaults may live in `.env.example`.

---

## File Structure

Create this project structure from the empty workspace:

```text
backend/
  app/
    __init__.py
    main.py
    config.py
    db.py
    models.py
    schemas.py
    bitcoin_rpc.py
    services/
      __init__.py
      users.py
      wallets.py
      transactions.py
      mining.py
    routers/
      __init__.py
      health.py
      users.py
      wallets.py
      transactions.py
      mining.py
  tests/
    conftest.py
    test_health.py
    test_users.py
    test_wallets.py
    test_transactions.py
    test_mining.py
  requirements.txt
  .env.example
frontend/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    api.ts
    types.ts
    components/
      UserSwitcher.tsx
      WalletDashboard.tsx
      ReceivePanel.tsx
      SendPanel.tsx
      TransactionHistory.tsx
      MineButton.tsx
README.md
```

Responsibility boundaries:

- `backend/app/bitcoin_rpc.py`: one small JSON-RPC client and typed methods for Bitcoin Core commands.
- `backend/app/services/*.py`: application decisions such as mapping users to wallets and formatting transaction results.
- `backend/app/routers/*.py`: HTTP endpoint definitions only.
- `backend/app/models.py`: SQLAlchemy tables for app metadata only.
- `backend/app/schemas.py`: Pydantic request and response objects shared by routers.
- `frontend/src/api.ts`: all HTTP calls to FastAPI.
- `frontend/src/components/*.tsx`: focused UI pieces for one user flow each.

---

### Task 1: Backend Project Skeleton And Health Endpoint

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/health.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`
- Produces: `GET /health` returning `{"status": "ok"}`
- Produces: `Settings` with Bitcoin RPC and SQLite defaults

- [ ] **Step 1: Create backend dependencies**

Create `backend/requirements.txt`:

```text
fastapi==0.116.1
uvicorn[standard]==0.35.0
pydantic-settings==2.10.1
SQLAlchemy==2.0.43
requests==2.32.4
pytest==8.4.1
httpx==0.28.1
```

- [ ] **Step 2: Create local environment example**

Create `backend/.env.example`:

```text
BITCOIN_RPC_HOST=127.0.0.1
BITCOIN_RPC_PORT=18443
BITCOIN_RPC_USER=bitcoinuser
BITCOIN_RPC_PASSWORD=bitcoinpass
DATABASE_URL=sqlite:///./local_bitcoin_bank.db
```

- [ ] **Step 3: Write the failing health test**

Create `backend/tests/conftest.py`:

```python
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app())
```

Create `backend/tests/test_health.py`:

```python
from tests.conftest import make_client


def test_health_returns_ok():
    client = make_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run the health test and verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_health.py -v
```

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 5: Implement the app factory and health router**

Create `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bitcoin_rpc_host: str = "127.0.0.1"
    bitcoin_rpc_port: int = 18443
    bitcoin_rpc_user: str = "bitcoinuser"
    bitcoin_rpc_password: str = "bitcoinpass"
    database_url: str = "sqlite:///./local_bitcoin_bank.db"
    cors_origins: list[str] = ["http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

Create `backend/app/routers/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.routers import health


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(title="Local Bitcoin Bank")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

Create empty package marker files:

```python
# backend/app/__init__.py
```

```python
# backend/app/routers/__init__.py
```

- [ ] **Step 6: Run the health test and verify it passes**

Run:

```powershell
cd backend
python -m pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend
git commit -m "feat: add backend health endpoint"
```

---

### Task 2: SQLite Metadata Database And Users API

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/users.py`
- Create: `backend/app/routers/users.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_users.py`

**Interfaces:**
- Consumes: `create_app() -> FastAPI`
- Produces: `User(id: int, name: str, wallet_name: str)`
- Produces: `create_user(name: str, wallet_name: str, db: Session) -> User`
- Produces: `list_users(db: Session) -> list[User]`
- Produces: `POST /users` and `GET /users`

- [ ] **Step 1: Write failing user API tests**

Create `backend/tests/test_users.py`:

```python
from tests.conftest import make_client


def test_create_user_returns_user_payload():
    client = make_client()

    response = client.post("/users", json={"name": "Alice", "wallet_name": "alice"})

    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
    assert response.json()["wallet_name"] == "alice"
    assert isinstance(response.json()["id"], int)


def test_list_users_includes_created_user():
    client = make_client()
    client.post("/users", json={"name": "Bob", "wallet_name": "bob"})

    response = client.get("/users")

    assert response.status_code == 200
    assert {"id": 1, "name": "Bob", "wallet_name": "bob"} in response.json()
```

- [ ] **Step 2: Run user tests and verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_users.py -v
```

Expected: FAIL with 404 responses for `/users`.

- [ ] **Step 3: Implement database session and user model**

Create `backend/app/db.py`:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


settings = Settings()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Create `backend/app/models.py`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    wallet_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
```

- [ ] **Step 4: Implement schemas and user service**

Create `backend/app/schemas.py`:

```python
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    wallet_name: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class UserRead(BaseModel):
    id: int
    name: str
    wallet_name: str

    model_config = {"from_attributes": True}
```

Create `backend/app/services/users.py`:

```python
from sqlalchemy.orm import Session

from app import models
from app.schemas import UserCreate


def create_user(payload: UserCreate, db: Session) -> models.User:
    user = models.User(name=payload.name, wallet_name=payload.wallet_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[models.User]:
    return db.query(models.User).order_by(models.User.id).all()
```

Create empty package marker:

```python
# backend/app/services/__init__.py
```

- [ ] **Step 5: Implement users router and register tables**

Create `backend/app/routers/users.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import UserCreate, UserRead
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(payload, db)


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    return user_service.list_users(db)
```

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.config import Settings
from app.db import Base, engine
from app.routers import health, users


def create_app() -> FastAPI:
    settings = Settings()
    Base.metadata.create_all(bind=engine)
    app = FastAPI(title="Local Bitcoin Bank")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(users.router)
    return app


app = create_app()
```

- [ ] **Step 6: Update tests to use isolated in-memory database**

Modify `backend/tests/conftest.py`:

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import create_app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    app = create_app()

    def override_get_db():
        db: Session = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def make_client() -> TestClient:
    return TestClient(create_app())
```

Modify `backend/tests/test_users.py`:

```python
from fastapi.testclient import TestClient


def test_create_user_returns_user_payload(client: TestClient):
    response = client.post("/users", json={"name": "Alice", "wallet_name": "alice"})

    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
    assert response.json()["wallet_name"] == "alice"
    assert isinstance(response.json()["id"], int)


def test_list_users_includes_created_user(client: TestClient):
    client.post("/users", json={"name": "Bob", "wallet_name": "bob"})

    response = client.get("/users")

    assert response.status_code == 200
    assert {"id": 1, "name": "Bob", "wallet_name": "bob"} in response.json()
```

- [ ] **Step 7: Run user tests and verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_users.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend
git commit -m "feat: add users metadata api"
```

---

### Task 3: Bitcoin RPC Client And Bitcoin Health Check

**Files:**
- Create: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/routers/health.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `BitcoinRpcClient.call(method: str, params: list | None = None, wallet: str | None = None) -> dict | list | str | int | float | None`
- Produces: `BitcoinRpcClient.get_blockchain_info() -> dict`
- Produces: `GET /health/bitcoin` returning `{"chain": "regtest", "blocks": int}`

- [ ] **Step 1: Replace health tests with app and Bitcoin health tests**

Modify `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bitcoin_health_returns_chain_info(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_blockchain_info(self):
            return {"chain": "regtest", "blocks": 101}

    monkeypatch.setattr("app.routers.health.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/health/bitcoin")

    assert response.status_code == 200
    assert response.json() == {"chain": "regtest", "blocks": 101}
```

- [ ] **Step 2: Run health tests and verify Bitcoin health fails**

Run:

```powershell
cd backend
python -m pytest tests/test_health.py -v
```

Expected: FAIL because `/health/bitcoin` does not exist.

- [ ] **Step 3: Implement Bitcoin RPC client**

Create `backend/app/bitcoin_rpc.py`:

```python
from typing import Any

import requests
from fastapi import HTTPException

from app.config import Settings


class BitcoinRpcError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def raise_http_rpc_error(error: BitcoinRpcError) -> None:
    raise HTTPException(status_code=error.status_code, detail=error.message)


class BitcoinRpcClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.base_url = f"http://{self.settings.bitcoin_rpc_host}:{self.settings.bitcoin_rpc_port}"
        self.auth = (self.settings.bitcoin_rpc_user, self.settings.bitcoin_rpc_password)

    def call(self, method: str, params: list[Any] | None = None, wallet: str | None = None) -> Any:
        url = self.base_url if wallet is None else f"{self.base_url}/wallet/{wallet}"
        response = requests.post(
            url,
            json={"jsonrpc": "1.0", "id": "local-bitcoin-bank", "method": method, "params": params or []},
            auth=self.auth,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error") is not None:
            raise BitcoinRpcError(str(payload["error"]))
        return payload["result"]

    def get_blockchain_info(self) -> dict[str, Any]:
        return self.call("getblockchaininfo")
```

- [ ] **Step 4: Add Bitcoin health endpoint**

Modify `backend/app/routers/health.py`:

```python
from fastapi import APIRouter

from app.bitcoin_rpc import BitcoinRpcClient

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/bitcoin")
def bitcoin_health() -> dict[str, int | str]:
    info = BitcoinRpcClient().get_blockchain_info()
    return {"chain": info["chain"], "blocks": info["blocks"]}
```

- [ ] **Step 5: Register a global Bitcoin RPC error handler**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.bitcoin_rpc import BitcoinRpcError
```

and inside `create_app()` before router registration:

```python
    @app.exception_handler(BitcoinRpcError)
    def bitcoin_rpc_error_handler(request: Request, exc: BitcoinRpcError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

- [ ] **Step 6: Run health tests and verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 7: Verify against running Bitcoin Core**

Run with `bitcoind -regtest` still open:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Open a second PowerShell tab:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/bitcoin
```

Expected output includes:

```text
chain   blocks
-----   ------
regtest 102
```

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend
git commit -m "feat: add bitcoin rpc health check"
```

---

### Task 4: Wallet Address And Balance API

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/app/services/wallets.py`
- Create: `backend/app/routers/wallets.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_wallets.py`

**Interfaces:**
- Consumes: `BitcoinRpcClient.call(...)`
- Produces: `BitcoinRpcClient.list_wallets() -> list[str]`
- Produces: `BitcoinRpcClient.ensure_wallet_loaded(wallet: str) -> None`
- Produces: `BitcoinRpcClient.get_new_address(wallet: str) -> str`
- Produces: `BitcoinRpcClient.get_balances(wallet: str) -> dict[str, Decimal]`
- Produces: `POST /wallets/{wallet_name}/address`
- Produces: `GET /wallets/{wallet_name}/balance`

- [ ] **Step 1: Write failing wallet API tests**

Create `backend/tests/test_wallets.py`:

```python
from fastapi.testclient import TestClient


def test_create_address_returns_bcrt_address(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_new_address(self, wallet: str):
            assert wallet == "alice"
            return "bcrt1qaliceaddress"

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post("/wallets/alice/address")

    assert response.status_code == 201
    assert response.json() == {"wallet_name": "alice", "address": "bcrt1qaliceaddress"}


def test_get_balance_returns_wallet_balance(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_balances(self, wallet: str):
            assert wallet == "alice"
            return {
                "confirmed": Decimal("10.00000000"),
                "unconfirmed": Decimal("2.00000000"),
                "total": Decimal("12.00000000"),
            }

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/wallets/alice/balance")

    assert response.status_code == 200
    assert response.json() == {
        "wallet_name": "alice",
        "confirmed_balance_btc": "10.00000000",
        "unconfirmed_balance_btc": "2.00000000",
        "total_balance_btc": "12.00000000",
        "confirmed_balance_sats": 1000000000,
        "unconfirmed_balance_sats": 200000000,
        "total_balance_sats": 1200000000,
    }
```

- [ ] **Step 2: Run wallet tests and verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_wallets.py -v
```

Expected: FAIL with 404 responses for `/wallets/alice/address` and `/wallets/alice/balance`.

- [ ] **Step 3: Add wallet RPC methods**

Modify `backend/app/bitcoin_rpc.py`: add these imports and helper near the top of the file:

```python
from decimal import Decimal


SATOSHIS_PER_BTC = Decimal("100000000")


def btc_to_sats(amount: Decimal) -> int:
    return int(amount * SATOSHIS_PER_BTC)
```

Then add these methods inside `class BitcoinRpcClient`:

```python

    def get_new_address(self, wallet: str) -> str:
        self.ensure_wallet_loaded(wallet)
        return self.call("getnewaddress", wallet=wallet)

    def list_wallets(self) -> list[str]:
        return self.call("listwallets")

    def ensure_wallet_loaded(self, wallet: str) -> None:
        if wallet not in self.list_wallets():
            raise BitcoinRpcError(f"Bitcoin wallet '{wallet}' is not loaded", status_code=404)

    def get_balances(self, wallet: str) -> dict[str, Decimal]:
        self.ensure_wallet_loaded(wallet)
        confirmed = Decimal(str(self.call("getbalance", ["*", 1], wallet=wallet)))
        trusted_total = Decimal(str(self.call("getbalance", ["*", 0], wallet=wallet)))
        unconfirmed = trusted_total - confirmed
        return {"confirmed": confirmed, "unconfirmed": unconfirmed, "total": trusted_total}
```

- [ ] **Step 4: Add wallet schemas and service**

Modify `backend/app/schemas.py` and add:

```python
class AddressRead(BaseModel):
    wallet_name: str
    address: str


class BalanceRead(BaseModel):
    wallet_name: str
    confirmed_balance_btc: str
    unconfirmed_balance_btc: str
    total_balance_btc: str
    confirmed_balance_sats: int
    unconfirmed_balance_sats: int
    total_balance_sats: int
```

Create `backend/app/services/wallets.py`:

```python
from decimal import Decimal

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.schemas import AddressRead, BalanceRead


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def create_address(wallet_name: str) -> AddressRead:
    address = BitcoinRpcClient().get_new_address(wallet_name)
    return AddressRead(wallet_name=wallet_name, address=address)


def get_balance(wallet_name: str) -> BalanceRead:
    balances = BitcoinRpcClient().get_balances(wallet_name)
    return BalanceRead(
        wallet_name=wallet_name,
        confirmed_balance_btc=format_btc(balances["confirmed"]),
        unconfirmed_balance_btc=format_btc(balances["unconfirmed"]),
        total_balance_btc=format_btc(balances["total"]),
        confirmed_balance_sats=btc_to_sats(balances["confirmed"]),
        unconfirmed_balance_sats=btc_to_sats(balances["unconfirmed"]),
        total_balance_sats=btc_to_sats(balances["total"]),
    )
```

- [ ] **Step 5: Add wallet router**

Create `backend/app/routers/wallets.py`:

```python
from fastapi import APIRouter, status

from app.schemas import AddressRead, BalanceRead
from app.services import wallets as wallet_service

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("/{wallet_name}/address", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
def create_address(wallet_name: str):
    return wallet_service.create_address(wallet_name)


@router.get("/{wallet_name}/balance", response_model=BalanceRead)
def get_balance(wallet_name: str):
    return wallet_service.get_balance(wallet_name)
```

Modify `backend/app/main.py`:

```python
from app.routers import health, users, wallets
```

and inside `create_app()`:

```python
    app.include_router(wallets.router)
```

- [ ] **Step 6: Run wallet tests and verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_wallets.py -v
```

Expected: PASS.

- [ ] **Step 7: Verify against Bitcoin Core**

Run:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/wallets/alice/address
Invoke-RestMethod http://127.0.0.1:8000/wallets/alice/balance
```

Expected: address starts with `bcrt1`; `confirmed_balance_btc` matches `bitcoin-cli -regtest -rpcwallet=alice getbalance "*" 1`, and `total_balance_btc` matches `bitcoin-cli -regtest -rpcwallet=alice getbalance "*" 0`.

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend
git commit -m "feat: add wallet balance and address api"
```

---

### Task 5: Send Transaction And Faucet API

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/app/services/transactions.py`
- Create: `backend/app/routers/transactions.py`
- Create: `backend/app/routers/faucet.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_transactions.py`

**Interfaces:**
- Produces: `BitcoinRpcClient.send_to_address(wallet: str, address: str, amount_btc: Decimal) -> str`
- Produces: `SendTransactionRequest(from_wallet: str, to_address: str, amount_btc: Decimal)`
- Produces: `SendTransactionRead(txid: str, from_wallet: str, to_address: str, amount_btc: str, amount_sats: int)`
- Produces: `POST /transactions/send`
- Produces: `POST /faucet/{wallet_name}` funds a wallet from `miner` and mines 1 confirmation block

- [ ] **Step 1: Write failing send transaction test**

Create `backend/tests/test_transactions.py`:

```python
from decimal import Decimal

from fastapi.testclient import TestClient


def test_send_transaction_returns_txid(client: TestClient, monkeypatch):
    class FakeRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            assert wallet == "alice"
            assert address == "bcrt1qbobaddress"
            assert amount_btc == Decimal("2.50000000")
            return "abc123txid"

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post(
        "/transactions/send",
        json={"from_wallet": "alice", "to_address": "bcrt1qbobaddress", "amount_btc": "2.50000000"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "txid": "abc123txid",
        "from_wallet": "alice",
        "to_address": "bcrt1qbobaddress",
        "amount_btc": "2.50000000",
        "amount_sats": 250000000,
    }


def test_faucet_funds_wallet_and_mines_confirmation(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_new_address(self, wallet: str):
            assert wallet == "alice"
            return "bcrt1qaliceaddress"

        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            assert wallet == "miner"
            assert address == "bcrt1qaliceaddress"
            assert amount_btc == Decimal("10.00000000")
            return "faucettxid"

        def mine_blocks(self, wallet: str, block_count: int):
            assert wallet == "miner"
            assert block_count == 1
            return ["blockhash1"]

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post("/faucet/alice", json={"amount_btc": "10.00000000"})

    assert response.status_code == 201
    assert response.json() == {
        "txid": "faucettxid",
        "from_wallet": "miner",
        "to_wallet": "alice",
        "to_address": "bcrt1qaliceaddress",
        "amount_btc": "10.00000000",
        "amount_sats": 1000000000,
        "block_hashes": ["blockhash1"],
    }
```

- [ ] **Step 2: Run transaction test and verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_transactions.py -v
```

Expected: FAIL with 404 responses for `/transactions/send` and `/faucet/alice`.

- [ ] **Step 3: Add RPC send method**

Modify `backend/app/bitcoin_rpc.py` and add:

```python
    def send_to_address(self, wallet: str, address: str, amount_btc: Decimal) -> str:
        self.ensure_wallet_loaded(wallet)
        return self.call("sendtoaddress", [address, f"{amount_btc:.8f}"], wallet=wallet)
```

- [ ] **Step 4: Add transaction schemas and service**

Modify `backend/app/schemas.py` and add:

```python
from decimal import Decimal


class SendTransactionRequest(BaseModel):
    from_wallet: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    to_address: str = Field(min_length=8)
    amount_btc: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=8)


class SendTransactionRead(BaseModel):
    txid: str
    from_wallet: str
    to_address: str
    amount_btc: str
    amount_sats: int


class FaucetRequest(BaseModel):
    amount_btc: Decimal = Field(default=Decimal("10.00000000"), gt=Decimal("0"), max_digits=16, decimal_places=8)


class FaucetRead(BaseModel):
    txid: str
    from_wallet: str
    to_wallet: str
    to_address: str
    amount_btc: str
    amount_sats: int
    block_hashes: list[str]
```

Create `backend/app/services/transactions.py`:

```python
from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.schemas import FaucetRead, FaucetRequest, SendTransactionRead, SendTransactionRequest


def send_transaction(payload: SendTransactionRequest) -> SendTransactionRead:
    txid = BitcoinRpcClient().send_to_address(payload.from_wallet, payload.to_address, payload.amount_btc)
    return SendTransactionRead(
        txid=txid,
        from_wallet=payload.from_wallet,
        to_address=payload.to_address,
        amount_btc=f"{payload.amount_btc:.8f}",
        amount_sats=btc_to_sats(payload.amount_btc),
    )


def fund_from_faucet(wallet_name: str, payload: FaucetRequest) -> FaucetRead:
    rpc = BitcoinRpcClient()
    address = rpc.get_new_address(wallet_name)
    txid = rpc.send_to_address("miner", address, payload.amount_btc)
    block_hashes = rpc.mine_blocks("miner", 1)
    return FaucetRead(
        txid=txid,
        from_wallet="miner",
        to_wallet=wallet_name,
        to_address=address,
        amount_btc=f"{payload.amount_btc:.8f}",
        amount_sats=btc_to_sats(payload.amount_btc),
        block_hashes=block_hashes,
    )
```

- [ ] **Step 5: Add transaction router**

Create `backend/app/routers/transactions.py`:

```python
from fastapi import APIRouter, status

from app.schemas import SendTransactionRead, SendTransactionRequest
from app.services import transactions as transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/send", response_model=SendTransactionRead, status_code=status.HTTP_201_CREATED)
def send_transaction(payload: SendTransactionRequest):
    return transaction_service.send_transaction(payload)
```

Create `backend/app/routers/faucet.py`:

```python
from fastapi import APIRouter, status

from app.schemas import FaucetRead, FaucetRequest
from app.services import transactions as transaction_service

router = APIRouter(prefix="/faucet", tags=["faucet"])


@router.post("/{wallet_name}", response_model=FaucetRead, status_code=status.HTTP_201_CREATED)
def fund_from_faucet(wallet_name: str, payload: FaucetRequest):
    return transaction_service.fund_from_faucet(wallet_name, payload)
```

Modify `backend/app/main.py`:

```python
from app.routers import faucet, health, transactions, users, wallets
```

and inside `create_app()`:

```python
    app.include_router(faucet.router)
    app.include_router(transactions.router)
```

- [ ] **Step 6: Run transaction tests and verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_transactions.py -v
```

Expected: PASS.

- [ ] **Step 7: Verify against Bitcoin Core**

Run:

```powershell
$faucet = Invoke-RestMethod -Method Post http://127.0.0.1:8000/faucet/alice -ContentType "application/json" -Body (@{ amount_btc = "10.00000000" } | ConvertTo-Json)
$bobAddress = Invoke-RestMethod -Method Post http://127.0.0.1:8000/wallets/bob/address
Invoke-RestMethod -Method Post http://127.0.0.1:8000/transactions/send -ContentType "application/json" -Body (@{ from_wallet = "alice"; to_address = $bobAddress.address; amount_btc = "2.00000000" } | ConvertTo-Json)
```

Expected: faucet response funds Alice with confirmed BTC, and send response includes a non-empty `txid`.

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend
git commit -m "feat: add bitcoin send transaction api"
```

---

### Task 6: Mining API And Confirmation Flow

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/app/services/mining.py`
- Create: `backend/app/routers/mining.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_mining.py`

**Interfaces:**
- Produces: `BitcoinRpcClient.mine_blocks(wallet: str, block_count: int) -> list[str]`
- Produces: `MineBlocksRequest(wallet_name: str = "miner", block_count: int = 1)`
- Produces: `MineBlocksRead(wallet_name: str, block_count: int, block_hashes: list[str])`
- Produces: `POST /mine`

- [ ] **Step 1: Write failing mining API test**

Create `backend/tests/test_mining.py`:

```python
from fastapi.testclient import TestClient


def test_mine_blocks_returns_hashes(client: TestClient, monkeypatch):
    class FakeRpc:
        def mine_blocks(self, wallet: str, block_count: int):
            assert wallet == "miner"
            assert block_count == 1
            return ["blockhash1"]

    monkeypatch.setattr("app.services.mining.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post("/mine", json={"wallet_name": "miner", "block_count": 1})

    assert response.status_code == 201
    assert response.json() == {
        "wallet_name": "miner",
        "block_count": 1,
        "block_hashes": ["blockhash1"],
    }
```

- [ ] **Step 2: Run mining test and verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_mining.py -v
```

Expected: FAIL with 404 response for `/mine`.

- [ ] **Step 3: Add RPC mining method**

Modify `backend/app/bitcoin_rpc.py` and add:

```python
    def mine_blocks(self, wallet: str, block_count: int) -> list[str]:
        address = self.get_new_address(wallet)
        return self.call("generatetoaddress", [block_count, address])
```

- [ ] **Step 4: Add mining schemas and service**

Modify `backend/app/schemas.py` and add:

```python
class MineBlocksRequest(BaseModel):
    wallet_name: str = Field(default="miner", min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    block_count: int = Field(default=1, ge=1, le=101)


class MineBlocksRead(BaseModel):
    wallet_name: str
    block_count: int
    block_hashes: list[str]
```

Create `backend/app/services/mining.py`:

```python
from app.bitcoin_rpc import BitcoinRpcClient
from app.schemas import MineBlocksRead, MineBlocksRequest


def mine_blocks(payload: MineBlocksRequest) -> MineBlocksRead:
    block_hashes = BitcoinRpcClient().mine_blocks(payload.wallet_name, payload.block_count)
    return MineBlocksRead(
        wallet_name=payload.wallet_name,
        block_count=payload.block_count,
        block_hashes=block_hashes,
    )
```

- [ ] **Step 5: Add mining router**

Create `backend/app/routers/mining.py`:

```python
from fastapi import APIRouter, status

from app.schemas import MineBlocksRead, MineBlocksRequest
from app.services import mining as mining_service

router = APIRouter(tags=["mining"])


@router.post("/mine", response_model=MineBlocksRead, status_code=status.HTTP_201_CREATED)
def mine_blocks(payload: MineBlocksRequest):
    return mining_service.mine_blocks(payload)
```

Modify `backend/app/main.py`:

```python
from app.routers import faucet, health, mining, transactions, users, wallets
```

and inside `create_app()`:

```python
    app.include_router(mining.router)
```

- [ ] **Step 6: Run mining tests and verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_mining.py -v
```

Expected: PASS.

- [ ] **Step 7: Verify confirmation flow against Bitcoin Core**

Run after sending a transaction from Alice to Bob:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/wallets/bob/balance
Invoke-RestMethod -Method Post http://127.0.0.1:8000/mine -ContentType "application/json" -Body (@{ wallet_name = "miner"; block_count = 1 } | ConvertTo-Json)
Invoke-RestMethod http://127.0.0.1:8000/wallets/bob/balance
```

Expected before mining: Bob's `total_balance_btc` includes the incoming amount and `unconfirmed_balance_btc` is greater than `0.00000000`.

Expected after mining: Bob's `total_balance_btc` remains the same, `confirmed_balance_btc` includes the incoming amount, and `unconfirmed_balance_btc` returns to `0.00000000`.

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend
git commit -m "feat: add mining api"
```

---

### Task 7: Transaction History API

**Files:**
- Modify: `backend/app/bitcoin_rpc.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/transactions.py`
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/tests/test_transactions.py`

**Interfaces:**
- Produces: `BitcoinRpcClient.list_transactions(wallet: str, count: int = 20) -> list[dict]`
- Produces: `TransactionRead(txid: str, category: str, amount_btc: str, amount_sats: int, confirmations: int, status: str, time: int | None, blockhash: str | None, address: str | None)`
- Produces: `GET /transactions/{wallet_name}` returning `list[TransactionRead]`

- [ ] **Step 1: Add failing transaction history test**

Modify `backend/tests/test_transactions.py` and add:

```python
def test_list_transactions_returns_recent_wallet_transactions(client: TestClient, monkeypatch):
    class FakeRpc:
        def list_transactions(self, wallet: str, count: int = 20):
            assert wallet == "alice"
            assert count == 20
            return [
                {
                    "txid": "tx1",
                    "category": "send",
                    "amount": "-2.00000000",
                    "confirmations": 1,
                    "address": "bcrt1qbobaddress",
                    "time": 1787030000,
                    "blockhash": "blockhash1",
                }
            ]

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/transactions/alice")

    assert response.status_code == 200
    assert response.json() == [
        {
            "txid": "tx1",
            "category": "send",
            "amount_btc": "-2.00000000",
            "amount_sats": -200000000,
            "confirmations": 1,
            "status": "confirmed",
            "time": 1787030000,
            "blockhash": "blockhash1",
            "address": "bcrt1qbobaddress",
        }
    ]
```

- [ ] **Step 2: Run transaction tests and verify history test fails**

Run:

```powershell
cd backend
python -m pytest tests/test_transactions.py -v
```

Expected: FAIL with 404 response for `/transactions/alice`.

- [ ] **Step 3: Add RPC history method**

Modify `backend/app/bitcoin_rpc.py` and add:

```python
    def list_transactions(self, wallet: str, count: int = 20) -> list[dict[str, Any]]:
        return self.call("listtransactions", ["*", count], wallet=wallet)
```

- [ ] **Step 4: Add history schema and service function**

Modify `backend/app/schemas.py` and add:

```python
class TransactionRead(BaseModel):
    txid: str
    category: str
    amount_btc: str
    amount_sats: int
    confirmations: int
    status: str
    time: int | None = None
    blockhash: str | None = None
    address: str | None = None
```

Modify `backend/app/services/transactions.py` and add:

```python
from decimal import Decimal

from app.bitcoin_rpc import btc_to_sats
from app.schemas import TransactionRead


def list_transactions(wallet_name: str) -> list[TransactionRead]:
    rows = BitcoinRpcClient().list_transactions(wallet_name, count=20)
    transactions: list[TransactionRead] = []
    for row in rows:
        amount = Decimal(str(row["amount"]))
        confirmations = int(row.get("confirmations", 0))
        transactions.append(
            TransactionRead(
                txid=row["txid"],
                category=row["category"],
                amount_btc=f"{amount:.8f}",
                amount_sats=btc_to_sats(amount),
                confirmations=confirmations,
                status="confirmed" if confirmations > 0 else "pending",
                time=row.get("time"),
                blockhash=row.get("blockhash"),
                address=row.get("address"),
            )
        )
    return transactions
```

- [ ] **Step 5: Add history endpoint**

Modify `backend/app/routers/transactions.py` and add:

```python
from app.schemas import SendTransactionRead, SendTransactionRequest, TransactionRead
```

and:

```python
@router.get("/{wallet_name}", response_model=list[TransactionRead])
def list_transactions(wallet_name: str):
    return transaction_service.list_transactions(wallet_name)
```

- [ ] **Step 6: Run transaction tests and verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_transactions.py -v
```

Expected: PASS.

- [ ] **Step 7: Verify against Bitcoin Core**

Run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/transactions/alice
Invoke-RestMethod http://127.0.0.1:8000/transactions/bob
```

Expected: Alice shows a `send` row and Bob shows a `receive` row after the demo transfer.

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend
git commit -m "feat: add transaction history api"
```

---

### Task 8: Frontend Project And API Client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: backend endpoints from Tasks 1-7
- Produces: Vite React app on `http://127.0.0.1:5173`
- Produces: API functions `getUsers`, `createUser`, `getBalance`, `createAddress`, `sendTransaction`, `fundFromFaucet`, `mineBlocks`, `getTransactions`

- [ ] **Step 1: Create frontend dependencies**

Create `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "typescript": "latest",
    "react": "latest",
    "react-dom": "latest",
    "lucide-react": "latest"
  },
  "devDependencies": {}
}
```

- [ ] **Step 2: Create Vite base files**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Local Bitcoin Bank</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}
```

Create `frontend/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173
  }
});
```

- [ ] **Step 3: Create frontend types and API client**

Create `frontend/src/types.ts`:

```typescript
export type User = {
  id: number;
  name: string;
  wallet_name: string;
};

export type Balance = {
  wallet_name: string;
  confirmed_balance_btc: string;
  unconfirmed_balance_btc: string;
  total_balance_btc: string;
  confirmed_balance_sats: number;
  unconfirmed_balance_sats: number;
  total_balance_sats: number;
};

export type Address = {
  wallet_name: string;
  address: string;
};

export type Transaction = {
  txid: string;
  category: string;
  amount_btc: string;
  amount_sats: number;
  confirmations: number;
  status: "pending" | "confirmed";
  time: number | null;
  blockhash: string | null;
  address: string | null;
};
```

Create `frontend/src/api.ts`:

```typescript
import type { Address, Balance, Transaction, User } from "./types";

const API_BASE = "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getUsers(): Promise<User[]> {
  return request<User[]>("/users");
}

export function createUser(name: string, walletName: string): Promise<User> {
  return request<User>("/users", {
    method: "POST",
    body: JSON.stringify({ name, wallet_name: walletName })
  });
}

export function getBalance(walletName: string): Promise<Balance> {
  return request<Balance>(`/wallets/${walletName}/balance`);
}

export function createAddress(walletName: string): Promise<Address> {
  return request<Address>(`/wallets/${walletName}/address`, { method: "POST" });
}

export function sendTransaction(fromWallet: string, toAddress: string, amountBtc: string) {
  return request("/transactions/send", {
    method: "POST",
    body: JSON.stringify({ from_wallet: fromWallet, to_address: toAddress, amount_btc: amountBtc })
  });
}

export function fundFromFaucet(walletName: string, amountBtc = "10.00000000") {
  return request(`/faucet/${walletName}`, {
    method: "POST",
    body: JSON.stringify({ amount_btc: amountBtc })
  });
}

export function mineBlocks(walletName = "miner", blockCount = 1) {
  return request("/mine", {
    method: "POST",
    body: JSON.stringify({ wallet_name: walletName, block_count: blockCount })
  });
}

export function getTransactions(walletName: string): Promise<Transaction[]> {
  return request<Transaction[]>(`/transactions/${walletName}`);
}
```

- [ ] **Step 4: Create minimal app shell**

Create `frontend/src/main.tsx`:

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `frontend/src/App.tsx`:

```typescript
export default function App() {
  return (
    <main>
      <h1>Local Bitcoin Bank</h1>
      <p>Regtest wallet dashboard is ready for UI components.</p>
    </main>
  );
}
```

- [ ] **Step 5: Install frontend dependencies**

Run:

```powershell
cd frontend
npm install
```

Expected: `node_modules` and `package-lock.json` are created.

- [ ] **Step 6: Build frontend**

Run:

```powershell
cd frontend
npm run build
```

Expected: build succeeds and creates `frontend/dist`.

- [ ] **Step 7: Commit**

Run:

```powershell
git add frontend
git commit -m "feat: add frontend scaffold"
```

---

### Task 9: Frontend Wallet Dashboard

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/UserSwitcher.tsx`
- Create: `frontend/src/components/WalletDashboard.tsx`
- Create: `frontend/src/components/ReceivePanel.tsx`
- Create: `frontend/src/components/SendPanel.tsx`
- Create: `frontend/src/components/MineButton.tsx`
- Create: `frontend/src/components/TransactionHistory.tsx`

**Interfaces:**
- Consumes: API functions from `frontend/src/api.ts`
- Produces: working UI for creating users, choosing Alice or Bob, displaying balance, generating receive address, sending BTC, mining a block, and viewing recent transactions

- [ ] **Step 1: Create user switcher component**

Create `frontend/src/components/UserSwitcher.tsx`:

```typescript
import type { User } from "../types";

type Props = {
  users: User[];
  selectedWallet: string;
  onSelect: (walletName: string) => void;
};

export function UserSwitcher({ users, selectedWallet, onSelect }: Props) {
  return (
    <div className="toolbar">
      {users.map((user) => (
        <button
          key={user.id}
          className={user.wallet_name === selectedWallet ? "active" : ""}
          onClick={() => onSelect(user.wallet_name)}
        >
          {user.name}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create balance dashboard component**

Create `frontend/src/components/WalletDashboard.tsx`:

```typescript
import type { Balance } from "../types";

type Props = {
  walletName: string;
  balance: Balance | null;
};

export function WalletDashboard({ walletName, balance }: Props) {
  return (
    <section className="panel">
      <p className="label">Wallet</p>
      <h2>{walletName}</h2>
      <p className="balance">{balance ? balance.confirmed_balance_btc : "0.00000000"} confirmed BTC</p>
      <p>{balance ? balance.unconfirmed_balance_btc : "0.00000000"} pending BTC</p>
    </section>
  );
}
```

- [ ] **Step 3: Create receive panel component**

Create `frontend/src/components/ReceivePanel.tsx`:

```typescript
type Props = {
  address: string;
  onCreateAddress: () => void;
};

export function ReceivePanel({ address, onCreateAddress }: Props) {
  return (
    <section className="panel">
      <h3>Receive</h3>
      <button onClick={onCreateAddress}>New address</button>
      {address && <code>{address}</code>}
    </section>
  );
}
```

- [ ] **Step 4: Create send panel component**

Create `frontend/src/components/SendPanel.tsx`:

```typescript
import { useState } from "react";

type Props = {
  onSend: (address: string, amountBtc: string) => void;
};

export function SendPanel({ onSend }: Props) {
  const [address, setAddress] = useState("");
  const [amount, setAmount] = useState("1");

  return (
    <section className="panel">
      <h3>Send</h3>
      <input value={address} onChange={(event) => setAddress(event.target.value)} placeholder="bcrt1..." />
      <input value={amount} onChange={(event) => setAmount(event.target.value)} type="number" min="0.00000001" step="0.00000001" />
      <button onClick={() => onSend(address, amount)}>Send BTC</button>
    </section>
  );
}
```

- [ ] **Step 5: Create mining button component**

Create `frontend/src/components/MineButton.tsx`:

```typescript
type Props = {
  onMine: () => void;
};

export function MineButton({ onMine }: Props) {
  return <button onClick={onMine}>Mine 1 block</button>;
}
```

- [ ] **Step 6: Create transaction history component**

Create `frontend/src/components/TransactionHistory.tsx`:

```typescript
import type { Transaction } from "../types";

type Props = {
  transactions: Transaction[];
};

export function TransactionHistory({ transactions }: Props) {
  return (
    <section className="panel">
      <h3>Recent transactions</h3>
      <ul>
        {transactions.map((tx) => (
          <li key={`${tx.txid}-${tx.category}-${tx.amount_sats}`}>
            <span>{tx.category}</span>
            <strong>{tx.amount_btc} BTC</strong>
            <small>{tx.status} - {tx.confirmations} confirmations</small>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 7: Wire components in App**

Modify `frontend/src/App.tsx`:

```typescript
import { useEffect, useState } from "react";
import { createAddress, createUser, fundFromFaucet, getBalance, getTransactions, getUsers, mineBlocks, sendTransaction } from "./api";
import { MineButton } from "./components/MineButton";
import { ReceivePanel } from "./components/ReceivePanel";
import { SendPanel } from "./components/SendPanel";
import { TransactionHistory } from "./components/TransactionHistory";
import { UserSwitcher } from "./components/UserSwitcher";
import { WalletDashboard } from "./components/WalletDashboard";
import type { Balance, Transaction, User } from "./types";

export default function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedWallet, setSelectedWallet] = useState("alice");
  const [balance, setBalance] = useState<Balance | null>(null);
  const [address, setAddress] = useState("");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [message, setMessage] = useState("");

  async function refresh(walletName = selectedWallet) {
    setUsers(await getUsers());
    setBalance(await getBalance(walletName));
    setTransactions(await getTransactions(walletName));
  }

  async function ensureDefaultUsers() {
    const currentUsers = await getUsers();
    if (currentUsers.length === 0) {
      await createUser("Alice", "alice");
      await createUser("Bob", "bob");
      await createUser("Miner", "miner");
    }
  }

  useEffect(() => {
    ensureDefaultUsers().then(() => refresh("alice"));
  }, []);

  async function handleAddress() {
    const result = await createAddress(selectedWallet);
    setAddress(result.address);
  }

  async function handleSend(toAddress: string, amountBtc: string) {
    await sendTransaction(selectedWallet, toAddress, amountBtc);
    setMessage("Transaction sent. Mine a block to confirm it.");
    await refresh();
  }

  async function handleFaucet() {
    await fundFromFaucet(selectedWallet, "10.00000000");
    setMessage(`${selectedWallet} funded from miner faucet.`);
    await refresh();
  }

  async function handleMine() {
    await mineBlocks("miner", 1);
    setMessage("Block mined.");
    await refresh();
  }

  return (
    <main className="app">
      <header>
        <h1>Local Bitcoin Bank</h1>
        <button onClick={handleFaucet}>Faucet 10 BTC</button>
        <MineButton onMine={handleMine} />
      </header>
      <UserSwitcher users={users} selectedWallet={selectedWallet} onSelect={(wallet) => { setSelectedWallet(wallet); refresh(wallet); }} />
      <WalletDashboard walletName={selectedWallet} balance={balance} />
      <div className="grid">
        <ReceivePanel address={address} onCreateAddress={handleAddress} />
        <SendPanel onSend={handleSend} />
      </div>
      {message && <p>{message}</p>}
      <TransactionHistory transactions={transactions} />
    </main>
  );
}
```

- [ ] **Step 8: Build frontend**

Run:

```powershell
cd frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 9: Manually verify UI flow**

Run backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Run frontend:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Expected flow:

```text
Alice dashboard loads
New address creates a bcrt1 address
Send BTC accepts Bob address and amount
Mine 1 block confirms pending transfer
Recent transactions refresh after mining
```

- [ ] **Step 10: Commit**

Run:

```powershell
git add frontend
git commit -m "feat: add wallet dashboard ui"
```

---

### Task 10: README And Demo Script

**Files:**
- Create: `README.md`

**Interfaces:**
- Produces: developer setup instructions
- Produces: demo script for proving the full Bitcoin transfer flow

- [ ] **Step 1: Create README**

Create `README.md`:

```markdown
# Local Bitcoin Bank

Local Bitcoin Bank is a learning project that uses Bitcoin Core regtest to send real local Bitcoin transactions without connecting to mainnet.

## Requirements

- Windows PowerShell
- Bitcoin Core v31.1
- Python 3.12
- Node.js 22 or newer

## Bitcoin Core Setup

Create `%APPDATA%\Bitcoin\bitcoin.conf`:

```ini
regtest=1
server=1
rpcuser=bitcoinuser
rpcpassword=bitcoinpass
fallbackfee=0.0001
```

Start Bitcoin Core:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoind.exe" -regtest
```

Create wallets:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest createwallet "alice"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest createwallet "bob"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest createwallet "miner"
```

Fund the miner, then fund Alice from the miner faucet:

```powershell
$minerAddress = & "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest -rpcwallet=miner getnewaddress
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest generatetoaddress 101 $minerAddress

$aliceAddress = & "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest -rpcwallet=alice getnewaddress
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest -rpcwallet=miner sendtoaddress $aliceAddress 10
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest generatetoaddress 1 $minerAddress
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest -rpcwallet=alice getbalance "*" 1
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Demo Flow

1. Open the app.
2. Select Alice and click `Faucet 10 BTC` if Alice does not already have confirmed BTC.
3. Select Bob and create a receive address.
4. Select Alice and send `2 BTC` to Bob's address.
5. Select Bob and confirm `pending BTC` shows the incoming transfer.
6. Click `Mine 1 block`.
7. Select Bob and confirm pending BTC moved to confirmed BTC.
8. Open transaction history for Alice and Bob; the transaction should move from `pending` to `confirmed`.

## Backend Tests

```powershell
cd backend
python -m pytest -v
```

## Frontend Build

```powershell
cd frontend
npm run build
```
```

- [ ] **Step 2: Run backend tests**

Run:

```powershell
cd backend
python -m pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: frontend build succeeds.

- [ ] **Step 4: Commit**

Run:

```powershell
git add README.md
git commit -m "docs: add local bitcoin bank setup guide"
```

---

## Final Verification

- [ ] Start Bitcoin Core:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoind.exe" -regtest
```

- [ ] Start backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

- [ ] Start frontend:

```powershell
cd frontend
npm run dev
```

- [ ] Open app:

```text
http://127.0.0.1:5173
```

- [ ] Prove the core project value:

```text
Bob creates a bcrt1 receive address
Miner faucet funds Alice with confirmed BTC
Alice sends BTC to Bob
Transaction appears before confirmation
Miner mines 1 block
Bob pending balance moves to confirmed balance
History shows status, confirmations, time, and blockhash
```

- [ ] Confirm backend-only flow:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/bitcoin
Invoke-RestMethod -Method Post http://127.0.0.1:8000/faucet/alice -ContentType "application/json" -Body (@{ amount_btc = "10.00000000" } | ConvertTo-Json)
Invoke-RestMethod http://127.0.0.1:8000/wallets/alice/balance
Invoke-RestMethod http://127.0.0.1:8000/transactions/alice
```

Expected: all commands return successful JSON responses; Alice balance shows confirmed BTC from the faucet.

---

## Self-Review

- Spec coverage: the plan covers Bitcoin Core regtest, one node with multiple wallets, FastAPI, SQLite metadata, React UI, wallet existence checks, faucet funding, wallet address creation, confirmed/unconfirmed balance lookup, BTC transfer, mining confirmation, and transaction history with status metadata.
- Placeholder scan: the plan contains concrete file names, command names, endpoint paths, request payloads, and test expectations.
- Type consistency: backend methods use the same names across RPC client, services, routers, and tests; frontend API types match backend response schemas.
