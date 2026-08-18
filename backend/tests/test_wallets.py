from decimal import Decimal

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


def test_get_balance_returns_confirmed_and_unconfirmed_wallet_balance(client: TestClient, monkeypatch):
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
