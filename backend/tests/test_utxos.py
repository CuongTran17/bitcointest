from decimal import Decimal

from fastapi.testclient import TestClient

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError


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


def test_get_utxos_returns_exact_summary_and_sorted_outputs(client: TestClient, monkeypatch):
    class FakeRpc:
        def list_unspent(self, wallet: str, min_conf: int = 0, max_conf: int = 9999999):
            assert wallet == "alice"
            assert (min_conf, max_conf) == (0, 9999999)
            return [
                {
                    "txid": "pending-small",
                    "vout": 1,
                    # Bitcoin Core returns JSON numbers in live responses; this guards
                    # the smallest BTC unit without doing float arithmetic in the service.
                    "amount": 0.00000001,
                    "confirmations": 0,
                    "spendable": True,
                    "solvable": True,
                    "safe": True,
                },
                {
                    "txid": "confirmed-large",
                    "vout": 0,
                    "address": "bcrt1qalice",
                    "amount": "2.50000000",
                    "confirmations": 1,
                    "spendable": True,
                    "solvable": True,
                    "safe": True,
                },
                {
                    "txid": "confirmed-small",
                    "vout": 0,
                    "address": "bcrt1qother",
                    "amount": "1.00000000",
                    "confirmations": 1,
                    "spendable": False,
                    "solvable": True,
                    "safe": False,
                },
            ]

    monkeypatch.setattr("app.services.utxos.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/utxos/alice")

    assert response.status_code == 200
    assert response.json() == {
        "wallet_name": "alice",
        "utxo_count": 3,
        "confirmed_count": 2,
        "unconfirmed_count": 1,
        "total_amount_btc": "3.50000001",
        "total_amount_sats": 350000001,
        "utxos": [
            {
                "txid": "confirmed-large",
                "vout": 0,
                "address": "bcrt1qalice",
                "amount_btc": "2.50000000",
                "amount_sats": 250000000,
                "confirmations": 1,
                "spendable": True,
                "solvable": True,
                "safe": True,
            },
            {
                "txid": "confirmed-small",
                "vout": 0,
                "address": "bcrt1qother",
                "amount_btc": "1.00000000",
                "amount_sats": 100000000,
                "confirmations": 1,
                "spendable": False,
                "solvable": True,
                "safe": False,
            },
            {
                "txid": "pending-small",
                "vout": 1,
                "address": None,
                "amount_btc": "0.00000001",
                "amount_sats": 1,
                "confirmations": 0,
                "spendable": True,
                "solvable": True,
                "safe": True,
            },
        ],
    }


def test_get_utxos_returns_empty_summary(client: TestClient, monkeypatch):
    class FakeRpc:
        def list_unspent(self, wallet: str, min_conf: int = 0, max_conf: int = 9999999):
            return []

    monkeypatch.setattr("app.services.utxos.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/utxos/bob")

    assert response.status_code == 200
    assert response.json() == {
        "wallet_name": "bob",
        "utxo_count": 0,
        "confirmed_count": 0,
        "unconfirmed_count": 0,
        "total_amount_btc": "0.00000000",
        "total_amount_sats": 0,
        "utxos": [],
    }


def test_get_utxos_returns_404_for_unloaded_wallet(client: TestClient, monkeypatch):
    class FakeRpc:
        def list_unspent(self, wallet: str, min_conf: int = 0, max_conf: int = 9999999):
            raise BitcoinRpcError("Bitcoin wallet 'ghost' is not loaded", status_code=404)

    monkeypatch.setattr("app.services.utxos.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/utxos/ghost")

    assert response.status_code == 404
