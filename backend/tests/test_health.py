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
