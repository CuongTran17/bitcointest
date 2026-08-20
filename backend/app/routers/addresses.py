from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AddressOwnerRead
from app.services import wallets as wallet_service

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("/{address}", response_model=AddressOwnerRead)
def get_address_owner(address: str, db: Session = Depends(get_db)):
    wallet_name = wallet_service.find_wallet_by_address(address, db)
    if wallet_name is None:
        raise HTTPException(status_code=404, detail="Address is not mapped to a local wallet")
    return AddressOwnerRead(address=address, wallet_name=wallet_name)
