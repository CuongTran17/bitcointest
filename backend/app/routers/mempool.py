from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import MempoolSummaryRead
from app.services import mempool as mempool_service

router = APIRouter(prefix="/mempool", tags=["mempool"])


@router.get("", response_model=MempoolSummaryRead)
def get_mempool(db: Session = Depends(get_db)):
    return mempool_service.list_mempool_transactions(db)
