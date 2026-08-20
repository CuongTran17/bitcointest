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
        "to_wallet": None,
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


def test_list_transactions_returns_status_and_metadata(client: TestClient, monkeypatch):
    class FakeWalletRpc:
        def get_new_address(self, wallet: str):
            assert wallet == "bob"
            return "bcrt1qbobaddress"

    class FakeSendRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            assert wallet == "alice"
            assert address == "bcrt1qbobaddress"
            assert amount_btc == Decimal("2.00000000")
            return "tx1"

    class FakeListRpc:
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
                },
                {
                    "txid": "tx2",
                    "category": "receive",
                    "amount": "1.00000000",
                    "confirmations": 0,
                    "address": "bcrt1qaliceaddress",
                    "time": 1787030100,
                },
            ]

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeWalletRpc())
    client.post("/wallets/bob/address")
    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeSendRpc())
    client.post(
        "/transactions/send",
        json={"from_wallet": "alice", "to_address": "bcrt1qbobaddress", "amount_btc": "2.00000000"},
    )
    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeListRpc())

    response = client.get("/transactions/alice")

    assert response.status_code == 200
    assert response.json() == [
        {
            "txid": "tx1",
            "from_wallet": "alice",
            "to_wallet": "bob",
            "category": "send",
            "amount_btc": "-2.00000000",
            "amount_sats": -200000000,
            "confirmations": 1,
            "status": "confirmed",
            "time": 1787030000,
            "blockhash": "blockhash1",
            "address": "bcrt1qbobaddress",
        },
        {
            "txid": "tx2",
            "from_wallet": None,
            "to_wallet": None,
            "category": "receive",
            "amount_btc": "1.00000000",
            "amount_sats": 100000000,
            "confirmations": 0,
            "status": "pending",
            "time": 1787030100,
            "blockhash": None,
            "address": "bcrt1qaliceaddress",
        },
    ]
