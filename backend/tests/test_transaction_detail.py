from decimal import Decimal

from app.models import AppTransaction, WalletAddress


def test_get_transaction_detail_merges_raw_transaction_with_app_metadata(client, monkeypatch):
    class FakeSendRpc:
        def send_to_address(self, wallet: str, address: str, amount_btc: Decimal):
            return "tx1"

    class FakeRawRpc:
        def get_raw_transaction(self, txid: str, verbosity: int = 2, block_hash: str | None = None):
            assert txid == "tx1"
            assert verbosity == 2
            assert block_hash is None
            return {
                "txid": "tx1",
                "confirmations": 1,
                "blockhash": "blockhash1",
                "blocktime": 1787030000,
                "time": 1787030000,
                "size": 225,
                "vsize": 144,
                "weight": 573,
                "vin": [{"txid": "prevtx", "vout": 0, "sequence": 4294967295}],
                "vout": [
                    {
                        "n": 0,
                        "value": 2.0,
                        "scriptPubKey": {
                            "type": "witness_v0_keyhash",
                            "address": "bcrt1qbobaddress",
                        },
                    },
                    {
                        "n": 1,
                        "value": 7.9999859,
                        "scriptPubKey": {
                            "type": "witness_v0_keyhash",
                            "address": "bcrt1qchangeaddress",
                        },
                    },
                ],
            }

    from app.db import get_db

    db = next(client.app.dependency_overrides[get_db]())
    db.add(WalletAddress(address="bcrt1qbobaddress", wallet_name="bob"))
    db.commit()
    db.close()

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeSendRpc())
    client.post(
        "/transactions/send",
        json={"from_wallet": "alice", "to_address": "bcrt1qbobaddress", "amount_btc": "2.00000000"},
    )

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRawRpc())

    response = client.get("/transactions/detail/tx1")

    assert response.status_code == 200
    body = response.json()
    assert body["txid"] == "tx1"
    assert body["from_wallet"] == "alice"
    assert body["to_wallet"] == "bob"
    assert body["to_address"] == "bcrt1qbobaddress"
    assert body["amount_btc"] == "2.00000000"
    assert body["amount_sats"] == 200000000
    assert body["status"] == "confirmed"
    assert body["confirmations"] == 1
    assert body["blockhash"] == "blockhash1"
    assert body["size"] == 225
    assert body["vsize"] == 144
    assert body["weight"] == 573
    assert body["fee_btc"] is None
    assert body["fee_sats"] is None
    assert body["inputs"] == [{"txid": "prevtx", "vout": 0, "coinbase": None, "sequence": 4294967295}]
    assert body["outputs"][0] == {
        "n": 0,
        "value_btc": "2.00000000",
        "value_sats": 200000000,
        "address": "bcrt1qbobaddress",
        "wallet_name": "bob",
        "script_type": "witness_v0_keyhash",
    }
    assert body["raw"]["txid"] == "tx1"


def test_transaction_detail_propagates_bitcoin_rpc_error(client, monkeypatch):
    from app.bitcoin_rpc import BitcoinRpcError

    class FakeRpc:
        def get_raw_transaction(self, txid: str, verbosity: int = 2, block_hash: str | None = None):
            raise BitcoinRpcError(
                "No such mempool or blockchain transaction",
                status_code=404,
                rpc_code=-5,
            )

    monkeypatch.setattr("app.services.transactions.BitcoinRpcClient", lambda: FakeRpc())

    response = client.get("/transactions/detail/missingtx")

    assert response.status_code == 404
    assert response.json() == {"detail": "No such mempool or blockchain transaction"}
