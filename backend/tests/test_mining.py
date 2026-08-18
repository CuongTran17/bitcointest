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
