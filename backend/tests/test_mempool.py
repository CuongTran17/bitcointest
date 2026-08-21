from decimal import Decimal

from fastapi.testclient import TestClient

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError


def test_get_raw_mempool_requests_verbose_node_data(monkeypatch):
    calls = []

    def fake_call(self, method, params=None, wallet=None):
        calls.append((method, params, wallet))
        return {"tx1": {"vsize": 141}}

    monkeypatch.setattr(BitcoinRpcClient, "call", fake_call)

    result = BitcoinRpcClient().get_raw_mempool()

    assert result == {"tx1": {"vsize": 141}}
    assert calls == [("getrawmempool", [True], None)]


def test_mempool_returns_fee_summary_and_known_wallet_metadata(client: TestClient, monkeypatch):
    class FakeAddressRpc:
        def get_new_address(self, wallet: str):
            assert wallet == "bob"
            return "bcrt1qbobaddress"

    monkeypatch.setattr("app.services.wallets.BitcoinRpcClient", lambda: FakeAddressRpc())
    assert client.post("/wallets/bob/address").status_code == 201

    class FakeSendRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            assert wallet == "alice"
            assert address == "bcrt1qbobaddress"
            assert amount_btc == Decimal("2.00000000")
            return "known-tx"

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeSendRpc())
    assert client.post(
        "/transactions/send",
        json={
            "from_wallet": "alice",
            "to_address": "bcrt1qbobaddress",
            "amount_btc": "2.00000000",
        },
    ).status_code == 201

    decoded_txids = []

    class FakeMempoolRpc:
        def get_raw_mempool(self, verbose: bool = True):
            assert verbose is True
            return {
                "unknown-tx": {
                    "wtxid": "unknown-wtx",
                    "vsize": 100,
                    "weight": 400,
                    "fees": {"base": "0.00002000"},
                    "time": 1787030001,
                    "height": 102,
                    "ancestorcount": 1,
                    "descendantcount": 1,
                    "depends": [],
                    "spentby": [],
                    "bip125-replaceable": False,
                    "unbroadcast": False,
                },
                "known-tx": {
                    "wtxid": "known-wtx",
                    "vsize": 141,
                    "weight": 564,
                    "fees": {"base": "0.00001000"},
                    "time": 1787030000,
                    "height": 101,
                    "ancestorcount": 1,
                    "descendantcount": 2,
                    "depends": ["parent-tx"],
                    "spentby": ["child-tx"],
                    "bip125-replaceable": True,
                    "unbroadcast": False,
                },
            }

        def get_raw_transaction(self, txid: str, verbosity: int = 2, block_hash: str | None = None):
            assert verbosity == 1
            assert block_hash is None
            decoded_txids.append(txid)
            return {
                "txid": txid,
                "vout": [
                    {
                        "value": "2.00000000",
                        "scriptPubKey": {
                            "address": "bcrt1qbobaddress" if txid == "known-tx" else "bcrt1qexternal"
                        },
                    }
                ],
            }

    monkeypatch.setattr("app.services.mempool.BitcoinRpcClient", lambda: FakeMempoolRpc())

    response = client.get("/mempool")

    assert response.status_code == 200
    payload = response.json()
    assert payload["transaction_count"] == 2
    assert payload["total_vsize"] == 241
    assert payload["total_fee_btc"] == "0.00003000"
    assert payload["total_fee_sats"] == 3000
    assert [item["txid"] for item in payload["transactions"]] == ["unknown-tx", "known-tx"]
    known = payload["transactions"][1]
    assert known["from_wallet"] == "alice"
    assert known["to_wallet"] == "bob"
    assert known["to_address"] == "bcrt1qbobaddress"
    assert known["fee_sats"] == 1000
    assert known["fee_rate_sat_vb"] == "7.09219858"
    assert known["status"] == "pending"
    assert known["output_addresses"] == ["bcrt1qbobaddress"]
    assert payload["transactions"][0]["from_wallet"] is None
    assert payload["transactions"][0]["to_wallet"] is None
    assert set(decoded_txids) == {"known-tx", "unknown-tx"}


def test_mempool_returns_empty_summary(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_raw_mempool(self, verbose: bool = True):
            return {}

    monkeypatch.setattr("app.services.mempool.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/mempool")

    assert response.status_code == 200
    assert response.json() == {
        "transaction_count": 0,
        "total_vsize": 0,
        "total_fee_btc": "0.00000000",
        "total_fee_sats": 0,
        "transactions": [],
    }


def test_mempool_skips_entry_mined_between_snapshot_and_decode(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_raw_mempool(self, verbose: bool = True):
            return {
                "vanished": {"vsize": 100, "fees": {"base": "0.00000100"}},
                "remaining": {"vsize": 120, "fees": {"base": "0.00000200"}},
            }

        def get_raw_transaction(self, txid: str, verbosity: int = 2, block_hash: str | None = None):
            if txid == "vanished":
                raise BitcoinRpcError("No such transaction", status_code=404, rpc_code=-5)
            return {"txid": txid, "vout": []}

    monkeypatch.setattr("app.services.mempool.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/mempool")

    assert response.status_code == 200
    assert [item["txid"] for item in response.json()["transactions"]] == ["remaining"]


def test_mempool_rpc_error_uses_existing_error_handler(client: TestClient, monkeypatch):
    class FakeRpc:
        def get_raw_mempool(self, verbose: bool = True):
            raise BitcoinRpcError("Bitcoin Core unavailable", status_code=502)

    monkeypatch.setattr("app.services.mempool.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/mempool")

    assert response.status_code == 502
    assert response.json() == {"detail": "Bitcoin Core unavailable"}
