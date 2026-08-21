from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    wallet_name: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class UserRead(BaseModel):
    id: int
    name: str
    wallet_name: str

    model_config = {"from_attributes": True}


class AddressRead(BaseModel):
    wallet_name: str
    address: str


class AddressOwnerRead(BaseModel):
    address: str
    wallet_name: str


class BalanceRead(BaseModel):
    wallet_name: str
    confirmed_balance_btc: str
    unconfirmed_balance_btc: str
    total_balance_btc: str
    confirmed_balance_sats: int
    unconfirmed_balance_sats: int
    total_balance_sats: int


class SendTransactionRequest(BaseModel):
    from_wallet: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    to_address: str = Field(min_length=8)
    amount_btc: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=8)


class SendTransactionRead(BaseModel):
    txid: str
    from_wallet: str
    to_wallet: str | None = None
    to_address: str
    amount_btc: str
    amount_sats: int


class FaucetRequest(BaseModel):
    amount_btc: Decimal = Field(default=Decimal("10.00000000"), gt=Decimal("0"), max_digits=16, decimal_places=8)


class FaucetRead(BaseModel):
    txid: str
    from_wallet: str
    to_wallet: str
    to_address: str
    amount_btc: str
    amount_sats: int
    block_hashes: list[str]


class MineBlocksRequest(BaseModel):
    wallet_name: str = Field(default="miner", min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    block_count: int = Field(default=1, ge=1, le=101)


class MineBlocksRead(BaseModel):
    wallet_name: str
    block_count: int
    block_hashes: list[str]


class TransactionRead(BaseModel):
    txid: str
    from_wallet: str | None = None
    to_wallet: str | None = None
    category: str
    amount_btc: str
    amount_sats: int
    confirmations: int
    status: str
    time: int | None = None
    blockhash: str | None = None
    address: str | None = None


class TransactionInputRead(BaseModel):
    txid: str | None = None
    vout: int | None = None
    coinbase: str | None = None
    sequence: int | None = None


class TransactionOutputRead(BaseModel):
    n: int
    value_btc: str
    value_sats: int
    address: str | None = None
    wallet_name: str | None = None
    script_type: str | None = None


class TransactionDetailRead(BaseModel):
    txid: str
    from_wallet: str | None = None
    to_wallet: str | None = None
    to_address: str | None = None
    amount_btc: str | None = None
    amount_sats: int | None = None
    confirmations: int
    status: str
    blockhash: str | None = None
    blocktime: int | None = None
    time: int | None = None
    size: int | None = None
    vsize: int | None = None
    weight: int | None = None
    fee_btc: str | None = None
    fee_sats: int | None = None
    inputs: list[TransactionInputRead]
    outputs: list[TransactionOutputRead]
    raw: dict[str, Any]
