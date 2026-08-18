from fastapi import APIRouter, status

from app.schemas import SendTransactionRead, SendTransactionRequest
from app.services import transactions as transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/send", response_model=SendTransactionRead, status_code=status.HTTP_201_CREATED)
def send_transaction(payload: SendTransactionRequest):
    return transaction_service.send_transaction(payload)
