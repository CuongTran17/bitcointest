from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    wallet_name: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class UserRead(BaseModel):
    id: int
    name: str
    wallet_name: str

    model_config = {"from_attributes": True}
