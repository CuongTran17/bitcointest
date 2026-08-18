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
