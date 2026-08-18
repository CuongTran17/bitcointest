from fastapi import APIRouter, status

from app.schemas import MineBlocksRead, MineBlocksRequest
from app.services import mining as mining_service

router = APIRouter(tags=["mining"])


@router.post("/mine", response_model=MineBlocksRead, status_code=status.HTTP_201_CREATED)
def mine_blocks(payload: MineBlocksRequest):
    return mining_service.mine_blocks(payload)
