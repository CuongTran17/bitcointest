from decimal import Decimal
from typing import Any

import requests

from app.config import Settings

SATOSHIS_PER_BTC = Decimal("100000000")


class BitcoinRpcError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def btc_to_sats(amount: Decimal) -> int:
    return int(amount * SATOSHIS_PER_BTC)


class BitcoinRpcClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.base_url = f"http://{self.settings.bitcoin_rpc_host}:{self.settings.bitcoin_rpc_port}"
        self.auth = (self.settings.bitcoin_rpc_user, self.settings.bitcoin_rpc_password)

    def call(self, method: str, params: list[Any] | None = None, wallet: str | None = None) -> Any:
        url = self.base_url if wallet is None else f"{self.base_url}/wallet/{wallet}"
        response = requests.post(
            url,
            json={"jsonrpc": "1.0", "id": "local-bitcoin-bank", "method": method, "params": params or []},
            auth=self.auth,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error") is not None:
            raise BitcoinRpcError(str(payload["error"]))
        return payload["result"]

    def get_blockchain_info(self) -> dict[str, Any]:
        return self.call("getblockchaininfo")

    def list_wallets(self) -> list[str]:
        return self.call("listwallets")

    def ensure_wallet_loaded(self, wallet: str) -> None:
        if wallet not in self.list_wallets():
            raise BitcoinRpcError(f"Bitcoin wallet '{wallet}' is not loaded", status_code=404)

    def get_new_address(self, wallet: str) -> str:
        self.ensure_wallet_loaded(wallet)
        return self.call("getnewaddress", wallet=wallet)

    def get_balances(self, wallet: str) -> dict[str, Decimal]:
        self.ensure_wallet_loaded(wallet)
        confirmed = Decimal(str(self.call("getbalance", ["*", 1], wallet=wallet)))
        total = Decimal(str(self.call("getbalance", ["*", 0], wallet=wallet)))
        return {"confirmed": confirmed, "unconfirmed": total - confirmed, "total": total}

    def send_to_address(self, wallet: str, address: str, amount_btc: Decimal) -> str:
        self.ensure_wallet_loaded(wallet)
        return self.call("sendtoaddress", [address, f"{amount_btc:.8f}"], wallet=wallet)

    def mine_blocks(self, wallet: str, block_count: int) -> list[str]:
        address = self.get_new_address(wallet)
        return self.call("generatetoaddress", [block_count, address])
