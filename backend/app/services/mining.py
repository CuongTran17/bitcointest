from app.bitcoin_rpc import BitcoinRpcClient
from app.schemas import MineBlocksRead, MineBlocksRequest


def mine_blocks(payload: MineBlocksRequest) -> MineBlocksRead:
    block_hashes = BitcoinRpcClient().mine_blocks(payload.wallet_name, payload.block_count)
    return MineBlocksRead(
        wallet_name=payload.wallet_name,
        block_count=payload.block_count,
        block_hashes=block_hashes,
    )
