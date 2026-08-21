import requests

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError


def test_get_raw_transaction_calls_numeric_verbosity_rpc(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"txid": "tx1", "vin": [], "vout": []}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_raw_transaction("tx1")

    assert result == {"txid": "tx1", "vin": [], "vout": []}
    assert calls == [("getrawtransaction", ["tx1", 2], None)]


def test_call_preserves_json_rpc_error_before_http_error(monkeypatch):
    class Response:
        def json(self):
            return {"result": None, "error": {"code": -5, "message": "No such transaction"}}

        def raise_for_status(self):
            raise requests.HTTPError("500 Server Error")

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: Response())

    try:
        BitcoinRpcClient().call("getrawtransaction", ["missing", 2])
    except BitcoinRpcError as exc:
        assert exc.rpc_code == -5
        assert exc.status_code == 502
    else:
        raise AssertionError("BitcoinRpcError was not raised")


def test_call_maps_connection_failure_to_502(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "post", fail)

    try:
        BitcoinRpcClient().call("getblockchaininfo")
    except BitcoinRpcError as exc:
        assert exc.status_code == 502
        assert exc.rpc_code is None
    else:
        raise AssertionError("BitcoinRpcError was not raised")


def test_get_raw_transaction_maps_core_not_found_to_404(monkeypatch):
    def fake_call(self, method, params=None, wallet=None):
        raise BitcoinRpcError("No such transaction", rpc_code=-5)

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    try:
        BitcoinRpcClient().get_raw_transaction("missing")
    except BitcoinRpcError as exc:
        assert exc.status_code == 404
        assert exc.rpc_code == -5
    else:
        raise AssertionError("BitcoinRpcError was not raised")
