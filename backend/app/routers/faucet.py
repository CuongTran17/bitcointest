from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import FaucetRead, FaucetRequest
from app.services import transactions as transaction_service

router = APIRouter(prefix="/faucet", tags=["faucet"])


@router.post("/{wallet_name}", response_model=FaucetRead, status_code=status.HTTP_201_CREATED)
def fund_from_faucet(wallet_name: str, payload: FaucetRequest, db: Session = Depends(get_db)):
    return transaction_service.fund_from_faucet(wallet_name, payload, db)
