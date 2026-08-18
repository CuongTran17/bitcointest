from fastapi import APIRouter, status

from app.schemas import AddressRead, BalanceRead
from app.services import wallets as wallet_service

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("/{wallet_name}/address", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
def create_address(wallet_name: str):
    return wallet_service.create_address(wallet_name)


@router.get("/{wallet_name}/balance", response_model=BalanceRead)
def get_balance(wallet_name: str):
    return wallet_service.get_balance(wallet_name)
