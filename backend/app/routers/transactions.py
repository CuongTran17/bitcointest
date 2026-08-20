from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import SendTransactionRead, SendTransactionRequest, TransactionRead
from app.services import transactions as transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/send", response_model=SendTransactionRead, status_code=status.HTTP_201_CREATED)
def send_transaction(payload: SendTransactionRequest, db: Session = Depends(get_db)):
    return transaction_service.send_transaction(payload, db)


@router.get("/{wallet_name}", response_model=list[TransactionRead])
def list_transactions(wallet_name: str, db: Session = Depends(get_db)):
    return transaction_service.list_transactions(wallet_name, db)
