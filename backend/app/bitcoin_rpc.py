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
