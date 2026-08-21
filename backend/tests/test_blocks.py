import pytest
from fastapi.testclient import TestClient

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError


BLOCK_101 = "0000000000000000000000000000000000000000000000000000000000000101"
BLOCK_100 = "0000000000000000000000000000000000000000000000000000000000000100"


def test_get_block_hash_calls_height_rpc(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return "0000000000000000000000000000000000000000000000000000000000000001"

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_block_hash(101)

    assert result.endswith("0001")
    assert calls == [("getblockhash", [101], None)]


def test_get_block_calls_metadata_verbosity(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"hash": "block1", "height": 101, "tx": ["tx1"]}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_block("block1")

    assert result["height"] == 101
    assert calls == [("getblock", ["block1", 1], None)]


def test_block_not_found_errors_are_translated_to_404(monkeypatch):
    def fake_call(self, method, params=None, wallet=None):
        raise BitcoinRpcError("Block height out of range", rpc_code=-8)

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    with pytest.raises(BitcoinRpcError) as error:
        BitcoinRpcClient().get_block_hash(999999)

    assert error.value.status_code == 404
    assert error.value.rpc_code == -8


def test_block_hash_not_found_error_is_translated_to_404(monkeypatch):
    def fake_call(self, method, params=None, wallet=None):
        raise BitcoinRpcError("Block not found", rpc_code=-5)

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    with pytest.raises(BitcoinRpcError) as error:
        BitcoinRpcClient().get_block("missing-hash")

    assert error.value.status_code == 404
    assert error.value.rpc_code == -5


def test_list_blocks_returns_newest_first_with_tip_metadata(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_blockchain_info(self):
            return {"chain": "regtest", "blocks": 101, "bestblockhash": BLOCK_101}

        def get_block_hash(self, height: int):
            return BLOCK_101 if height == 101 else BLOCK_100

        def get_block(self, block_hash: str, verbosity: int = 1):
            height = 101 if block_hash == BLOCK_101 else 100
            return {
                "hash": block_hash,
                "confirmations": 1 if height == 101 else 2,
                "height": height,
                "time": 1787030000 + height,
                "size": 285,
                "weight": 1140,
                "tx": [f"tx-{height}"],
                "previousblockhash": BLOCK_100 if height == 101 else None,
                "nextblockhash": BLOCK_101 if height == 100 else None,
            }

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/blocks?limit=2")

    assert response.status_code == 200
    assert response.json() == {
        "chain": "regtest",
        "tip_height": 101,
        "tip_hash": BLOCK_101,
        "blocks": [
            {
                "height": 101,
                "hash": BLOCK_101,
                "confirmations": 1,
                "time": 1787030101,
                "size": 285,
                "weight": 1140,
                "transaction_count": 1,
                "previous_hash": BLOCK_100,
                "next_hash": None,
            },
            {
                "height": 100,
                "hash": BLOCK_100,
                "confirmations": 2,
                "time": 1787030100,
                "size": 285,
                "weight": 1140,
                "transaction_count": 1,
                "previous_hash": None,
                "next_hash": BLOCK_101,
            },
        ],
    }


def test_block_detail_accepts_height_and_hash(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_block_hash(self, height: int):
            assert height == 101
            return BLOCK_101

        def get_block(self, block_hash: str, verbosity: int = 1):
            assert block_hash == BLOCK_101
            assert verbosity == 1
            return {
                "hash": BLOCK_101,
                "confirmations": 1,
                "height": 101,
                "time": 1787030000,
                "size": 285,
                "weight": 1140,
                "tx": ["coinbase-tx", "transfer-tx"],
                "previousblockhash": BLOCK_100,
                "nextblockhash": None,
                "version": 536870912,
                "versionHex": "20000000",
                "merkleroot": "merkle-root",
                "mediantime": 1787029990,
                "nonce": 42,
                "bits": "207fffff",
                "difficulty": 4.656542373906925e-10,
                "chainwork": "0002",
            }

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    by_height = client.get("/blocks/101")
    by_hash = client.get(f"/blocks/{BLOCK_101}")

    assert by_height.status_code == 200
    assert by_hash.status_code == 200
    assert by_height.json() == by_hash.json()
    assert by_height.json()["transaction_ids"] == ["coinbase-tx", "transfer-tx"]
    assert by_height.json()["difficulty"] == "0.000000000465654237"


def test_block_detail_rejects_invalid_reference(client: TestClient):
    response = client.get("/blocks/not-a-height-or-hash")

    assert response.status_code == 422


def test_block_detail_returns_404_for_missing_block(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_block_hash(self, height: int):
            raise BitcoinRpcError("Block height out of range", status_code=404)

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/blocks/999999")

    assert response.status_code == 404


def test_list_blocks_rejects_out_of_range_limit(client: TestClient):
    assert client.get("/blocks?limit=0").status_code == 422
    assert client.get("/blocks?limit=101").status_code == 422


def test_list_blocks_returns_rpc_error(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_blockchain_info(self):
            raise BitcoinRpcError("Bitcoin Core unavailable", status_code=502)

    monkeypatch.setattr("app.services.blocks.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/blocks")

    assert response.status_code == 502
    assert response.json() == {"detail": "Bitcoin Core unavailable"}
