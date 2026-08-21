# Local Bitcoin Bank

Local Bitcoin Bank is a learning project that uses Bitcoin Core regtest to send real local Bitcoin transactions without connecting to mainnet.

## What You Will Run

The local app has three parts:

```text
React web app
  -> FastAPI backend
    -> Bitcoin Core regtest
```

Keep Bitcoin Core and the backend running while using the web app.

## Requirements

- Windows PowerShell
- Bitcoin Core v31.1
- Python 3.14 or newer
- Node.js 22 or newer
- Git

Check versions:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" --version
python --version
node --version
npm --version
git --version
```

## 1. Clone The Project

```powershell
git clone https://github.com/CuongTran17/bitcointest.git
cd bitcointest
```

## 2. Configure Bitcoin Core

Create the Bitcoin data folder and config file:

```powershell
New-Item -ItemType Directory -Force "$env:APPDATA\Bitcoin"
notepad "$env:APPDATA\Bitcoin\bitcoin.conf"
```

Paste this into `bitcoin.conf`:

```ini
[regtest]
txindex=1

regtest=1
server=1
rpcuser=bitcoinuser
rpcpassword=bitcoinpass
fallbackfee=0.0001
```

If you previously ran Bitcoin Core without `txindex=1`, perform a one-time reindex:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoind.exe" -regtest -txindex=1 -reindex
```

## 3. Start Bitcoin Core Regtest

Open PowerShell tab 1:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoind.exe" -regtest
```

Keep this tab open.

In another PowerShell tab, check that regtest is running:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest getblockchaininfo
```

The response should include:

```json
{
  "chain": "regtest"
}
```

## 4. Create Or Load Wallets

Run these once:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest createwallet "alice"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest createwallet "bob"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest createwallet "miner"
```

If a wallet already exists, load it instead:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest loadwallet "alice"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest loadwallet "bob"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest loadwallet "miner"
```

Check loaded wallets:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest listwallets
```

## 5. Fund The Miner Wallet

The miner wallet acts as a local faucet.

```powershell
$minerAddress = & "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest -rpcwallet=miner getnewaddress
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest generatetoaddress 101 $minerAddress
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest -rpcwallet=miner getbalance
```

The miner should now have spendable regtest BTC.

## 6. Setup Backend

Open PowerShell tab 2 in the project folder:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Keep this tab open.

Backend URL:

```text
http://127.0.0.1:8000
```

Quick backend checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/bitcoin
```

## 7. Setup And Start The Web App

Open PowerShell tab 3 in the project folder:

```powershell
cd frontend
npm install
npm run dev
```

Open the web app:

```text
http://127.0.0.1:5173
```

Keep the frontend tab open while using the app.

## 8. Demo Flow In The Web App

1. Open `http://127.0.0.1:5173`.
2. Select Alice.
3. Click `Faucet 10 BTC` to fund Alice from the miner wallet.
4. Select Bob.
5. Click `New address`.
6. Copy Bob's `bcrt1...` address.
7. Select Alice.
8. Paste Bob's address into `Send`.
9. Send `2.00000000` BTC.
10. Select Bob and observe `Alice -> Bob`, `pending`, and `0 confirmations`.
11. Click `Mine 1 block`.
12. Refresh or switch wallets and observe `confirmed`, at least `1 confirmation`, and a block hash.
13. Hover the shortened `txid` value when debugging the transaction.
14. Click the transaction row in `Recent transactions`.
15. Review `Inputs`, `Outputs`, `Block`, `Size`, and `Raw JSON`.
16. Select Bob and inspect `UTXO Viewer` after the transfer is confirmed.
17. Observe the total amount, satoshi value, txid/vout, confirmations, address, and spendable state.
18. Select Alice and compare that her change output appears as a different UTXO.
19. Click `Refresh` in UTXO Viewer after sending or mining to reload the current wallet UTXO set.

The detail panel uses Bitcoin Core `getrawtransaction` data. Wallet names appear only when the app has local metadata for that txid or output address. Fee may show `Not available` for transactions where Bitcoin Core does not return fee directly.

