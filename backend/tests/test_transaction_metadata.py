from decimal import Decimal

from fastapi.testclient import TestClient


def test_send_records_known_recipient(client: TestClient, monkeypatch):
    class FakeWalletRpc:
        def get_new_address(self, wallet: str):
            assert wallet == "bob"
            return "bcrt1qbobaddress"

    class FakeTransactionRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            assert wallet == "alice"
            assert address == "bcrt1qbobaddress"
            assert amount_btc == Decimal("2.00000000")
            return "sendtxid"

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeWalletRpc())
    client.post("/wallets/bob/address")
    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeTransactionRpc())

    response = client.post(
        "/transactions/send",
        json={"from_wallet": "alice", "to_address": "bcrt1qbobaddress", "amount_btc": "2.00000000"},
    )

    assert response.status_code == 201
    assert response.json()["to_wallet"] == "bob"


def test_send_allows_unknown_recipient(client: TestClient, monkeypatch):
    class FakeRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            assert wallet == "alice"
            assert address == "bcrt1qexternaladdress"
            assert amount_btc == Decimal("1.00000000")
            return "external-txid"

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post(
        "/transactions/send",
        json={"from_wallet": "alice", "to_address": "bcrt1qexternaladdress", "amount_btc": "1.00000000"},
    )

    assert response.status_code == 201
    assert response.json()["to_wallet"] is None


def test_faucet_records_miner_to_wallet_relationship(client: TestClient, monkeypatch):
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

        def list_transactions(self, wallet: str, count: int = 20):
            assert wallet == "alice"
            return [
                {
                    "txid": "faucettxid",
                    "category": "receive",
                    "amount": "10.00000000",
                    "confirmations": 1,
                    "address": "bcrt1qaliceaddress",
                    "time": 1787030000,
                    "blockhash": "blockhash1",
                }
            ]

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post("/faucet/alice", json={"amount_btc": "10.00000000"})

    assert response.status_code == 201

    history = client.get("/transactions/alice")
    assert history.status_code == 200
    assert history.json()[0]["from_wallet"] == "miner"
    assert history.json()[0]["to_wallet"] == "alice"
