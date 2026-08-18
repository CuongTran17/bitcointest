from decimal import Decimal

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.schemas import FaucetRead, FaucetRequest, SendTransactionRead, SendTransactionRequest


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def send_transaction(payload: SendTransactionRequest) -> SendTransactionRead:
    txid = BitcoinRpcClient().send_to_address(payload.from_wallet, payload.to_address, payload.amount_btc)
    return SendTransactionRead(
        txid=txid,
        from_wallet=payload.from_wallet,
        to_address=payload.to_address,
        amount_btc=format_btc(payload.amount_btc),
        amount_sats=btc_to_sats(payload.amount_btc),
    )


def fund_from_faucet(wallet_name: str, payload: FaucetRequest) -> FaucetRead:
    rpc = BitcoinRpcClient()
    address = rpc.get_new_address(wallet_name)
    txid = rpc.send_to_address("miner", address, payload.amount_btc)
    block_hashes = rpc.mine_blocks("miner", 1)
    return FaucetRead(
        txid=txid,
        from_wallet="miner",
        to_wallet=wallet_name,
        to_address=address,
        amount_btc=format_btc(payload.amount_btc),
        amount_sats=btc_to_sats(payload.amount_btc),
        block_hashes=block_hashes,
    )
