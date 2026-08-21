import re
from decimal import Decimal

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError
from app.schemas import BlockDetailRead, BlockListRead, BlockSummaryRead

BLOCK_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def format_difficulty(value: object) -> str:
    return f"{Decimal(str(value)):.18f}".rstrip("0").rstrip(".") or "0"


def summary_from_raw(raw: dict) -> BlockSummaryRead:
    return BlockSummaryRead(
        height=int(raw["height"]),
        hash=raw["hash"],
        confirmations=int(raw.get("confirmations", 0)),
        time=int(raw["time"]),
        size=int(raw["size"]),
        weight=int(raw["weight"]),
        transaction_count=len(raw.get("tx", [])),
        previous_hash=raw.get("previousblockhash"),
        next_hash=raw.get("nextblockhash"),
    )


def resolve_block_hash(rpc: BitcoinRpcClient, block_ref: str) -> str:
    if re.fullmatch(r"[0-9]+", block_ref):
        return rpc.get_block_hash(int(block_ref))
    if BLOCK_HASH_PATTERN.fullmatch(block_ref):
        return block_ref
    raise BitcoinRpcError(
        "Block reference must be a non-negative height or 64-character hash",
        status_code=422,
    )


def list_blocks(limit: int = 20) -> BlockListRead:
    rpc = BitcoinRpcClient()
    info = rpc.get_blockchain_info()
    tip_height = int(info["blocks"])
    first_height = max(0, tip_height - limit + 1)
    blocks = []
    for height in range(tip_height, first_height - 1, -1):
        block_hash = info["bestblockhash"] if height == tip_height else rpc.get_block_hash(height)
        blocks.append(summary_from_raw(rpc.get_block(block_hash, verbosity=1)))
    return BlockListRead(
        chain=info["chain"],
        tip_height=tip_height,
        tip_hash=info["bestblockhash"],
        blocks=blocks,
    )


def get_block_detail(block_ref: str) -> BlockDetailRead:
    rpc = BitcoinRpcClient()
    block_hash = resolve_block_hash(rpc, block_ref)
    raw = rpc.get_block(block_hash, verbosity=1)
    summary = summary_from_raw(raw)
    return BlockDetailRead(
        **summary.model_dump(),
        version=int(raw["version"]),
        version_hex=raw["versionHex"],
        merkle_root=raw["merkleroot"],
        median_time=int(raw["mediantime"]),
        nonce=int(raw["nonce"]),
        bits=raw["bits"],
        difficulty=format_difficulty(raw["difficulty"]),
        chainwork=raw["chainwork"],
        transaction_ids=list(raw.get("tx", [])),
    )
