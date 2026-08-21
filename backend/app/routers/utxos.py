from fastapi import APIRouter

from app.schemas import UtxoSummaryRead
from app.services import utxos as utxo_service

router = APIRouter(prefix="/utxos", tags=["utxos"])


@router.get("/{wallet_name}", response_model=UtxoSummaryRead)
def get_utxos(wallet_name: str):
    return utxo_service.list_utxos(wallet_name)
