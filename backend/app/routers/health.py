from fastapi import APIRouter

from app.bitcoin_rpc import BitcoinRpcClient

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/bitcoin")
def bitcoin_health() -> dict[str, int | str]:
    info = BitcoinRpcClient().get_blockchain_info()
    return {"chain": info["chain"], "blocks": info["blocks"]}
