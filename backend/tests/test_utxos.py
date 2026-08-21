from app.bitcoin_rpc import BitcoinRpcClient


def test_list_unspent_uses_wallet_and_confirmation_range(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return [{"txid": "tx1", "vout": 0, "amount": "1.25000000", "confirmations": 0}]

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)
    monkeypatch.setattr(BitcoinRpcClient, "ensure_wallet_loaded", lambda self, wallet: None)

    result = BitcoinRpcClient().list_unspent("alice")

    assert result[0]["txid"] == "tx1"
    assert calls == [("listunspent", [0, 9999999, [], True], "alice")]
