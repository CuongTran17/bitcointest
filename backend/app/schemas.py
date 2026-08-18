from decimal import Decimal

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
