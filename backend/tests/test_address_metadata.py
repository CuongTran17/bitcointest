from fastapi.testclient import TestClient


def test_create_address_persists_owner(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_new_address(self, wallet: str):
            assert wallet == "alice"
            return "bcrt1qaliceaddress"

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeRpc())

    response = client.post("/wallets/alice/address")

    assert response.status_code == 201
    assert response.json() == {"wallet_name": "alice", "address": "bcrt1qaliceaddress"}

    lookup = client.get("/addresses/bcrt1qaliceaddress")
    assert lookup.status_code == 200
    assert lookup.json() == {"address": "bcrt1qaliceaddress", "wallet_name": "alice"}


def test_address_lookup_returns_404_for_unknown_address(client: TestClient):
    response = client.get("/addresses/bcrt1qunknownaddress")

    assert response.status_code == 404
    assert response.json() == {"detail": "Address is not mapped to a local wallet"}
