import pytest

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError


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
