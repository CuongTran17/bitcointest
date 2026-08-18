# Local Bitcoin Bank

Local Bitcoin Bank is a learning project that uses Bitcoin Core regtest to send real local Bitcoin transactions without connecting to mainnet.

## Requirements

- Windows PowerShell
- Bitcoin Core v31.1
- Python 3.14 or newer
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
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
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
.\.venv\Scripts\python.exe -m pytest -v
```

## Frontend Build

```powershell
cd frontend
npm run build
```
