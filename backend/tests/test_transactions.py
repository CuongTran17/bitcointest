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