The app can show `Alice -> Bob` only when Bob's address was generated through this app or through `POST /wallets/bob/address`. If Alice sends to an address that the app has never seen, the transaction is still valid, but the history shows `Unknown address`.

## Useful API Commands

Create default app users:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/users -ContentType "application/json" -Body (@{ name = "Alice"; wallet_name = "alice" } | ConvertTo-Json)
Invoke-RestMethod -Method Post http://127.0.0.1:8000/users -ContentType "application/json" -Body (@{ name = "Bob"; wallet_name = "bob" } | ConvertTo-Json)
Invoke-RestMethod -Method Post http://127.0.0.1:8000/users -ContentType "application/json" -Body (@{ name = "Miner"; wallet_name = "miner" } | ConvertTo-Json)
```

Fund Alice from the faucet:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/faucet/alice -ContentType "application/json" -Body (@{ amount_btc = "10.00000000" } | ConvertTo-Json)
```

Get Bob address:

```powershell
$bobAddress = Invoke-RestMethod -Method Post http://127.0.0.1:8000/wallets/bob/address
$bobAddress.address
```

Send from Alice to Bob:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/transactions/send -ContentType "application/json" -Body (@{ from_wallet = "alice"; to_address = $bobAddress.address; amount_btc = "2.00000000" } | ConvertTo-Json)
```

Mine one confirmation block:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/mine -ContentType "application/json" -Body (@{ wallet_name = "miner"; block_count = 1 } | ConvertTo-Json)
```

Check balances and history:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/wallets/alice/balance
Invoke-RestMethod http://127.0.0.1:8000/wallets/bob/balance
Invoke-RestMethod http://127.0.0.1:8000/transactions/alice
Invoke-RestMethod http://127.0.0.1:8000/transactions/bob
```

Fetch detailed transaction data:

```powershell
$history = Invoke-RestMethod http://127.0.0.1:8000/transactions/alice
$txid = $history[0].txid
Invoke-RestMethod "http://127.0.0.1:8000/transactions/detail/$txid"
```

Fetch unspent transaction outputs (UTXOs):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/utxos/alice
Invoke-RestMethod http://127.0.0.1:8000/utxos/bob
```

Important UTXO fields:

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

The viewer includes pending outputs with zero confirmations. A wallet with no UTXOs returns zero totals.

Look up which local wallet owns an address created by the app:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/addresses/$($bobAddress.address)"
```

Transaction history returns readable wallet relationship metadata when known:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/transactions/alice
Invoke-RestMethod http://127.0.0.1:8000/transactions/bob
```

Important fields:

```json
{
  "from_wallet": "alice",
  "to_wallet": "bob",
  "status": "pending",
  "confirmations": 0,
  "blockhash": null
}
```

## Tests And Builds

Backend tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

Frontend build:

```powershell
cd frontend
npm run build
```

## Common Problems

### `bitcoin-cli` or `bitcoind` is not recognized

Use the full path:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" --version
& "C:\Program Files\Bitcoin\daemon\bitcoind.exe" --version
```

### Backend cannot connect to Bitcoin Core

Check that:

- The `bitcoind -regtest` PowerShell tab is still running.
- `%APPDATA%\Bitcoin\bitcoin.conf` has `server=1`.
- RPC user/password match the backend defaults.
- `bitcoin-cli -regtest getblockchaininfo` works.

### Wallet is not loaded

Load the wallet:

```powershell
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest loadwallet "alice"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest loadwallet "bob"
& "C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe" -regtest loadwallet "miner"
```

### Alice has 0 BTC

Use the web button `Faucet 10 BTC`, or call:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/faucet/alice -ContentType "application/json" -Body (@{ amount_btc = "10.00000000" } | ConvertTo-Json)
```

### Web app cannot call backend

Check that:

- Backend is running at `http://127.0.0.1:8000`.
- Frontend is running at `http://127.0.0.1:5173`.
- You opened the Vite URL, not the backend URL.
