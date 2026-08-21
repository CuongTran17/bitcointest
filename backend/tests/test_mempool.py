from app.bitcoin_rpc import BitcoinRpcClient


def test_get_raw_mempool_requests_verbose_node_data(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"tx1": {"vsize": 141}}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_raw_mempool()

    assert result == {"tx1": {"vsize": 141}}
    assert calls == [("getrawmempool", [True], None)]
